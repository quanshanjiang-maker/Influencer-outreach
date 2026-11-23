"""Step 1 pipeline: criteria -> queries -> search -> prefilter -> Candidates sheet."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from . import prefilter
from .models import Creator, Criteria
from .sources import XSource

log = logging.getLogger(__name__)


@dataclass
class SearchResult:
    criteria: Criteria
    queries: list[str]
    tweets_fetched: int
    creators_seen: int
    candidates: list[Creator]


def run_search(
    source: XSource,
    criteria: Criteria,
    queries: list[str],
    known: set[str],
    pages_per_query: int,
    tweet_budget: int,
) -> SearchResult:
    found: dict[str, Creator] = {}
    fetched = 0
    for q in queries:
        if fetched >= tweet_budget:
            log.warning("Tweet budget %s reached, skipping remaining queries", tweet_budget)
            break
        log.info("search: %s", q)
        try:
            for creator, tweet in source.search(q, max_pages=pages_per_query):
                fetched += 1
                prefilter.merge(found, creator, tweet, q)
                if fetched >= tweet_budget:
                    break
        except Exception as e:  # one bad query should not kill the run
            log.error("query failed (%s): %s", q, e)
    kept = [c for c in found.values() if prefilter.passes(c, criteria, known)]
    kept = prefilter.rank(kept)[: criteria.max_candidates]
    return SearchResult(criteria, queries, fetched, len(found), kept)
