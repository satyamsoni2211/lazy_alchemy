from pathlib import Path

from lazy_alchemy.lazy_alchemy import get_lazy_class, CustomTable

here = Path(__file__).resolve().parent
version = (here / "VERSION").read_text(encoding="utf-8")

__version__ = version

__all__ = ("get_lazy_class", "CustomTable", "version")
