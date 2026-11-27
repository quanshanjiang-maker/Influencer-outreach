"""TwitterAPI.io adapter. Docs: https://docs.twitterapi.io"""
from __future__ import annotations

import time
from typing import Iterator

import requests

from ..models import Creator, Post as Tweet
from .base import Source

BASE = "https://api.twitterapi.io"


def _tweet(d: dict) -> Tweet:
    return Tweet(
        id=str(d.get("id", "")),
        text=d.get("text", "") or "",
        url=d.get("url", "") or "",
        likes=int(d.get("likeCount") or 0),
        retweets=int(d.get("retweetCount") or 0),
        replies=int(d.get("replyCount") or 0),
        views=int(d.get("viewCount") or 0),
        lang=d.get("lang", "") or "",
        created_at=d.get("createdAt", "") or "",
    )


def _creator(a: dict) -> Creator:
    website = ""
    urls = (((a.get("profile_bio") or {}).get("entities") or {}).get("url") or {}).get("urls") or []
    if urls:
        website = urls[0].get("expanded_url", "") or ""
    username = a.get("userName", "") or ""
    return Creator(
        username=username,
        platform="x",
        name=a.get("name", "") or "",
        profile_url=a.get("url") or f"https://x.com/{username}",
        followers=int(a.get("followers") or 0),
        following=int(a.get("following") or 0),
        bio=a.get("description", "") or "",
        location=a.get("location", "") or "",
        website=website,
        account_created=str(a.get("createdAt", "") or ""),
        dm_open={True: "yes", False: "no"}.get(a.get("canDm"), ""),
    )


class TwitterApiIoSource(Source):
    platform = "x"

    def __init__(self, api_key: str | None, timeout: int = 20):
        if not api_key:
            raise ValueError("TWITTERAPI_IO_KEY is not set")
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = api_key
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> dict:
        for attempt in range(4):
            r = self.session.get(f"{BASE}{path}", params=params, timeout=self.timeout)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()
        return r.json()

    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Tweet]]:
        cursor = ""
        for _ in range(max_pages):
            params = {"query": query, "queryType": "Latest"}
            if cursor:
                params["cursor"] = cursor
            data = self._get("/twitter/tweet/advanced_search", params)
            for t in data.get("tweets") or []:
                author = t.get("author") or {}
                if not author.get("userName"):
                    continue
                yield _creator(author), _tweet(t)
            if not data.get("has_next_page") or not data.get("next_cursor"):
                break
            cursor = data["next_cursor"]

    def recent_posts(self, username: str, limit: int = 20) -> list[Tweet]:
        data = self._get("/twitter/user/last_tweets", {"userName": username})
        # The response nests tweets under "data" on some API versions.
        tweets = data.get("tweets") or (data.get("data") or {}).get("tweets") or []
        out = [_tweet(t) for t in tweets if not t.get("retweeted_tweet")]
        return out[:limit]

    def user_info(self, username: str) -> Creator | None:
        data = self._get("/twitter/user/info", {"userName": username})
        u = data.get("data") or {}
        return _creator(u) if u.get("userName") else None

    def user_search(self, query: str) -> list[Creator]:
        data = self._get("/twitter/user/search", {"query": query})
        return [_creator(u) for u in (data.get("users") or []) if u.get("userName")]
