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
    regions: list[str] = field(default_factory=list)   # ISO country codes, used by EasyKOL
    rules: str = ""             # free-text hard rules, exclusions and ICP tiers for the scorer
    # Fixed searches as (label, query); when set, no Claude query expansion. The label
    # (e.g. a competitor's name) is written to the "competitor" column.
    queries: list[tuple[str, str]] = field(default_factory=list)
    since_days: int = 0         # X: only posts from the last N days (0 = no limit)
    pages_per_query: int = 0    # 0 = use config search.pages_per_query
    platforms: list[str] = field(default_factory=lambda: ["x"])


@dataclass
class Post:
    """A tweet, video, reel or post. Engagement fields are 0 when a platform lacks them."""
    id: str
    text: str
    url: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    lang: str = ""
    created_at: str = ""


Tweet = Post  # backwards-compatible name


PLATFORMS = ("x", "youtube", "instagram", "tiktok")


@dataclass
class Creator:
    username: str
    platform: str = "x"
    name: str = ""
    profile_url: str = ""
    followers: int = 0
    bio: str = ""
    location: str = ""
    website: str = ""
    account_created: str = ""   # X: account creation date
    dm_open: str = ""           # X: "yes" / "no" / "" (unknown)
    lang: str = ""
    tweets: list[Post] = field(default_factory=list)
    matched_queries: set[str] = field(default_factory=set)
    email: str = ""
    email_source: str = ""
    relevance: float = 0.0      # provider's own relevance score, 0-1, if any
    match_reason: str = ""
    competitor: str = ""        # labels of the fixed queries this creator matched
    competitor_post: str = ""   # URL of their most-liked matching post
    competitor_post_text: str = ""
    competitor_post_date: str = ""

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.username.lower()}"

    @property
    def avg_likes(self) -> float:
        if not self.tweets:
            return 0.0
        return sum(t.likes for t in self.tweets) / len(self.tweets)

    @property
    def top_tweet(self) -> Post | None:
        return max(self.tweets, key=lambda t: t.likes, default=None)
