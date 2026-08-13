"""easyofd backend: pure Python, zero native dependencies."""

from __future__ import annotations

import logging
import math
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from easyofd.ofd import OFD

from .base import BaseBackend

logger = logging.getLogger(__name__)


def _patch_easyofd_font_size_scaling() -> None:
    """Patch easyofd to scale font size by TextObject CTM.

    easyofd's DrawPDF applies the CTM to character positions but keeps
    the font size at the raw ``Size`` value. When a document uses a CTM
    with a scale factor (common in WPS-generated tables), the glyphs are
    drawn too large for their computed spacing and overlap each other,
    producing the "重影" effect seen in complex appendices.

    This patch scales each text object's font size by the CTM's linear
    scale factor so that glyph size and glyph spacing are consistent.
    """
    try:
        from easyofd.draw import draw_pdf
    except Exception as exc:  # pragma: no cover
        logger.debug("Could not load easyofd.draw.draw_pdf for patching: %s", exc)
        return

    _original_draw_chars = draw_pdf.DrawPDF.draw_chars

    def _draw_chars_with_ctm_font_scaling(
        self, canvas, text_list, fonts, page_size, drawparams
    ):
        scaled_text_list = []
        for line_dict in text_list:
            line = dict(line_dict)  # shallow copy so we do not mutate parsed data
            ctm = line.get("CTM", "")
            if ctm:
                parts = ctm.split(" ")
                if len(parts) == 6:
                    try:
                        a, b, _c, _d, _e, _f = (float(p) for p in parts)
                        scale = math.hypot(a, b) or 1.0
                        if scale > 0:
                            line["size"] = line["size"] * scale
                    except (ValueError, TypeError):
                        pass
            scaled_text_list.append(line)
        return _original_draw_chars(
            self, canvas, scaled_text_list, fonts, page_size, drawparams
        )

    draw_pdf.DrawPDF.draw_chars = _draw_chars_with_ctm_font_scaling


# ---------------------------------------------------------------------------
# Path (table border) CTM fix.
#
# WPS-generated OFDs store PathObject coordinates in pt units relative to the
# Boundary origin, with a CTM that maps them into mm (scale ~0.3528, sometimes
# combined with a rotation for landscape pages). easyofd ignores the CTM and
# treats the numbers as mm offsets, so table borders are drawn ~2.83x too far
# out and end up clipped off the page ("表格显示不全"). We make easyofd carry
# the CTM through parsing and apply it to path coordinates before drawing.
# ---------------------------------------------------------------------------

_ABBR_MODES = {"M": 2, "L": 2, "S": 2, "Q": 4, "B": 6, "C": 0, "A": 7}


def _apply_ctm_to_abbr(abbr: str, ctm: str) -> str:
    """Apply the PathObject CTM to every coordinate pair in AbbreviatedData.

    The CTM maps object (pt) coordinates to mm offsets relative to the
    Boundary origin; the result is fed back into easyofd's draw_line, which
    already understands mm offsets.
    """
    try:
        a, b, c, d, e, f = (float(v) for v in ctm.split())
    except ValueError:
        return abbr

    parts = abbr.split()
    out: list[str] = []
    i = 0
    while i < len(parts):
        tok = parts[i]
        out.append(tok)
        n = _ABBR_MODES.get(tok, 0)
        if n:
            coords = parts[i + 1 : i + 1 + n]
            if tok == "A":  # arc: transform only the (x, y) end point
                rx, ry, ang, la, sw, x, y = (float(v) for v in coords)
                nx = a * x + c * y + e
                ny = b * x + d * y + f
                out.extend([f"{rx:.4f}", f"{ry:.4f}", ang, la, sw, f"{nx:.4f}", f"{ny:.4f}"])
            else:
                new_coords: list[str] = []
                for j in range(0, n, 2):
                    x, y = float(coords[j]), float(coords[j + 1])
                    new_coords.extend([f"{a * x + c * y + e:.4f}", f"{b * x + d * y + f:.4f}"])
                out.extend(new_coords)
            i += 1 + n
        else:
            i += 1
    return " ".join(out)


def _collect_path_ctm(xml_obj: Any) -> dict[str, str]:
    """Map PathObject ID -> CTM by walking the parsed XML tree."""
    ctm_map: dict[str, str] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "ofd:PathObject":
                    items = v if isinstance(v, list) else [v]
                    for item in items:
                        if isinstance(item, dict) and item.get("@ID") is not None:
                            ctm_map[str(item["@ID"])] = item.get("@CTM", "")
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(xml_obj)
    return ctm_map


