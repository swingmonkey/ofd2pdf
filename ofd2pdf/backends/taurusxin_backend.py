"""taurusxin/Ofd2Pdf backend (Windows EXE)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .base import BaseBackend

logger = logging.getLogger(__name__)


class TaurusxinBackend(BaseBackend):
    """Backend that calls taurusxin/Ofd2Pdf executable.

    Best for complex OFD documents on Windows. Download the EXE with
    ``scripts/setup_taurusxin.ps1`` (Windows) or the manual steps in README.md.
    """

    name = "taurusxin"
    default_exe_names = ["Ofd2Pdf.exe", "Ofd2Pdf"]

    def _find_exe(self) -> Path | None:
        # 1. Environment variable
        env = os.environ.get("OFD2PDF_TAURUSXIN_EXE")
        if env and Path(env).exists():
            return Path(env)

        # 2. Project bin/ directory (recommended setup location)
        project_root = Path(__file__).resolve().parents[2]
        for name in self.default_exe_names:
            candidate = project_root / "bin" / name
            if candidate.exists():
                return candidate

        # Note: we intentionally do NOT search PATH, because our own console
        # script is named "ofd2pdf.exe" and on Windows case-insensitive file
        # systems it would be mistaken for "Ofd2Pdf.exe".
        return None

    @classmethod
    def is_available(cls) -> bool:
        return cls()._find_exe() is not None

    def convert(self, input_path: str | Path, output_path: str | Path, **kwargs: Any) -> None:
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(f"OFD file not found: {input_path}")

        exe = self._find_exe()
        if not exe:
            raise RuntimeError(
                "taurusxin Ofd2Pdf.exe not found. "
                "Run scripts/setup_taurusxin.ps1 or set OFD2PDF_TAURUSXIN_EXE."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("[taurusxin] Converting %s -> %s using %s", input_path, output_path, exe)

        # Ofd2Pdf v1.2 accepts the input file path as the first argument.
        cmd = [str(exe), str(input_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"taurusxin conversion failed: {exc.stderr or exc.stdout}") from exc

        # The EXE writes to the same directory as the input with .pdf extension.
        inferred_pdf = input_path.with_suffix(".pdf")
        if not inferred_pdf.exists():
            raise RuntimeError(
                f"taurusxin did not produce expected output: {inferred_pdf}"
            )

        # Move to requested output path if different
        if inferred_pdf.resolve() != output_path.resolve():
            if output_path.exists():
                output_path.unlink()
            os.replace(inferred_pdf, output_path)

        logger.info("[taurusxin] Wrote %s (%d bytes)", output_path, output_path.stat().st_size)
