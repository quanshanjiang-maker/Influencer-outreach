"""Turn plain-language keywords into X advanced-search queries with Claude."""
from __future__ import annotations

from datetime import date

import anthropic
from pydantic import BaseModel

from .models import Criteria

COMMON = """You write search queries to find content creators on {platform}.
- Cover synonyms, product names, community slang and common hashtags for the topic.
- Prefer queries that surface creators who post original content about the topic,
  not news accounts, brands or giveaways.
- Return exactly the number of queries requested, all different.
"""

PLATFORM_RULES = {
    "x": """- Each query is one string valid in the x.com search box (advanced-search syntax).
- Use -filter:replies -filter:retweets, add lang:<code> when a language is given,
  and min_faves:<n> to skip low-signal posts. Do not use since:/until:.""",
    "youtube": """- Each query is plain words as typed into YouTube search (no operators).
- Favour phrasing creators use in titles: "review", "tutorial", "vs", "how to".""",
    "instagram": """- Each query is a single hashtag starting with # (no spaces), e.g. #aivideo.
- Mix broad and niche hashtags; avoid generic ones like #love or #instagood.""",
    "tiktok": """- Mix single hashtags starting with # (no spaces) and short keyword phrases.
- Use the words TikTok creators put in captions.""",
}

NAMES = {"x": "X (Twitter)", "youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok"}


class Queries(BaseModel):
    queries: list[str]


def expand_queries(client: anthropic.Anthropic, model: str, criteria: Criteria, n: int,
                   platform: str = "x") -> list[str]:
    system = COMMON.format(platform=NAMES[platform]) + PLATFORM_RULES[platform]
    prompt = (
        f"Topic keywords: {criteria.keywords}\n"
        f"What kind of creators we want: {criteria.description or '(not given)'}\n"
        + (f"Targeting rules (for context; the scorer enforces them): {criteria.rules[:1500]}\n"
           if criteria.rules.strip() else "")
        + f"Language: {criteria.language or 'any'}\n"
        f"Number of queries: {n}\n"
        f"Today's date: {date.today().isoformat()} (if a query names a year, use this one)"
    )
    resp = client.messages.parse(
        model=model,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=Queries,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return [_fallback_query(criteria, platform)]
    seen, out = set(), []
    for q in resp.parsed_output.queries:
        q = q.strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:n] or [_fallback_query(criteria, platform)]


def _fallback_query(criteria: Criteria, platform: str = "x") -> str:
    if platform == "instagram":
        return "#" + "".join(criteria.keywords.split()).lower()
    if platform != "x":
        return criteria.keywords
    q = f"{criteria.keywords} -filter:replies -filter:retweets"
    if criteria.language:
        q += f" lang:{criteria.language}"
    return q
