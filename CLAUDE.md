# Working on this repo with Claude

This repo is an influencer outreach tool for X, YouTube, Instagram and TikTok. The user can operate it by
chatting with Claude (Claude Code) or with the Slack bot; both call the same CLI.

## Operating it from chat

Translate the user's plain-language requests into CLI commands, show what you will
run, and wait for a clear "yes" before anything that sends email or spends money
beyond a dry run.

- `python -m outreach setup-sheet` creates the Google Sheet tabs.
- `python -m outreach search --dry-run` previews today's creators from the Criteria tab.
- `python -m outreach search` writes them to the Candidates tab.
- `python -m outreach score [--dry-run] [--limit N]` scores new candidates (0-10) and drafts openers.
- `python -m outreach search --keywords "..." --lang en --platforms x,youtube,instagram,tiktok` quick search without a sheet.

Approval, sending and reply commands are coming in later steps; add them here as they land.

## Developing

- Python 3.12+, `pip install -r requirements.txt`, tests: `python -m pytest -q`.
- Secrets come from `.env` or GitHub Secrets; never commit keys.
- Data providers implement `outreach/sources/base.py:Source` and register in `outreach/sources/__init__.py`.
