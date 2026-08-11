"""easyofd backend: pure Python, zero native dependencies."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from easyofd.ofd import OFD

from .base import BaseBackend

logger = logging.getLogger(__name__)


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
