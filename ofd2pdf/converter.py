"""High-level conversion API and backend registry."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from .backends import EasyOFDBackend, OFDRWBackend, TaurusxinBackend
from .backends.base import BaseBackend

logger = logging.getLogger(__name__)

BACKENDS: dict[str, Callable[[], BaseBackend]] = {
    EasyOFDBackend.name: EasyOFDBackend,
    TaurusxinBackend.name: TaurusxinBackend,
    OFDRWBackend.name: OFDRWBackend,
}

DEFAULT_BACKENDS = [EasyOFDBackend.name, TaurusxinBackend.name, OFDRWBackend.name]


def list_backends() -> dict[str, dict[str, Any]]:
    """Return status info for every known backend."""
    result: dict[str, dict[str, Any]] = {}
    for name, cls in BACKENDS.items():
        result[name] = {
            "name": name,
            "available": cls.is_available(),
            "description": cls.__doc__.strip().splitlines()[0] if cls.__doc__ else "",
        }
    return result


def pick_backend(name: str | None = None) -> BaseBackend:
    """Return an instantiated backend.

    If ``name`` is given, use it. Otherwise pick the first available backend
    in order: easyofd, taurusxin, ofdrw.
    """
    if name:
        if name not in BACKENDS:
            raise ValueError(f"Unknown backend '{name}'. Known: {list(BACKENDS)}")
        cls = BACKENDS[name]
        if not cls.is_available():
            raise RuntimeError(f"Backend '{name}' is not available. See README.md to set it up.")
        return cls()

    for candidate in DEFAULT_BACKENDS:
        cls = BACKENDS[candidate]
        if cls.is_available():
            logger.info("Auto-selected backend: %s", candidate)
            return cls()

    raise RuntimeError(
        "No backend available. Install easyofd (`pip install easyofd`) or set up taurusxin/ofdrw."
    )


def convert_file(
    input_path: str | Path,
    output_path: str | Path,
    backend: str | None = None,
    **kwargs: Any,
) -> None:
    """Convert a single OFD file to PDF."""
    b = pick_backend(backend)
    b.convert(input_path, output_path, **kwargs)


def convert_batch(
    input_dir: str | Path,
    output_dir: str | Path,
    backend: str | None = None,
    pattern: str = "*.ofd",
    **kwargs: Any,
) -> list[tuple[Path, Path | None]]:
    """Convert every OFD file in ``input_dir`` to ``output_dir``.

    Returns a list of (input_path, output_path_or_None_if_failed) pairs.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    files = sorted(input_dir.glob(pattern))
    if not files:
        logger.warning("No files matched %s in %s", pattern, input_dir)
        return []

    backend_inst = pick_backend(backend)
    results: list[tuple[Path, Path | None]] = []

    for idx, src in enumerate(files, 1):
        dst = output_dir / src.with_suffix(".pdf").name
        print(f"[{idx}/{len(files)}] {src.name} -> {dst}", flush=True)
        try:
            backend_inst.convert(src, dst, **kwargs)
            results.append((src, dst))
        except Exception as exc:
            logger.error("Failed to convert %s: %s", src, exc)
            results.append((src, None))

    return results
