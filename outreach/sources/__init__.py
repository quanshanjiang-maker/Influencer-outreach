"""X data source adapters. Add a new provider by implementing XSource."""
from __future__ import annotations

from .base import XSource


def get_source(name: str, api_key: str | None) -> XSource:
    if name == "twitterapi_io":
        from .twitterapi_io import TwitterApiIoSource
        return TwitterApiIoSource(api_key)
    raise ValueError(f"Unknown data_source: {name}")


__all__ = ["XSource", "get_source"]
