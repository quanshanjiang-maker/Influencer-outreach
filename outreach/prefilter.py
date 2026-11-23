"""Cheap, rule-based filtering before any LLM scoring."""
from __future__ import annotations

from .models import Creator, Criteria, Post


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


def passes(c: Creator, criteria: Criteria, known: set[str]) -> bool:
    if c.key in known:
        return False
    if c.followers < criteria.min_followers:
        return False
    if criteria.max_followers and c.followers > criteria.max_followers:
        return False
    if criteria.language and c.lang and c.lang != criteria.language:
        return False
    if c.avg_likes < criteria.min_avg_likes:
        return False
    return True


def rank(creators: list[Creator]) -> list[Creator]:
    """More matched queries and more engagement first."""
    return sorted(creators, key=lambda c: (len(c.matched_queries), c.avg_likes), reverse=True)
