# Working on this repo with Claude

This repo is an X (Twitter) influencer outreach tool. The user can operate it by
chatting with Claude (Claude Code) or with the Slack bot; both call the same CLI.

## Operating it from chat

Translate the user's plain-language requests into CLI commands, show what you will
run, and wait for a clear "yes" before anything that sends email or spends money
beyond a dry run.

- `python -m outreach setup-sheet` creates the Google Sheet tabs.
- `python -m outreach search --dry-run` previews today's creators from the Criteria tab.
- `python -m outreach search` writes them to the Candidates tab.
- `python -m outreach search --keywords "..." --lang en` quick search without a sheet.

Approval, sending and reply commands are coming in later steps; add them here as they land.

## Developing

- Python 3.12+, `pip install -r requirements.txt`, tests: `python -m pytest -q`.
- Secrets come from `.env` or GitHub Secrets; never commit keys.
- New X providers implement `outreach/sources/base.py:XSource`.
