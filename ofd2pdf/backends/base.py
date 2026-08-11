"""Base backend interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseBackend(ABC):
    """Abstract conversion backend."""

    name: str = ""

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Return True if this backend can be used right now."""

    @abstractmethod
    def convert(self, input_path: str | Path, output_path: str | Path, **kwargs: Any) -> None:
        """Convert ``input_path`` (OFD) to ``output_path`` (PDF)."""

    @classmethod
    def _which(cls, executable: str) -> str | None:
        """Cross-platform ``which``."""
        from shutil import which

        path = which(executable)
        return path
