from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from ..models import Creator, Tweet


class XSource(ABC):
    """Interface every X data provider implements."""

    @abstractmethod
    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Tweet]]:
        """Yield (author, tweet) pairs for an X advanced-search query."""

    @abstractmethod
    def recent_tweets(self, username: str, limit: int = 20) -> list[Tweet]:
        """Return a creator's most recent original tweets."""