def _patch_easyofd_path_ctm() -> None:
    """Let easyofd keep the PathObject CTM and apply it to path coordinates."""
    try:
        from easyofd.draw import draw_pdf
        from easyofd.parser_ofd.file_content_parser import ContentFileParser
    except Exception as exc:  # pragma: no cover
        logger.debug("Could not load easyofd for path CTM patch: %s", exc)
        return

    # (a) parser: keep the PathObject CTM in each line entry, and restore
    # leading spaces that xmltodict (strip_whitespace=True) removed from
    # TextCode text. WPS uses leading spaces for indentation; without them
    # the character count no longer matches DeltaX and glyphs are drawn on
    # the wrong advance (overlapping text).
    _original_content_call = ContentFileParser.__call__

    def _call_with_ctm(self):
        result = _original_content_call(self)
        try:
            ctm_map = _collect_path_ctm(self.xml_obj)
            for line in result.get("line_list", []):
                line["CTM"] = ctm_map.get(str(line.get("ID")), "")
            for t in result.get("text_list", []):
                text = t.get("text", "")
                dx = t.get("DeltaX", "")
                dy = t.get("DeltaY", "")
                n_adv = len(dx.split()) if dx else 0
                if not n_adv and dy:
                    n_adv = len(dy.split())
                if n_adv and len(text) < n_adv + 1:
                    t["text"] = " " * (n_adv + 1 - len(text)) + text
        except Exception as exc:  # pragma: no cover
            logger.debug("line CTM collection failed: %s", exc)
        return result

    ContentFileParser.__call__ = _call_with_ctm

    # (b) draw: transform path coordinates with the CTM before drawing
    _original_draw_line = draw_pdf.DrawPDF.draw_line

    def _draw_line_with_ctm(self, canvas, line_list, page_size, drawparams):
        if not line_list:
            return _original_draw_line(self, canvas, line_list, page_size, drawparams)
        new_list = []
        for line in line_list:
            ctm = line.get("CTM", "")
            if ctm and line.get("AbbreviatedData"):
                line = dict(line)
                line["AbbreviatedData"] = _apply_ctm_to_abbr(line["AbbreviatedData"], ctm)
            new_list.append(line)
        return _original_draw_line(self, canvas, new_list, page_size, drawparams)

    draw_pdf.DrawPDF.draw_line = _draw_line_with_ctm


# Apply the patch once at import time. Set OFD2PDF_DISABLE_CTM_PATCH=1 to
# skip it (escape hatch for documents where the original behaviour is wanted).
if os.environ.get("OFD2PDF_DISABLE_CTM_PATCH", "").lower() not in ("1", "true", "yes"):
    _patch_easyofd_font_size_scaling()
    _patch_easyofd_path_ctm()


@contextmanager
def _easyofd_workdir():
    """Run easyofd in a private temp directory.

    easyofd writes temporary OFD/ZIP files into the current working
    directory and removes them with ``shutil.rmtree``. Some restricted
    environments (e.g., sandboxes without a Recycle Bin) block that
    removal. By moving into a temp directory first, any leftover files
    are isolated and the conversion still succeeds.
    """
    original_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(prefix="ofd2pdf_easyofd_")
    _original_rmtree = shutil.rmtree

    def _tolerant_rmtree(path, *args, **kwargs):
        try:
            return _original_rmtree(path, *args, **kwargs)
        except OSError as exc:
            logger.debug("Ignored cleanup error for %s: %s", path, exc)

    os.chdir(tmpdir)
    shutil.rmtree = _tolerant_rmtree
    try:
        yield tmpdir
    finally:
        shutil.rmtree = _original_rmtree
        os.chdir(original_cwd)
        try:
            _original_rmtree(tmpdir, ignore_errors=True)
        except OSError as exc:
            logger.debug("Could not remove temp dir %s: %s", tmpdir, exc)


class EasyOFDBackend(BaseBackend):
    """Backend powered by the easyofd package.

    Strengths: pip-installable, runs anywhere, good for simple invoices
    and text-heavy documents.

    Limitations: complex tables or CTM-heavy layouts may misalign.
    """

    name = "easyofd"

    @classmethod
    def is_available(cls) -> bool:
        try:
            import easyofd  # noqa: F401
            return True
        except Exception:
            return False

    def convert(self, input_path: str | Path, output_path: str | Path, **kwargs: Any) -> None:
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(f"OFD file not found: {input_path}")

        logger.info("[easyofd] Converting %s -> %s", input_path, output_path)

        input_abs = input_path.resolve()
        with _easyofd_workdir():
            ofd = OFD()
            ofd.read(str(input_abs), fmt="path")
            pdf_bytes = ofd.to_pdf()
            if not pdf_bytes:
                raise RuntimeError("easyofd returned empty PDF bytes")
            ofd.del_data()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)
        logger.info("[easyofd] Wrote %s (%d bytes)", output_path, len(pdf_bytes))
