"""Google Sheets storage: criteria in, candidates out."""
from __future__ import annotations

from datetime import date

import gspread
from gspread.utils import rowcol_to_a1

from .models import PLATFORMS, Creator, Criteria

CRITERIA_HEADERS = [
    "enabled", "name", "platforms", "regions", "pitch", "keywords", "description", "language",
    "min_followers", "max_followers", "min_avg_likes", "max_candidates",
]

CANDIDATE_HEADERS = [
    "date", "criteria", "platform", "username", "profile_url", "followers", "avg_likes",
    "language", "bio", "website", "matched_query", "top_tweet_url",
    "score", "score_reason", "tags",
    "email", "email_source", "email_status", "opener",
    "send_from", "status", "thread_id", "reply_category", "reply_summary", "notes",
    "sent_at", "followup_count", "message_id",
    "quote", "leader_review", "leader_note",
]

# Leader review: one Candidates table, a dropdown column and two saved filter views.
# The tool never overwrites these columns except to mark a new price reply as pending review.
REVIEW_COLUMN = "leader_review"
REVIEW_PENDING, REVIEW_YES, REVIEW_NO = "待审", "通过", "不要"
REVIEW_OPTIONS = [REVIEW_PENDING, REVIEW_YES, REVIEW_NO]
REVIEW_VIEWS = {  # filter view title -> leader_review value it shows
    "Leader 审批（待审）": REVIEW_PENDING,
    "推进中（通过）": REVIEW_YES,
}

OUTREACH_HEADERS = [
    "sent_at", "platform", "username", "email", "send_from", "subject", "thread_id",
    "followup_count", "last_event", "last_event_at",
]

TEMPLATE_HEADERS = ["name", "subject", "body"]

EXAMPLE_CRITERIA = [
    "TRUE", "ai-video", "x,youtube", "US,GB",
    "We make an AI video editor and offer creators paid reviews plus an affiliate deal.",
    "AI video tools",
    "Creators who review or teach AI video generation tools", "en",
    "5000", "200000", "20", "200",
]

EXAMPLE_TEMPLATE = [
    "default",
    "Collab idea for {name}",
    "Hi {name},\n\n{opener}\n\n<your pitch here>\n\nBest,\n<your name>\n\n"
    "(Reply 'unsubscribe' and I won't email again.)",
]

EXAMPLE_FOLLOWUP = [
    "followup",
    "Re: Collab idea for {name}",
    "Hi {name},\n\nJust bumping this in case it got buried. Happy to share details or send a sample.\n\n"
    "Best,\n<your name>\n\n(Reply 'unsubscribe' and I won't email again.)",
]


def _truthy(v) -> bool:
    return str(v).strip().lower() in {"true", "yes", "1", "y", "是"}


def _int(v, default=0) -> int:
    try:
        return int(float(str(v).replace(",", "").strip()))
    except ValueError:
        return default


