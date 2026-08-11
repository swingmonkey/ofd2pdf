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


# Apply the patch once at import time. Set OFD2PDF_DISABLE_CTM_PATCH=1 to
# skip it (escape hatch for documents where the original behaviour is wanted).
if os.environ.get("OFD2PDF_DISABLE_CTM_PATCH", "").lower() not in ("1", "true", "yes"):
    _patch_easyofd_font_size_scaling()


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
