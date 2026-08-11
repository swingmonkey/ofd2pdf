"""ofdrw (Java) backend."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseBackend

logger = logging.getLogger(__name__)


class OFDRWBackend(BaseBackend):
    """Backend that calls an ofdrw-based Java converter jar.

    Most accurate for complex official OFD documents, but requires Java.
    Build the converter jar with ``scripts/ofdrw/`` and place it at
    ``bin/ofdrw-converter.jar`` (or set ``OFD2PDF_OFDRW_JAR``).
    """

    name = "ofdrw"

    def _find_jar(self) -> Path | None:
        env = os.environ.get("OFD2PDF_OFDRW_JAR")
        if env and Path(env).exists():
            return Path(env)

        project_root = Path(__file__).resolve().parents[2]
        candidate = project_root / "bin" / "ofdrw-converter.jar"
        if candidate.exists():
            return candidate
        return None

    @classmethod
    def is_available(cls) -> bool:
        if not cls()._find_jar():
            return False
        return cls()._which("java") is not None

    def convert(self, input_path: str | Path, output_path: str | Path, **kwargs: Any) -> None:
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(f"OFD file not found: {input_path}")

        jar = self._find_jar()
        if not jar:
            raise RuntimeError(
                "ofdrw converter jar not found. Build it from scripts/ofdrw/ "
                "or set OFD2PDF_OFDRW_JAR."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("[ofdrw] Converting %s -> %s using %s", input_path, output_path, jar)

        cmd = [
            "java",
            "-jar",
            str(jar),
            str(input_path),
            str(output_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"ofdrw conversion failed: {exc.stderr or exc.stdout}") from exc

        if not output_path.exists():
            raise RuntimeError("ofdrw did not produce output PDF")

        logger.info("[ofdrw] Wrote %s (%d bytes)", output_path, output_path.stat().st_size)
