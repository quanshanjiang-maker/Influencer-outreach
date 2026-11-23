"""Platform data source adapters. Add a provider by implementing Source."""
from __future__ import annotations

from .base import Source, XSource


def get_source(platform: str, cfg) -> Source:
    if platform == "x":
        from .twitterapi_io import TwitterApiIoSource
        return TwitterApiIoSource(cfg.twitterapi_io_key)
    if platform == "youtube":
        from .youtube import YouTubeSource
        return YouTubeSource(cfg.youtube_api_key)
    if platform == "instagram":
        from .apify_instagram import ApifyInstagramSource
        return ApifyInstagramSource(cfg.apify_token)
    if platform == "tiktok":
        from .apify_tiktok import ApifyTikTokSource
        return ApifyTikTokSource(cfg.apify_token)
    raise ValueError(f"Unknown platform: {platform}")


__all__ = ["Source", "XSource", "get_source"]
