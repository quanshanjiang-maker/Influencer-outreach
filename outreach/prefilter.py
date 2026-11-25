"""Cheap, rule-based filtering before any LLM scoring."""
from __future__ import annotations

import re

from .models import Creator, Criteria, Post

# Promo-for-hire bios ("DM for collab", "open for paid collaborations"). The user rejected these
# accounts on 2026-11-25: they read as paid-promo / follow-for-follow accounts, so they are dropped
# before scoring.
HIRE_BIO = re.compile(
    r"\bdm\b[^|\n]{0,15}\b(for|4)\b[^|\n]{0,20}\b(collab|promo|promotion|paid|partnership|sponsor)"
    r"|\bopen (to|for) (paid )?(collab|promo|partnership)"
    r"|\bpaid (collab|promo|promotion|partnership)", re.I)
# Follow-for-follow: following count close to (or above) the follower count.
F4F_RATIO = 0.8


def hire_bio(bio: str) -> bool:
    return bool(HIRE_BIO.search(bio or ""))


def follow_for_follow(c: Creator) -> bool:
    return c.following > 0 and c.followers >= 1000 and c.following >= c.followers * F4F_RATIO


def merge(found: dict[str, Creator], creator: Creator, tweet: Post, query: str) -> None:
    """Group search hits by platform + author (case-insensitive)."""
    key = creator.key
    if key not in found:
        found[key] = creator
    c = found[key]
    if all(t.id != tweet.id for t in c.tweets):
        c.tweets.append(tweet)
    c.matched_queries.add(query)
    if tweet.lang and not c.lang:
        c.lang = tweet.lang


def passes(c: Creator, criteria: Criteria, known: set[str], prefiltered: bool = False) -> bool:
    if c.key in known:
        return False
    if c.followers < criteria.min_followers:
        return False
    if criteria.max_followers and c.followers > criteria.max_followers:
        return False
    if criteria.language and c.lang and c.lang != criteria.language:
        return False
    if not prefiltered and c.avg_likes < criteria.min_avg_likes:
        return False
    if hire_bio(c.bio) or follow_for_follow(c):
        return False
    return True


def rank(creators: list[Creator]) -> list[Creator]:
    """More matched queries and more engagement first."""
    return sorted(creators, key=lambda c: (len(c.matched_queries), c.relevance, c.avg_likes), reverse=True)
