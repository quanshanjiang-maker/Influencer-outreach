"""Platform data source adapters. Add a provider by implementing Source."""
from __future__ import annotations

from .base import Source, XSource


DEFAULT_PROVIDERS = {"x": "twitterapi_io", "youtube": "youtube_api",
                     "instagram": "apify", "tiktok": "apify"}


def get_source(platform: str, cfg) -> Source:
    provider = (cfg.providers or {}).get(platform, DEFAULT_PROVIDERS.get(platform))
    if provider == "easykol":
        from .easykol import EasyKolSource
        opts = (cfg.providers or {}).get("easykol_options", {}) or {}
        return EasyKolSource(cfg.easykol_api_key, cfg.easykol_api_email, platform,
                             batch_count=int(opts.get("batch_count", 1)),
                             has_contact_info=bool(opts.get("has_contact_info", True)))
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
