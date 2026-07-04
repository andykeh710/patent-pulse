"""Patent figure storage — pluggable backend (local FS, future S3)."""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings


class FigureStorage(ABC):
    """Abstract storage for patent figure files."""

    @abstractmethod
    def save(self, patent_id: str, ordinal: int, data: bytes, suffix: str = "png") -> str:
        """Save raw figure bytes, return storage path."""

    @abstractmethod
    def get(self, path: str) -> bytes:
        """Retrieve figure bytes by storage path."""

    @abstractmethod
    def delete(self, patent_id: str) -> None:
        """Delete all figures for a patent."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check whether a figure exists."""


class LocalFigureStorage(FigureStorage):
    """Filesystem-backed figure storage under settings.figures_storage_dir."""

    def __init__(self, base_dir: str | None = None):
        self._base = Path(base_dir or settings.figures_storage_dir)

    def _patent_dir(self, patent_id: str) -> Path:
        return self._base / str(patent_id)

    def save(self, patent_id: str, ordinal: int, data: bytes, suffix: str = "png") -> str:
        d = self._patent_dir(patent_id)
        d.mkdir(parents=True, exist_ok=True)
        filename = f"{ordinal}.{suffix}"
        filepath = d / filename
        filepath.write_bytes(data)
        return str(filepath)

    def get(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def delete(self, patent_id: str) -> None:
        d = self._patent_dir(patent_id)
        if d.exists():
            shutil.rmtree(d)

    def exists(self, path: str) -> bool:
        return Path(path).exists()


# Singleton
_storage: FigureStorage | None = None


def get_storage() -> FigureStorage:
    global _storage
    if _storage is None:
        _storage = LocalFigureStorage()
    return _storage
