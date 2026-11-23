"""YouTube via the official YouTube Data API v3 (free daily quota).

search.list finds videos; videos.list and channels.list (cheap) add stats and
channel details. https://developers.google.com/youtube/v3/determine_quota_cost
"""
from __future__ import annotations

from typing import Iterator

import requests

from ..models import Creator, Post
from .base import Source

API = "https://www.googleapis.com/youtube/v3"


class YouTubeSource(Source):
    platform = "youtube"

    def __init__(self, api_key: str | None, language: str = "", timeout: int = 20):
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY is not set")
        self.key = api_key
        self.language = language
        self.timeout = timeout

    def _get(self, endpoint: str, params: dict) -> dict:
        r = requests.get(f"{API}/{endpoint}", params={**params, "key": self.key}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def search(self, query: str, max_pages: int) -> Iterator[tuple[Creator, Post]]:
        token = ""
        for _ in range(max_pages):
            params = {"part": "snippet", "q": query, "type": "video", "maxResults": 50, "order": "relevance"}
            if self.language:
                params["relevanceLanguage"] = self.language
            if token:
                params["pageToken"] = token
            data = self._get("search", params)
            items = [i for i in data.get("items", []) if i.get("id", {}).get("videoId")]
            if not items:
                break
            video_ids = [i["id"]["videoId"] for i in items]
            stats = {v["id"]: v for v in self._get("videos", {
                "part": "statistics,snippet", "id": ",".join(video_ids)}).get("items", [])}
            channel_ids = sorted({i["snippet"]["channelId"] for i in items})
            channels = {c["id"]: c for c in self._get("channels", {
                "part": "snippet,statistics", "id": ",".join(channel_ids)}).get("items", [])}
            for i in items:
                vid, sn = i["id"]["videoId"], i["snippet"]
                ch = channels.get(sn["channelId"], {})
                csn, cst = ch.get("snippet", {}), ch.get("statistics", {})
                handle = (csn.get("customUrl") or "").lstrip("@") or sn["channelId"]
                creator = Creator(
                    username=handle, platform="youtube", name=csn.get("title") or sn.get("channelTitle", ""),
                    profile_url=f"https://www.youtube.com/channel/{sn['channelId']}",
                    followers=int(cst.get("subscriberCount") or 0), bio=csn.get("description", "") or "",
                    location=csn.get("country", "") or "",
                )
                vst = stats.get(vid, {}).get("statistics", {})
                vsn = stats.get(vid, {}).get("snippet", {})
                post = Post(id=vid, text=f"{sn.get('title', '')}\n{vsn.get('description', '')[:500]}",
                            url=f"https://www.youtube.com/watch?v={vid}", likes=int(vst.get("likeCount") or 0),
                            replies=int(vst.get("commentCount") or 0), views=int(vst.get("viewCount") or 0),
                            lang=vsn.get("defaultAudioLanguage", "") or vsn.get("defaultLanguage", "") or "",
                            created_at=sn.get("publishedAt", ""))
                yield creator, post
            token = data.get("nextPageToken", "")
            if not token:
                break
