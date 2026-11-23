from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from ..models import Creator, Post


class Source(ABC):
    """Interface every platform data provider implements."""

    platform: str = ""

    @abstractmethod
    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Post]]:
        """Yield (author, post) pairs for a search query."""

    def recent_posts(self, username: str, limit: int = 20) -> list[Post]:
        """Return a creator's recent posts (used by scoring). Optional."""
        return []

    def enrich(self, creators: list[Creator]) -> None:
        """Fill in profile fields (followers, bio) that search results lack. Optional."""


XSource = Source  # backwards-compatible name
