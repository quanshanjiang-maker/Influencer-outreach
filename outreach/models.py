"""Plain data types shared across modules."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Criteria:
    """One row of the Criteria tab: what to look for today."""
    name: str
    keywords: str
    description: str = ""
    language: str = ""          # e.g. "en"; empty = any
    min_followers: int = 0
    max_followers: int = 0      # 0 = no limit
    min_avg_likes: float = 0.0
    max_candidates: int = 200
    enabled: bool = True


@dataclass
class Tweet:
    id: str
    text: str
    url: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    lang: str = ""
    created_at: str = ""


@dataclass
class Creator:
    username: str
    name: str = ""
    profile_url: str = ""
    followers: int = 0
    bio: str = ""
    location: str = ""
    website: str = ""
    lang: str = ""
    tweets: list[Tweet] = field(default_factory=list)
    matched_queries: set[str] = field(default_factory=set)

    @property
    def avg_likes(self) -> float:
        if not self.tweets:
            return 0.0
        return sum(t.likes for t in self.tweets) / len(self.tweets)

    @property
    def top_tweet(self) -> Tweet | None:
        return max(self.tweets, key=lambda t: t.likes, default=None)
