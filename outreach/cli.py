"""Command line entry point.

    python -m outreach setup-sheet
    python -m outreach search [--dry-run] [--criteria NAME]
    python -m outreach score [--dry-run] [--limit N]
    python -m outreach emails [--dry-run] [--limit N]
    python -m outreach approve --handles alice,youtube:bob | --min-score 8 [--followups]
    python -m outreach send [--dry-run] [--max N]
    python -m outreach replies [--dry-run]
    python -m outreach slack digest | poll | listen
    python -m outreach gmail-auth --client-secret client_secret.json
    python -m outreach search --keywords "AI video tools" --lang en   # no sheet needed
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys

from .config import load_config


def cmd_setup_sheet(cfg, args) -> int:
    from .sheets import Sheet
    sheet = Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs, oauth=cfg.google_oauth)
    created = sheet.setup()
    print("Created: " + (", ".join(created) if created else "nothing new (tabs and review views already exist)"))
    return 0


def cmd_search(cfg, args) -> int:
    import anthropic

    from .expand import expand_queries
    from .search import run_search
    from .sheets import Sheet
    from .sources import get_source

    from .models import Criteria

    sheet = None
    if args.keywords:  # quick test without a sheet: implies --dry-run
        args.dry_run = True
        criteria_list = [Criteria(name="cli", keywords=args.keywords, language=args.lang or "",
                                  min_followers=args.min_followers, max_candidates=50,
                                  platforms=[p.strip() for p in args.platforms.split(",")])]
    else:
        sheet = Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs, oauth=cfg.google_oauth)
        criteria_list = sheet.read_criteria()
    if args.criteria:
        criteria_list = [c for c in criteria_list if c.name == args.criteria]
    if not criteria_list:
        print("No enabled rows in the Criteria tab.")
        return 1

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    known = sheet.known_creators() if sheet else set()
    budgets = {p: int(v) for p, v in (cfg.search.get("daily_result_budget") or {}).items()}
    sources = {}

    for crit, platform in [(c, p) for c in criteria_list for p in c.platforms]:
        if budgets.get(platform, 1) <= 0:
            print(f"[{crit.name}/{platform}] daily budget used up, skipping")
            continue
        try:
            source = sources.get(platform) or get_source(platform, cfg)
        except ValueError as e:
            print(f"[{crit.name}/{platform}] skipped: {e}")
            continue
        sources[platform] = source
        if hasattr(source, "language"):
            source.language = crit.language
        if hasattr(source, "regions"):
            source.regions = crit.regions
            source.min_followers, source.max_followers = crit.min_followers, crit.max_followers
            source.min_avg = crit.min_avg_likes
        labels: dict[str, str] = {}
        if crit.queries:
            since = ""
            if crit.since_days and platform == "x":
                from datetime import date, timedelta
                since = f" since:{(date.today() - timedelta(days=crit.since_days)).isoformat()}"
            labels = {q + since: label for label, q in crit.queries}
            queries = list(labels)
        elif source.expands_queries:
            queries = expand_queries(
                client, cfg.models.get("query_expansion", "claude-opus-5-5"), crit,
                int(cfg.search.get("queries_per_criteria", 12)), platform=platform,
            )
        else:
            queries = [f"{crit.description or crit.keywords} ({crit.keywords})"]
        result = run_search(
            source, crit, queries, known,
            pages_per_query=crit.pages_per_query or int(cfg.search.get("pages_per_query", 3)),
            tweet_budget=budgets.get(platform, 10**9),
        )
        if labels:
            for c in result.candidates:
                c.competitor = ", ".join(sorted({labels[q] for q in c.matched_queries if labels.get(q)}))
                top = c.top_tweet
                if top:
                    c.competitor_post, c.competitor_post_text = top.url, top.text
                    c.competitor_post_date = top.created_at
        if platform in budgets:
            budgets[platform] -= result.tweets_fetched
        print(f"[{crit.name}/{platform}] queries={len(queries)} results={result.tweets_fetched} "
              f"creators={result.creators_seen} kept={len(result.candidates)}")
        if args.dry_run:
            w = csv.writer(sys.stdout)
            w.writerow(["platform", "username", "followers", "avg_likes", "matched_queries", "bio"])
            for c in result.candidates:
                w.writerow([c.platform, c.username, c.followers, round(c.avg_likes, 1),
                            len(c.matched_queries), c.bio.replace("\n", " ")[:120]])
        else:
            n = sheet.append_candidates(crit, result.candidates)
            print(f"  wrote {n} rows to {sheet.tabs['candidates']}")
        known |= {c.key for c in result.candidates}
    return 0


def cmd_score(cfg, args) -> int:
    import anthropic

    from .score import ScoreInput, assess_many, post_line
    from .sheets import Sheet
    from .sources import get_source

    sc = cfg.scoring or {}
    min_score = int(sc.get("min_score", 7))
    limit = args.limit or int(sc.get("max_per_run", 1000))
    sheet = Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs, oauth=cfg.google_oauth)
    crits = {c.name: c for c in sheet.read_criteria()}
    briefs = {n: f"{c.keywords}. {c.description}".strip() for n, c in crits.items()}

    todo = [(row, r) for row, r in sheet.read_candidates()
            if str(r.get("status", "")).strip() == "new" and str(r.get("score", "")).strip() == ""]
    if args.criteria:
        todo = [(row, r) for row, r in todo if str(r.get("criteria", "")) == args.criteria]
    todo = todo[:limit]
    if not todo:
        print("No new candidates to score.")
        return 0

    sources = {}
    inputs = []
    stats: dict[int, dict] = {}
    for row, r in todo:
        platform = str(r.get("platform") or "x")
        posts = [p for p in [str(r.get("score_reason", "")), str(r.get("matched_query", ""))] if p]
        if sc.get("fetch_recent_posts", True) and platform == "x":
            try:
                src = sources.get(platform) or get_source(platform, cfg)
                sources[platform] = src
                recent = src.recent_posts(str(r["username"]), 20)
                posts = [post_line(p) for p in recent] or posts
                if recent:  # engagement on their latest posts, not just the search hits
                    stats[row] = {"avg_views": round(sum(p.views for p in recent) / len(recent)),
                                  "avg_likes": round(sum(p.likes for p in recent) / len(recent), 1)}
            except Exception as e:
                print(f"  could not fetch posts for @{r['username']}: {e}")
        if str(r.get("competitor_post_text", "")).strip():
            posts = [f"[post that matched the search, about {r.get('competitor') or 'a tracked brand'}] "
                     f"{r['competitor_post_text']}"] + posts
        inputs.append(ScoreInput(
            row=row, platform=platform, username=str(r["username"]),
            followers=int(float(r.get("followers") or 0)), bio=str(r.get("bio", "")), posts=posts,
            brief=briefs.get(str(r.get("criteria")), str(r.get("criteria", ""))),
            pitch=sheet.pitch_for(str(r.get("criteria"))),
            rules=getattr(crits.get(str(r.get("criteria"))), "rules", ""),
            profile={k: r.get(k, "") for k in ("location", "account_created", "dm_open", "website",
                                                "competitor")},
        ))

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    model = cfg.models.get("scoring", "claude-haiku-5-5")
    results = assess_many(client, model, inputs, workers=int(sc.get("workers", 8)))

    updates, kept = [], 0
    for x in inputs:
        a = results.get(x.row)
        if a is None:
            continue
        ok = a.score >= min_score and a.icp_fit != "Low"  # Low = don't contact
        kept += ok
        updates.append((x.row, {
            "score": a.score, "score_reason": a.reason, "tags": ", ".join(a.tags), "icp_fit": a.icp_fit,
            "opener": a.opener if ok else "", "status": "scored" if ok else "rejected",
            **stats.get(x.row, {}),
        }))
        if args.dry_run:
            print(f"{x.platform}:{x.username}\t{a.score}\t{a.icp_fit}\t{a.reason}\n    opener: {a.opener}")
    if not args.dry_run:
        sheet.update_candidates(updates)
    print(f"Scored {len(updates)}/{len(inputs)}; {kept} kept (score >= {min_score} and ICP fit not Low).")
    return 0


def cmd_emails(cfg, args) -> int:
    from concurrent.futures import ThreadPoolExecutor

    from .emails import SENDABLE, find_email, verify
    from .sheets import Sheet

    sheet = Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs, oauth=cfg.google_oauth)
    todo = [(row, r) for row, r in sheet.read_candidates()
            if str(r.get("status", "")).strip() == "scored" and not str(r.get("email_status", "")).strip()]
    todo = todo[: args.limit] if args.limit else todo
    if not todo:
        print("No scored candidates waiting for an email.")
        return 0

    def one(item):
        row, r = item
        res = find_email(str(r.get("email", "")), str(r.get("email_source", "")),
                         str(r.get("bio", "")), str(r.get("website", "")), cfg.hunter_api_key)
        return row, r, verify(res, cfg.millionverifier_api_key)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(one, todo))

    updates, ready = [], 0
    for row, r, res in results:
        sendable = res.status in SENDABLE
        ready += sendable
        updates.append((row, {
            "email": res.email, "email_source": res.source, "email_status": res.status,
            "status": "ready" if sendable else "no_email",
        }))
        if args.dry_run:
            print(f"{r.get('platform')}:{r.get('username')}\t{res.email or '-'}\t{res.source}\t{res.status}")
    if not args.dry_run:
        sheet.update_candidates(updates)
    print(f"Checked {len(results)}; {ready} ready to email, {len(results) - ready} need another channel (DM).")
    return 0


def _sheet(cfg):
    from .sheets import Sheet
    return Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs, oauth=cfg.google_oauth)


def cmd_approve(cfg, args) -> int:
    from .send import select_for_approval

    sheet = _sheet(cfg)
    handles = [h for h in (args.handles or "").split(",") if h.strip()]
    if not handles and args.min_score is None:
        print("Give --handles or --min-score (nothing is approved by default).")
        return 1
    skip = [h for h in (args.skip or "").split(",") if h.strip()]
    picked = select_for_approval(sheet.read_candidates(), handles, args.min_score, args.followups, skip)
    new = "followup_approved" if args.followups else "approved"
    for _, r in picked:
        print(f"{r.get('platform')}:{r.get('username')}\tscore={r.get('score')}\t{r.get('email')}")
    if not args.dry_run:
        sheet.update_candidates([(row, {"status": new}) for row, _ in picked])
    print(f"{'Would approve' if args.dry_run else 'Approved'} {len(picked)} rows -> {new}.")
    return 0


def _rotation(cfg, sheet):
    from .mail import get_mailbox
    from .send import Rotation, sent_today

    if not cfg.mailboxes:
        raise SystemExit("No mailboxes in config.yaml (see config.example.yaml, section mailboxes).")
    boxes = [(c, get_mailbox(c)) for c in cfg.mailboxes]
    return Rotation(boxes, sent_today(sheet.read_outreach()))


def cmd_send(cfg, args) -> int:
    from .send import SENDABLE_STATUSES, send_batch, suppressed

    sheet = _sheet(cfg)
    rows = sheet.read_candidates()
    todo = [(row, r) for row, r in rows if str(r.get("status", "")).strip() in SENDABLE_STATUSES]
    if not todo:
        print("Nothing approved to send.")
        return 0
    sc = cfg.sending or {}
    rot = _rotation(cfg, sheet)
    results = send_batch(
        todo, sheet.read_templates(), rot, suppressed(rows),
        max_send=args.max or int(sc.get("max_per_run", 50)),
        delay=(float(sc.get("min_delay_seconds", 60)), float(sc.get("max_delay_seconds", 180))),
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        sheet.update_candidates([(x.row, x.changes) for x in results])
        sheet.append_outreach([x.log for x in results])
    print(f"{'Would send' if args.dry_run else 'Sent'} {len(results)} of {len(todo)} approved emails.")
    return 0


def cmd_replies(cfg, args) -> int:
    from datetime import datetime, timezone

    import anthropic

    from .send import classify_reply, followup_due

    sheet = _sheet(cfg)
    sc = cfg.sending or {}
    after, max_fu = int(sc.get("followup_after_days", 4)), int(sc.get("max_followups", 1))
    sent = [(row, r) for row, r in sheet.read_candidates() if str(r.get("status", "")).strip() == "sent"]
    if not sent:
        print("No sent emails to check.")
        return 0
    rot = _rotation(cfg, sheet)
    boxes = {c["address"]: m for c, m in rot.boxes}
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    model = cfg.models.get("replies", cfg.models.get("scoring", "claude-haiku-5-5"))
    now = datetime.now(timezone.utc)
    updates, log_rows, counts = [], [], {}
    for row, r in sent:
        box, thread = boxes.get(str(r.get("send_from"))), str(r.get("thread_id", ""))
        if box is None or not thread:
            continue
        try:
            got = box.replies(thread)
        except Exception as e:
            print(f"  could not read thread for {r.get('username')}: {e}")
            continue
        change = None
        if any(x.is_bounce for x in got):
            change = {"status": "bounced", "email_status": "invalid", "reply_category": "bounce"}
        elif got:
            c = classify_reply(client, model, "\n\n".join(x.text for x in got))
            if c.category == "auto_reply":  # out-of-office: treat like no reply yet
                if followup_due(r, after, max_fu, now):
                    change = {"status": "followup_due", "reply_category": "auto_reply"}
            else:
                status = "unsubscribed" if c.category == "unsubscribe" else "replied"
                change = {"status": status, "reply_category": c.category, "reply_summary": c.summary}
                for col in ("price_post", "price_thread", "price_retweet", "price_quote"):  # fill blanks only
                    value = str(getattr(c, col, "") or "").strip()[:60]
                    if value and not str(r.get(col, "")).strip():
                        change[col] = value  # any price puts the row in the leader's review view
        elif followup_due(r, after, max_fu, now):
            change = {"status": "followup_due"}
        if change is None:
            continue
        counts[change["status"]] = counts.get(change["status"], 0) + 1
        updates.append((row, change))
        log_rows.append({"sent_at": r.get("sent_at", ""), "platform": r.get("platform", ""),
                         "username": r.get("username", ""), "email": r.get("email", ""),
                         "send_from": r.get("send_from", ""), "thread_id": thread,
                         "followup_count": r.get("followup_count", 0),
                         "last_event": change.get("reply_category") or change["status"],
                         "last_event_at": now.isoformat(timespec="seconds")})
        if args.dry_run:
            print(f"{r.get('platform')}:{r.get('username')}\t{change}")
    if not args.dry_run:
        sheet.update_candidates(updates)
        sheet.append_outreach(log_rows)
    print(f"Checked {len(sent)} threads: " + (", ".join(f"{k}={v}" for k, v in counts.items()) or "no change"))
    return 0


def cmd_criteria_import(cfg, args) -> int:
    """Add or update one Criteria row from a YAML file (keys are Criteria column names)."""
    import yaml

    row = yaml.safe_load(open(args.file, encoding="utf-8").read())
    if not isinstance(row, dict) or not row.get("name"):
        raise SystemExit("The file must be a mapping with at least a 'name'.")
    if isinstance(row.get("platforms"), list):
        row["platforms"] = ",".join(row["platforms"])
    if isinstance(row.get("regions"), list):
        row["regions"] = ",".join(row["regions"])
    if isinstance(row.get("queries"), dict):  # {label: query or [queries]}
        row["queries"] = "\n".join(f"{k}: {q}" for k, v in row["queries"].items()
                                   for q in (v if isinstance(v, list) else [v]))
    result = _sheet(cfg).upsert_criteria(row, only=args.only)
    print(f"Criteria '{row['name']}' {result}" + ("; other rows disabled." if args.only else "."))
    return 0


def cmd_template_import(cfg, args) -> int:
    """Add or replace a Templates row from a YAML file with name, subject and body."""
    import yaml

    t = yaml.safe_load(open(args.file, encoding="utf-8").read())
    if not isinstance(t, dict) or not all(t.get(k) for k in ("name", "subject", "body")):
        raise SystemExit("The file needs name, subject and body.")
    result = _sheet(cfg).upsert_template(str(t["name"]), str(t["subject"]), str(t["body"]).rstrip() + "\n")
    print(f"Template '{t['name']}' {result}.")
    return 0


def cmd_archive(cfg, args) -> int:
    """Move one platform's rows out of Candidates into a dated archive tab (a full copy)."""
    n, title = _sheet(cfg).archive_candidates(args.platform.lower(), dry_run=args.dry_run)
    if args.dry_run:
        print(f"Would copy Candidates to '{title}' and remove {n} {args.platform} rows.")
    else:
        print(f"Removed {n} {args.platform} rows; a full copy is in the '{title}' tab." if n
              else f"No {args.platform} rows to remove.")
    return 0


