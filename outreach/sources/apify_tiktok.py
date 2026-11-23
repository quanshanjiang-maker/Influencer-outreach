"""TikTok via Apify's TikTok Scraper (clockworks/tiktok-scraper)."""
from __future__ import annotations

from typing import Iterator

from ..models import Creator, Post
from ._apify import run_actor
from .base import Source

ACTOR = "clockworks~tiktok-scraper"


class ApifyTikTokSource(Source):
    platform = "tiktok"

    def __init__(self, token: str | None, videos_per_page: int = 20):
        if not token:
            raise ValueError("APIFY_TOKEN is not set")
        self.token = token
        self.videos_per_page = videos_per_page

    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Post]]:
        term = query.strip()
        run_input = {"resultsPerPage": self.videos_per_page * max_pages}
        if term.startswith("#"):
            run_input["hashtags"] = [term.lstrip("#")]
        else:
            run_input.update({"searchQueries": [term], "searchSection": "/video"})
        for it in run_actor(self.token, ACTOR, run_input):
            a = it.get("authorMeta") or {}
            user = a.get("name")
            if not user:
                continue
            creator = Creator(username=user, platform="tiktok", name=a.get("nickName", "") or "",
                              profile_url=a.get("profileUrl") or f"https://www.tiktok.com/@{user}",
                              followers=int(a.get("fans") or 0), bio=a.get("signature", "") or "")
            post = Post(id=str(it.get("id", "")), text=it.get("text", "") or "",
                        url=it.get("webVideoUrl", "") or "", likes=int(it.get("diggCount") or 0),
                        replies=int(it.get("commentCount") or 0), retweets=int(it.get("shareCount") or 0),
                        views=int(it.get("playCount") or 0), lang=it.get("textLanguage", "") or "",
                        created_at=it.get("createTimeISO", "") or "")
            yield creator, post
