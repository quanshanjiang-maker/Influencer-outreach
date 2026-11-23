"""Turn plain-language keywords into X advanced-search queries with Claude."""
from __future__ import annotations

import anthropic
from pydantic import BaseModel

from .models import Criteria

SYSTEM = """You write X (Twitter) advanced-search queries to find content creators.
Rules:
- Each query is one string valid in the x.com search box.
- Cover synonyms, product names, community slang and common hashtags for the topic.
- Prefer queries that surface creators who post original content about the topic,
  not news bots or giveaways. Use -filter:replies -filter:retweets.
- Add lang:<code> when a language is given, and min_faves:<n> to skip low-signal posts.
- Do not use since:/until: (the tool adds date limits itself).
- Return exactly the number of queries requested, all different."""


class Queries(BaseModel):
    queries: list[str]


def expand_queries(client: anthropic.Anthropic, model: str, criteria: Criteria, n: int) -> list[str]:
    prompt = (
        f"Topic keywords: {criteria.keywords}\n"
        f"What kind of creators we want: {criteria.description or '(not given)'}\n"
        f"Language: {criteria.language or 'any'}\n"
        f"Number of queries: {n}"
    )
    resp = client.messages.parse(
        model=model,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_format=Queries,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return [_fallback_query(criteria)]
    seen, out = set(), []
    for q in resp.parsed_output.queries:
        q = q.strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:n] or [_fallback_query(criteria)]


def _fallback_query(criteria: Criteria) -> str:
    q = f"{criteria.keywords} -filter:replies -filter:retweets"
    if criteria.language:
        q += f" lang:{criteria.language}"
    return q
