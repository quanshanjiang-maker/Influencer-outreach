"""YouTube / TikTok / Instagram via the EasyKOL external API.

EasyKOL searches its own creator index semantically and returns creators with
follower counts, average views/likes and (often) a contact email, so this source
needs no query expansion and no separate email lookup.

API reference: https://github.com/iftechio/easykol-skills/blob/main/docs/api.md
Billing: POST /web-search costs 1 task point per batch on TikTok/YouTube and 2 on
Instagram; zero results are refunded. The same API key never returns a creator twice.
"""
from __future__ import annotations

import time
from typing import Iterator

import requests

from ..models import Creator, Post
from .base import Source

BASE = "https://app.easykol.com/external/v1"
PLATFORM_CODES = {"youtube": "YOUTUBE", "tiktok": "TIKTOK", "instagram": "INSTAGRAM"}


class EasyKolError(RuntimeError):
    pass


class EasyKolSource(Source):
    # Results are already semantic matches with stats, so skip LLM query expansion
    # and local engagement filtering (EasyKOL applies avgMin itself).
    expands_queries = False
    prefiltered = True

    def __init__(self, api_key: str | None, email: str | None, platform: str,
                 batch_count: int = 1, has_contact_info: bool = True,
                 poll_seconds: int = 5, timeout_seconds: int = 300):
        if not api_key or not email:
            raise ValueError("EASYKOL_API_KEY and EASYKOL_API_EMAIL are not set")
        if platform not in PLATFORM_CODES:
            raise ValueError(f"EasyKOL does not support platform {platform}")
        self.platform = platform
        self.session = requests.Session()
        self.session.headers.update({"ek-api-key": api_key, "ek-api-email": email})
        self.batch_count = batch_count
        self.has_contact_info = has_contact_info
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        # Set per criteria row by the CLI.
        self.language = ""
        self.regions: list[str] = []
        self.min_followers = 0
        self.max_followers = 0
        self.min_avg = 0

    def _call(self, method: str, path: str, **kw) -> dict:
        for attempt in range(5):
            r = self.session.request(method, f"{BASE}{path}", timeout=30, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(60, 2 ** attempt * 3))
                continue
            body = r.json()
            if body.get("statusCode") != 1000:
                raise EasyKolError(f"{body.get('statusCode')} {body.get('error')}: {body.get('message')}")
            return body.get("data") or {}
        raise EasyKolError(f"{path} kept failing with HTTP {r.status_code}")

    def quota(self) -> dict:
        return self._call("GET", "/quota")

    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Post]]:
        body = {
            "searchType": "smart",
            "platform": PLATFORM_CODES[self.platform],
            "sentence": query[:500],
            "batchCount": max(1, min(10, self.batch_count)),
            "hasContactInfo": self.has_contact_info,
        }
        if self.regions:
            body["regions"] = self.regions
        if self.language:
            body["languages"] = [self.language]
        if self.min_followers:
            body["minSubscribers"] = self.min_followers
        if self.max_followers:
            body["maxSubscribers"] = self.max_followers
        if self.min_avg:
            body["avgMin"] = int(self.min_avg)
        task = self._call("POST", "/web-search", json=body)
        task_id = task["taskId"]
        deadline = time.time() + self.timeout_seconds
        while task.get("status") not in ("COMPLETED", "FAILED"):
            if time.time() > deadline:
                raise EasyKolError(f"web-search task {task_id} still {task.get('status')} after "
                                   f"{self.timeout_seconds}s; it keeps running on EasyKOL's side")
            time.sleep(self.poll_seconds)
            task = self._call("GET", f"/web-search/{task_id}")
        if task["status"] == "FAILED":
            raise EasyKolError(f"web-search task {task_id} failed")
        for row in task.get("data") or []:
            yield _creator(row, self.platform), _summary_post(row)


def _creator(row: dict, platform: str) -> Creator:
    c = Creator(
        username=str(row.get("username") or "").lstrip("@"),
        platform=platform,
        name=row.get("nickname") or "",
        profile_url=row.get("profileUrl") or "",
        followers=int(row.get("followerCount") or 0),
        location=row.get("region") or "",
        lang=row.get("language") or "",
    )
    c.email = (row.get("email") or "").strip()
    c.email_source = "easykol" if c.email else ""
    c.relevance = float(row.get("relevanceScore") or 0)
    c.match_reason = row.get("reason") or ""
    return c


def _summary_post(row: dict) -> Post:
    """EasyKOL returns averages, not posts: store them as one summary post."""
    return Post(id=f"easykol:{row.get('username')}", text=row.get("reason") or "",
                url=row.get("profileUrl") or "", likes=int(row.get("averageLikeCount") or 0),
                views=int(row.get("averagePlayCount") or 0))
