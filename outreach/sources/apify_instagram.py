"""Instagram via Apify's Instagram Scraper (apify/instagram-scraper).

Search returns posts for a hashtag or keyword; post items lack follower counts,
so enrich() fetches profile details for the creators that survive grouping.
"""
from __future__ import annotations

from typing import Iterator

from ..models import Creator, Post
from ._apify import run_actor
from .base import Source

ACTOR = "apify~instagram-scraper"


class ApifyInstagramSource(Source):
    platform = "instagram"

    def __init__(self, token: str | None, posts_per_page: int = 20):
        if not token:
            raise ValueError("APIFY_TOKEN is not set")
        self.token = token
        self.posts_per_page = posts_per_page

    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Post]]:
        term = query.strip()
        items = run_actor(self.token, ACTOR, {
            "search": term,
            "searchType": "hashtag",
            "searchLimit": 1 if term.startswith("#") else 3,
            "resultsType": "posts",
            "resultsLimit": self.posts_per_page * max_pages,
        })
        for it in items:
            user = it.get("ownerUsername")
            if not user:
                continue
            creator = Creator(username=user, platform="instagram", name=it.get("ownerFullName", "") or "",
                              profile_url=f"https://www.instagram.com/{user}/")
            post = Post(id=str(it.get("id") or it.get("shortCode") or ""), text=it.get("caption", "") or "",
                        url=it.get("url", "") or "", likes=int(it.get("likesCount") or 0),
                        replies=int(it.get("commentsCount") or 0),
                        views=int(it.get("videoPlayCount") or 0), created_at=it.get("timestamp", "") or "")
            yield creator, post

    def enrich(self, creators: list[Creator]) -> None:
        if not creators:
            return
        by_user = {c.username.lower(): c for c in creators}
        items = run_actor(self.token, ACTOR, {
            "directUrls": [f"https://www.instagram.com/{c.username}/" for c in creators],
            "resultsType": "details",
            "resultsLimit": 1,
        })
        for it in items:
            c = by_user.get(str(it.get("username", "")).lower())
            if not c:
                continue
            c.followers = int(it.get("followersCount") or 0)
            c.bio = it.get("biography", "") or c.bio
            c.name = it.get("fullName", "") or c.name
            c.website = it.get("externalUrl", "") or c.website
