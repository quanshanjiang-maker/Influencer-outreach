"""Google Sheets storage: criteria in, candidates out."""
from __future__ import annotations

from datetime import date

import gspread
from gspread.utils import rowcol_to_a1

from .models import PLATFORMS, Creator, Criteria

CRITERIA_HEADERS = [
    "enabled", "name", "platforms", "regions", "pitch", "keywords", "description", "language",
    "min_followers", "max_followers", "min_avg_likes", "max_candidates", "rules",
    "queries", "since_days", "pages_per_query",
]

CANDIDATE_HEADERS = [
    "date", "criteria", "platform", "username", "profile_url", "followers", "avg_likes",
    "language", "bio", "website", "matched_query", "top_tweet_url",
    "score", "score_reason", "tags",
    "email", "email_source", "email_status", "opener",
    "send_from", "status", "thread_id", "reply_category", "reply_summary", "notes",
    "sent_at", "followup_count", "message_id",
    "price_post", "price_thread", "price_retweet", "price_quote", "leader_review", "leader_note",
    "icp_fit", "location", "account_created", "dm_open",
    "competitor", "competitor_post", "competitor_post_date", "competitor_post_text", "avg_views",
    "avg_replies", "median_replies", "template",
]

# X rates: a plain post, a thread, a retweet and a quote post (quote tweet).
PRICE_COLUMNS = ["price_post", "price_thread", "price_retweet", "price_quote"]

# Leader review: one Candidates table, a dropdown column and two saved filter views.
# A row shows up for the leader as soon as any price is filled and the leader hasn't decided yet.
# The tool only fills empty price cells from replies and never touches leader_review / leader_note.
REVIEW_COLUMN = "leader_review"
REVIEW_PENDING, REVIEW_YES, REVIEW_NO = "待审", "通过", "不要"
REVIEW_OPTIONS = [REVIEW_PENDING, REVIEW_YES, REVIEW_NO]
# Columns the tool fills for itself; hidden by setup-sheet so the reviewer sees a short table.
# Hiding never affects the tool: it reads and writes columns by header name.
HIDDEN_COLUMNS = ["date", "criteria", "language", "matched_query", "top_tweet_url", "email_source", "account_created",
                  "email_status", "opener", "send_from", "thread_id", "reply_category", "sent_at",
                  "followup_count", "message_id", "competitor_post_text"]
LEADER_VIEW, APPROVED_VIEW = "Leader 审批（待审）", "推进中（通过）"


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
    "Hi {name},\n\n{opener}\n\n<your pitch here>\n\n"
    "If you're open to it, could you share your rates for a post, a thread, a retweet and a quote post?\n\nBest,\n<your name>\n\n"
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