def cmd_test_email(cfg, args) -> int:
    """Send one test email from each mailbox to its own address (never to a creator)."""
    from .mail import get_mailbox

    if not cfg.mailboxes:
        raise SystemExit("No mailboxes in config.yaml (see config.example.yaml, section mailboxes).")
    for conf in cfg.mailboxes:
        box = get_mailbox(conf)
        sent = box.send(box.address, "Influencer Outreach test",
                        "This is a test from Influencer Outreach. If you can read it, sending works.\n"
                        "这是一封测试邮件。能看到它，说明发信已接通。")
        print(f"Sent a test email from {box.address} to itself (thread {sent.thread_id}).")
    return 0


def cmd_gmail_auth(cfg, args) -> int:
    from .mail.gmail import authorize

    token = authorize(args.client_secret)
    print("Refresh token. Store it as a secret: GOOGLE_REFRESH_TOKEN (sheet + main Gmail) "
          "or GMAILn_REFRESH_TOKEN for extra Gmail mailboxes. Do not commit it:")
    print(token)
    return 0


def cmd_slack(cfg, args) -> int:
    import anthropic

    from . import slack_bot as sb

    sheet = _sheet(cfg)
    slack = sb.Slack(cfg.slack_bot_token, cfg.slack_channel_id)
    if args.action == "digest":
        text = sb.digest_text(sheet.read_candidates())
        if args.dry_run:
            print(text)
        else:
            slack.post(text, event=sb.DIGEST_EVENT)
            print("Posted digest.")
        return 0
    ctx = sb.Context(slack, sheet, anthropic.Anthropic(api_key=cfg.anthropic_api_key),
                     cfg.models.get("chat", cfg.models.get("scoring", "claude-haiku-5-5")))
    if args.action == "poll":
        sb.poll(ctx)
    else:
        if not cfg.slack_app_token:
            raise SystemExit("Socket Mode needs SLACK_APP_TOKEN (xapp-...) and `pip install slack_bolt`.")
        sb.listen(ctx, cfg.slack_app_token)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="outreach")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup-sheet", help="create the sheet tabs and headers")
    s = sub.add_parser("search", help="find creators for today's criteria")
    s.add_argument("--dry-run", action="store_true", help="print results instead of writing the sheet")
    s.add_argument("--criteria", help="only run the criteria row with this name")
    s.add_argument("--keywords", help="skip the sheet and search these keywords (dry run)")
    s.add_argument("--lang", help="language code for --keywords, e.g. en")
    s.add_argument("--platforms", default="x", help="for --keywords: comma list of x,youtube,instagram,tiktok")
    s.add_argument("--min-followers", type=int, default=1000, help="for --keywords")
    sc = sub.add_parser("score", help="score new candidates and draft openers")
    sc.add_argument("--dry-run", action="store_true", help="print results instead of writing the sheet")
    sc.add_argument("--limit", type=int, help="score at most N candidates")
    sc.add_argument("--criteria", help="only score rows found by the criteria row with this name")
    em = sub.add_parser("emails", help="find and verify emails for scored candidates")
    em.add_argument("--dry-run", action="store_true", help="print results instead of writing the sheet")
    em.add_argument("--limit", type=int, help="process at most N candidates")
    ap = sub.add_parser("approve", help="approve ready rows for sending (only changes the sheet)")
    ap.add_argument("--handles", help="comma list: alice,@bob,youtube:carol")
    ap.add_argument("--min-score", type=int, help="approve every ready row with score >= N")
    ap.add_argument("--skip", help="comma list of handles to leave out")
    ap.add_argument("--followups", action="store_true", help="approve followup_due rows instead")
    ap.add_argument("--dry-run", action="store_true")
    se = sub.add_parser("send", help="email approved rows")
    se.add_argument("--dry-run", action="store_true", help="print the emails instead of sending")
    se.add_argument("--max", type=int, help="send at most N this run")
    rp = sub.add_parser("replies", help="check sent threads for replies, bounces and follow-ups")
    rp.add_argument("--dry-run", action="store_true")
    ci = sub.add_parser("criteria-import", help="add or update a Criteria row from a YAML file")
    ci.add_argument("file")
    ci.add_argument("--only", action="store_true", help="disable every other Criteria row")
    ti = sub.add_parser("template-import", help="add or replace a Templates row from a YAML file")
    ti.add_argument("file")
    ar = sub.add_parser("archive-candidates", help="move one platform's candidates to an archive tab")
    ar.add_argument("--platform", required=True)
    ar.add_argument("--dry-run", action="store_true")
    sub.add_parser("test-email", help="send one test email from each mailbox to itself")
    sl = sub.add_parser("slack", help="Slack bot: post the shortlist and answer thread replies")
    sl.add_argument("action", choices=["digest", "poll", "listen"])
    sl.add_argument("--dry-run", action="store_true", help="digest: print instead of posting")
    ga = sub.add_parser("gmail-auth", aliases=["google-auth"],
                        help="one-time: get a Google refresh token (Sheets + Gmail)")
    ga.add_argument("--client-secret", required=True, help="OAuth client JSON from Google Cloud")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    cfg = load_config(args.config)
    return {"setup-sheet": cmd_setup_sheet, "search": cmd_search, "score": cmd_score, "emails": cmd_emails,
            "approve": cmd_approve, "send": cmd_send, "replies": cmd_replies,
            "slack": cmd_slack, "test-email": cmd_test_email,
            "criteria-import": cmd_criteria_import, "template-import": cmd_template_import, "archive-candidates": cmd_archive, "gmail-auth": cmd_gmail_auth, "google-auth": cmd_gmail_auth}[args.cmd](cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