class Sheet:
    def __init__(self, service_account: dict | None, sheet_id: str, tabs: dict, oauth: dict | None = None):
        if not sheet_id or not (service_account or oauth):
            raise ValueError("Set SHEET_ID and either GOOGLE_SERVICE_ACCOUNT_JSON or "
                             "GOOGLE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET")
        if service_account:
            self.gc = gspread.service_account_from_dict(service_account)
        else:
            from google.oauth2.credentials import Credentials
            creds = Credentials(None, refresh_token=oauth["refresh_token"], client_id=oauth["client_id"],
                                client_secret=oauth["client_secret"],
                                token_uri="https://oauth2.googleapis.com/token",
                                scopes=["https://www.googleapis.com/auth/spreadsheets"])
            self.gc = gspread.authorize(creds)
        self.book = self.gc.open_by_key(sheet_id)
        self._pitch: dict[str, str] = {}
        self._cols: dict[str, list[str]] = {}
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
            ("templates", TEMPLATE_HEADERS, [EXAMPLE_TEMPLATE, EXAMPLE_FOLLOWUP]),
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
        created += self.setup_review()
        return created

    def setup_review(self) -> list[str]:
        """Add the leader review dropdown, colors and filter views to Candidates (idempotent)."""
        cols = self._columns("candidates", CANDIDATE_HEADERS)
        ws = self.book.worksheet(self.tabs["candidates"])
        sid, c = ws.id, cols.index(REVIEW_COLUMN)
        meta = self.book.fetch_sheet_metadata(params={"fields": "sheets(properties.sheetId,filterViews,conditionalFormats)"})
        mine = next((x for x in meta.get("sheets", []) if x["properties"]["sheetId"] == sid), {})
        have_views = {v.get("title") for v in mine.get("filterViews", [])}
        column = {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": c, "endColumnIndex": c + 1}
        requests: list[dict] = [{"setDataValidation": {"range": column, "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in REVIEW_OPTIONS]},
            "showCustomUi": True, "strict": True}}}]
        if not any(any(r.get("startColumnIndex") == c for r in f.get("ranges", []))
                   for f in mine.get("conditionalFormats", [])):
            for value, rgb in ((REVIEW_YES, (0.85, 0.94, 0.83)), (REVIEW_NO, (0.9, 0.9, 0.9)),
                               (REVIEW_PENDING, (1.0, 0.95, 0.8))):
                requests.append({"addConditionalFormatRule": {"index": 0, "rule": {
                    "ranges": [column],
                    "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": value}]},
                                    "format": {"backgroundColor": dict(zip(("red", "green", "blue"), rgb))}}}}})
        added = []
        score = cols.index("score") if "score" in cols else None
        for title, value in REVIEW_VIEWS.items():
            if title in have_views:
                continue
            view = {"title": title, "range": {"sheetId": sid, "startRowIndex": 0, "startColumnIndex": 0,
                                              "endColumnIndex": len(cols)},
                    "filterSpecs": [{"columnIndex": c, "filterCriteria": {"condition": {
                        "type": "TEXT_EQ", "values": [{"userEnteredValue": value}]}}}]}
            if score is not None:
                view["sortSpecs"] = [{"dimensionIndex": score, "sortOrder": "DESCENDING"}]
            requests.append({"addFilterView": {"filter": view}})
            added.append(f"filter view '{title}'")
        self.book.batch_update({"requests": requests})
        return added

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
            self._pitch[str(r.get("name") or r.get("keywords"))] = str(r.get("pitch", "") or "")
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
                regions=[x.strip().upper() for x in str(r.get("regions") or "").split(",") if x.strip()],
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
                "email": c.email,
                "email_source": c.email_source,
                "score_reason": c.match_reason,
                "status": "new",
            }
            rows.append(row)
        ws = self.book.worksheet(self.tabs["candidates"])
        cols = self._columns("candidates", CANDIDATE_HEADERS)
        ws.append_rows([[r.get(h, "") for h in cols] for r in rows], value_input_option="RAW")
        return len(rows)

    def pitch_for(self, criteria_name: str) -> str:
        return self._pitch.get(criteria_name, "")

    def read_candidates(self) -> list[tuple[int, dict]]:
        """(sheet row number, record) for every candidate row."""
        ws = self.book.worksheet(self.tabs["candidates"])
        return [(i + 2, r) for i, r in enumerate(ws.get_all_records())]

    def update_candidates(self, updates: list[tuple[int, dict]]) -> int:
        """Write {column: value} changes for many rows in one request.
        Columns are found by header name, so users may reorder or add columns."""
        cols = self._columns("candidates", CANDIDATE_HEADERS)
        data = []
        for row, changes in updates:
            for col, value in changes.items():
                data.append({"range": rowcol_to_a1(row, cols.index(col) + 1), "values": [[value]]})
        if data:
            self.book.worksheet(self.tabs["candidates"]).batch_update(data, value_input_option="RAW")
        return len(updates)

    # --- columns -------------------------------------------------------
    def _columns(self, key: str, required: list[str]) -> list[str]:
        """Header row of a tab; appends any required header that is missing
        (so sheets created by older versions keep working)."""
        if key in self._cols:
            return self._cols[key]
        ws = self.book.worksheet(self.tabs[key])
        header = [h.strip() for h in ws.row_values(1)]
        missing = [h for h in required if h not in header]
        if missing:
            start = len(header) + 1
            if ws.col_count < start + len(missing) - 1:
                ws.add_cols(start + len(missing) - 1 - ws.col_count)
            ws.update(range_name=rowcol_to_a1(1, start), values=[missing], value_input_option="RAW")
            header += missing
        self._cols[key] = header
        return header

    # --- outreach log & templates -------------------------------------
    def read_outreach(self) -> list[dict]:
        return self.book.worksheet(self.tabs["outreach"]).get_all_records()

    def append_outreach(self, records: list[dict]) -> int:
        if not records:
            return 0
        cols = self._columns("outreach", OUTREACH_HEADERS)
        self.book.worksheet(self.tabs["outreach"]).append_rows(
            [[r.get(h, "") for h in cols] for r in records], value_input_option="RAW")
        return len(records)

    def read_templates(self) -> dict[str, tuple[str, str]]:
        """{name: (subject, body)} from the Templates tab."""
        out = {}
        for r in self.book.worksheet(self.tabs["templates"]).get_all_records():
            name = str(r.get("name", "")).strip()
            if name:
                out[name] = (str(r.get("subject", "")), str(r.get("body", "")))
        return out