def parse_queries(text: str) -> list[tuple[str, str]]:
    """One search per line, "Label: query" (the label is optional)."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        label, sep, q = line.partition(": ")
        out.append((label.strip(), q.strip()) if sep and q.strip() else ("", line))
    return out


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
        ws = self.book.worksheet(self.tabs["candidates"])
        header = [h.strip() for h in ws.row_values(1)]
        if "quote" in header and "price_post" not in header:  # older single price column
            ws.update(range_name=rowcol_to_a1(1, header.index("quote") + 1), values=[["price_post"]],
                      value_input_option="RAW")
            self._cols.pop("candidates", None)
        cols = self._columns("candidates", CANDIDATE_HEADERS)
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
        for name in HIDDEN_COLUMNS:
            if name in cols:
                i = cols.index(name)
                requests.append({"updateDimensionProperties": {
                    "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                    "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
        added = []
        score = cols.index("score") if "score" in cols else None

        def col(name):  # "$X2": absolute column, first data row
            return "$" + rowcol_to_a1(2, cols.index(name) + 1)

        prices = ",".join(f"LEN({col(p)})>0" for p in PRICE_COLUMNS)
        review = col(REVIEW_COLUMN)
        formulas = {
            LEADER_VIEW: f'=AND(OR({prices}),{review}<>"{REVIEW_YES}",{review}<>"{REVIEW_NO}")',
            APPROVED_VIEW: f'={review}="{REVIEW_YES}"',
        }
        ids = {v.get("title"): v.get("filterViewId") for v in mine.get("filterViews", [])}
        for title, formula in formulas.items():
            view = {"title": title, "range": {"sheetId": sid, "startRowIndex": 0, "startColumnIndex": 0,
                                              "endColumnIndex": len(cols)},
                    "filterSpecs": [{"columnIndex": c, "filterCriteria": {"condition": {
                        "type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]}}}]}
            if score is not None:
                view["sortSpecs"] = [{"dimensionIndex": score, "sortOrder": "DESCENDING"}]
            if title in ids:
                view["filterViewId"] = ids[title]
                requests.append({"updateFilterView": {"filter": view, "fields": "range,filterSpecs,sortSpecs"}})
            else:
                requests.append({"addFilterView": {"filter": view}})
                added.append(f"filter view '{title}'")
        self.book.batch_update({"requests": requests})
        return added

    # --- criteria ------------------------------------------------------
    def read_criteria(self, include_disabled: bool = False) -> list[Criteria]:
        """Enabled Criteria rows (for search). Scoring passes include_disabled=True so rows found
        under a criteria that was later switched off are still judged by its own rules."""
        ws = self.book.worksheet(self.tabs["criteria"])
        out = []
        for r in ws.get_all_records():
            off = not _truthy(r.get("enabled", "TRUE")) and not include_disabled
            if off or not str(r.get("keywords", "")).strip():
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
                rules=str(r.get("rules", "") or ""),
                queries=parse_queries(str(r.get("queries", "") or "")),
                since_days=_int(r.get("since_days")),
                pages_per_query=_int(r.get("pages_per_query")),
            ))
        return out

    def upsert_criteria(self, row: dict, only: bool = False) -> str:
        """Write one Criteria row matched by name; with only=True disable every other row."""
        cols = self._columns("criteria", CRITERIA_HEADERS)
        rows = self.read_tab("criteria", CRITERIA_HEADERS)
        name = str(row["name"]).strip()
        match = next((n for n, r in rows if str(r.get("name", "")).strip() == name), None)
        values = {k: ("TRUE" if v is True else "FALSE" if v is False else str(v)) for k, v in row.items()}
        values.setdefault("enabled", "TRUE")
        unknown = [k for k in values if k not in cols]
        if unknown:
            raise ValueError(f"Unknown Criteria columns: {unknown}")
        if match is None:
            self.append_tab("criteria", CRITERIA_HEADERS, [values])
        else:
            self.update_tab("criteria", CRITERIA_HEADERS, [(match, values)])
        if only:
            self.update_tab("criteria", CRITERIA_HEADERS,
                            [(n, {"enabled": "FALSE"}) for n, r in rows
                             if str(r.get("name", "")).strip() != name and _truthy(r.get("enabled", "TRUE"))])
        return "updated" if match else "added"

    def archive_candidates(self, platform: str, dry_run: bool = False) -> tuple[int, str]:
        """Copy the whole Candidates tab to a dated archive tab, then delete that platform's rows."""
        rows = self.read_candidates()
        doomed = [n for n, r in rows if str(r.get("platform", "")).strip().lower() == platform]
        title = f"Archive {platform} {date.today().isoformat()}"
        if dry_run or not doomed:
            return len(doomed), title
        ws = self.book.worksheet(self.tabs["candidates"])
        existing = {w.title for w in self.book.worksheets()}
        if title not in existing:
            self.book.duplicate_sheet(ws.id, new_sheet_name=title, insert_sheet_index=len(existing))
        # delete bottom-up in contiguous blocks so row numbers stay valid
        blocks, start, prev = [], None, None
        for n in sorted(doomed):
            if start is None:
                start = prev = n
            elif n == prev + 1:
                prev = n
            else:
                blocks.append((start, prev))
                start = prev = n
        blocks.append((start, prev))
        for a, b in reversed(blocks):
            ws.delete_rows(a, b)
        return len(doomed), title

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
                "location": c.location,
                "account_created": c.account_created,
                "dm_open": c.dm_open,
                "competitor": c.competitor,
                "competitor_post": c.competitor_post,
                "competitor_post_date": c.competitor_post_date,
                "competitor_post_text": c.competitor_post_text[:500],
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
        """Columns are found by header name, so users may reorder or add columns."""
        return self.update_tab("candidates", CANDIDATE_HEADERS, updates)

    # --- generic tab access -------------------------------------------
    def read_tab(self, key: str, headers: list[str]) -> list[tuple[int, dict]]:
        self._columns(key, headers)
        return [(i + 2, r) for i, r in enumerate(self.book.worksheet(self.tabs[key]).get_all_records())]

    def append_tab(self, key: str, headers: list[str], records: list[dict]) -> int:
        if not records:
            return 0
        cols = self._columns(key, headers)
        self.book.worksheet(self.tabs[key]).append_rows(
            [[r.get(h, "") for h in cols] for r in records], value_input_option="RAW")
        return len(records)

    def update_tab(self, key: str, headers: list[str], updates: list[tuple[int, dict]]) -> int:
        """Write {column: value} changes for many rows in one request, finding columns by header name."""
        cols = self._columns(key, headers)
        data = [{"range": rowcol_to_a1(row, cols.index(col) + 1), "values": [[value]]}
                for row, changes in updates for col, value in changes.items()]
        if data:
            self.book.worksheet(self.tabs[key]).batch_update(data, value_input_option="RAW")
        return len(updates)

    def sort_candidates(self, by: str = "score", first: int | None = None, last: int | None = None) -> int:
        """Sort whole data rows by one column, highest first; empty cells go to the bottom.
        With first/last, only that sheet row range is sorted (one search batch), so the
        row numbers of other batches stay the same."""
        cols = self._columns("candidates", CANDIDATE_HEADERS)
        ws = self.book.worksheet(self.tabs["candidates"])
        n = len(ws.col_values(1))
        first = max(first or 2, 2)
        last = min(last or n, n)
        if last - first < 1:
            return max(last - first + 1, 0)
        ws.sort((cols.index(by) + 1, "des"), range=f"{rowcol_to_a1(first, 1)}:{rowcol_to_a1(last, len(cols))}")
        return last - first + 1

    def move_blocked_last(self, first: int, last: int, order: list[str] | None = None) -> list[tuple[str, int]]:
        """Within sheet rows first..last, group rows by status in the given order (default: every
        status except "blocked", then "blocked"); "*" stands for any status not named. Each group
        keeps its current order. Returns [(group, rows)] in sheet order."""
        order = [("*" if o.strip().lower() == "rest" else o.strip().lower()) for o in (order or ["*", "blocked"])]
        if "*" not in order:  # never drop rows whose status isn't named
            order.append("*")
        cols = self._columns("candidates", CANDIDATE_HEADERS)
        ws = self.book.worksheet(self.tabs["candidates"])
        rng = f"{rowcol_to_a1(first, 1)}:{rowcol_to_a1(last, len(cols))}"
        values = ws.get(rng, value_render_option="UNFORMATTED_VALUE")
        values += [[] for _ in range(last - first + 1 - len(values))]
        values = [v + [""] * (len(cols) - len(v)) for v in values]
        i = cols.index("status")
        key = lambda v: str(v[i]).strip().lower() if str(v[i]).strip().lower() in order else "*"
        groups = [(o, [v for v in values if key(v) == o]) for o in order]
        ws.update(range_name=rng, values=[v for _, g in groups for v in g], value_input_option="RAW")
        return [(o, len(g)) for o, g in groups]

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

    def upsert_template(self, name: str, subject: str, body: str) -> str:
        """Add or replace one row of the Templates tab, matched by name."""
        rows = self.read_tab("templates", TEMPLATE_HEADERS)
        match = next((n for n, r in rows if str(r.get("name", "")).strip() == name), None)
        values = {"name": name, "subject": subject, "body": body}
        if match is None:
            self.append_tab("templates", TEMPLATE_HEADERS, [values])
            return "added"
        self.update_tab("templates", TEMPLATE_HEADERS, [(match, values)])
        return "updated"

    def read_templates(self) -> dict[str, tuple[str, str]]:
        """{name: (subject, body)} from the Templates tab."""
        out = {}
        for r in self.book.worksheet(self.tabs["templates"]).get_all_records():
            name = str(r.get("name", "")).strip()
            if name:
                out[name] = (str(r.get("subject", "")), str(r.get("body", "")))
        return out
