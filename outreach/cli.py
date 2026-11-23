"""Command line entry point.

    python -m outreach setup-sheet
    python -m outreach search [--dry-run] [--criteria NAME]
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
    sheet = Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs)
    created = sheet.setup()
    print("Created tabs: " + (", ".join(created) if created else "none (all tabs already exist)"))
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
        sheet = Sheet(cfg.google_service_account, cfg.sheet_id, cfg.sheet_tabs)
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
        queries = expand_queries(
            client, cfg.models.get("query_expansion", "claude-opus-5-5"), crit,
            int(cfg.search.get("queries_per_criteria", 12)), platform=platform,
        )
        result = run_search(
            source, crit, queries, known,
            pages_per_query=int(cfg.search.get("pages_per_query", 3)),
            tweet_budget=budgets.get(platform, 10**9),
        )
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
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    cfg = load_config(args.config)
    return {"setup-sheet": cmd_setup_sheet, "search": cmd_search}[args.cmd](cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
