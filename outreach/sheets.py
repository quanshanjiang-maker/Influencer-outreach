"""Google Sheets storage: criteria in, candidates out."""
from __future__ import annotations

from datetime import date

import gspread

from .models import PLATFORMS, Creator, Criteria

CRITERIA_HEADERS = [
    "enabled", "name", "platforms", "keywords", "description", "language",
    "min_followers", "max_followers", "min_avg_likes", "max_candidates",
]

CANDIDATE_HEADERS = [
    "date", "criteria", "platform", "username", "profile_url", "followers", "avg_likes",
    "language", "bio", "website", "matched_query", "top_tweet_url",
    "score", "score_reason", "tags",
    "email", "email_source", "email_status", "opener",
    "send_from", "status", "thread_id", "reply_category", "reply_summary", "notes",
]

OUTREACH_HEADERS = [
    "sent_at", "platform", "username", "email", "send_from", "subject", "thread_id",
    "followup_count", "last_event", "last_event_at",
]

TEMPLATE_HEADERS = ["name", "subject", "body"]

EXAMPLE_CRITERIA = [
    "TRUE", "ai-video", "x,youtube", "AI video tools",
    "Creators who review or teach AI video generation tools", "en",
    "5000", "200000", "20", "200",
]

EXAMPLE_TEMPLATE = [
    "default",
    "Collab idea for {name}",
    "Hi {name},\n\n{opener}\n\n<your pitch here>\n\nBest,\n<your name>\n\n"
    "(Reply 'unsubscribe' and I won't email again.)",
]


def _truthy(v) -> bool:
    return str(v).strip().lower() in {"true", "yes", "1", "y", "是"}


def _int(v, default=0) -> int:
    try:
        return int(float(str(v).replace(",", "").strip()))
    except ValueError:
        return default


class Sheet:
    def __init__(self, service_account: dict, sheet_id: str, tabs: dict):
        if not service_account or not sheet_id:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON and SHEET_ID must be set")
        self.gc = gspread.service_account_from_dict(service_account)
        self.book = self.gc.open_by_key(sheet_id)
        self.tabs = {
            "criteria": tabs.get("criteria", "Criteria"),
            "candidates": tabs.get("candidates", "Candidates"),
            "outreach": tabs.get("outreach", "Outreach"),
            "templates": tabs.get("templates", "Templates"),
        }

    # --- setup ---------------------------------------------------------
    def setup(self) -> list[str]:
        """Create any missing tabs with headers. Never touches existing data."""
        existing = {ws.title for ws in self.book.worksheets()}
        plan = [
            ("criteria", CRITERIA_HEADERS, [EXAMPLE_CRITERIA]),
            ("candidates", CANDIDATE_HEADERS, []),
            ("outreach", OUTREACH_HEADERS, []),
            ("templates", TEMPLATE_HEADERS, [EXAMPLE_TEMPLATE]),
        ]
        created = []
        for key, headers, rows in plan:
            title = self.tabs[key]
            if title in existing:
                continue
            ws = self.book.add_worksheet(title=title, rows=1000, cols=len(headers))
            ws.append_rows([headers, *rows], value_input_option="RAW")
            ws.freeze(rows=1)
            created.append(title)
        return created

    # --- criteria ------------------------------------------------------
    def read_criteria(self) -> list[Criteria]:
        ws = self.book.worksheet(self.tabs["criteria"])
        out = []
        for r in ws.get_all_records():
            if not _truthy(r.get("enabled", "TRUE")) or not str(r.get("keywords", "")).strip():
                continue
            platforms = [p.strip().lower() for p in str(r.get("platforms") or "x").split(",") if p.strip()]
            bad = [p for p in platforms if p not in PLATFORMS]
            if bad:
                raise ValueError(f"Unknown platform(s) {bad} in Criteria row {r.get('name')}; use {PLATFORMS}")
            out.append(Criteria(
                name=str(r.get("name") or r.get("keywords")),
                keywords=str(r["keywords"]),
                description=str(r.get("description", "")),
                language=str(r.get("language", "")).strip(),
                min_followers=_int(r.get("min_followers")),
                max_followers=_int(r.get("max_followers")),
                min_avg_likes=float(_int(r.get("min_avg_likes"))),
                max_candidates=_int(r.get("max_candidates"), 200) or 200,
                platforms=platforms,
            ))
        return out

    # --- candidates ----------------------------------------------------
    def known_creators(self) -> set[str]:
        """Keys like 'x:alice' for every creator already in Candidates."""
        ws = self.book.worksheet(self.tabs["candidates"])
        rows = ws.get_all_records()
        return {
            f"{str(r.get('platform') or 'x').lower()}:{str(r.get('username')).strip().lower().lstrip('@')}"
            for r in rows if str(r.get("username", "")).strip()
        }

    def append_candidates(self, criteria: Criteria, creators: list[Creator]) -> int:
        if not creators:
            return 0
        today = date.today().isoformat()
        rows = []
        for c in creators:
            top = c.top_tweet
            row = {
                "date": today,
                "criteria": criteria.name,
                "platform": c.platform,
                "username": c.username,
                "profile_url": c.profile_url,
                "followers": c.followers,
                "avg_likes": round(c.avg_likes, 1),
                "language": c.lang,
                "bio": c.bio,
                "website": c.website,
                "matched_query": " | ".join(sorted(c.matched_queries))[:500],
                "top_tweet_url": top.url if top else "",
                "status": "new",
            }
            rows.append([row.get(h, "") for h in CANDIDATE_HEADERS])
        ws = self.book.worksheet(self.tabs["candidates"])
        ws.append_rows(rows, value_input_option="RAW")
        return len(rows)
