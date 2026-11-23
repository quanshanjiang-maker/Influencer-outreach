# X Influencer Outreach

[中文说明](README.zh-CN.md)

Find X (Twitter) creators by topic every day, collect their stats and emails into Google Sheets, approve them by chatting with a Slack bot, send personalized emails, and track replies.

> Status: early development. Step 1 (sheet setup + creator search) works. Scoring, email finding, sending, reply tracking and the Slack bot are next.

## How it works

1. You write today's topics in the **Criteria** tab of a Google Sheet.
2. Claude expands each topic into a set of X advanced-search queries (synonyms, product names, hashtags).
3. [TwitterAPI.io](https://twitterapi.io) runs the searches; authors are grouped and filtered by followers, language and engagement.
4. *(next)* Claude scores each creator's bio and recent posts for relevance and writes a personalized opener.
5. *(next)* Emails are found (bio, website, Hunter) and verified (MillionVerifier).
6. *(next)* A Slack bot posts the shortlist; you reply in plain language ("send everyone 8+, skip @foo") and confirm.
7. *(next)* Emails go out through Gmail API or any SMTP/IMAP mailbox; replies are detected and classified.

Everything runs on GitHub Actions. You bring your own API keys; nothing is shared.

## Cost (your own accounts)

At 400–1000 creators screened per day, expect roughly **$130–$400/month**, mostly X data (pay-as-you-go) and Claude API usage. Google Sheets, Gmail API and GitHub Actions (public repos) are free.

## Setup

1. **Fork** this repository.
2. **Google Sheet**: create an empty sheet. In Google Cloud, create a service account, enable the *Google Sheets API*, download its JSON key, and share the sheet with the service account's email (Editor).
3. **Keys**: get an [Anthropic API key](https://console.anthropic.com) and a [TwitterAPI.io](https://twitterapi.io) key.
4. **Local run**:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env            # fill in the values
   cp config.example.yaml config.yaml
   python -m outreach setup-sheet  # creates Criteria / Candidates / Outreach / Templates tabs
   # edit the Criteria tab, then:
   python -m outreach search --dry-run   # preview
   python -m outreach search             # write to the Candidates tab
   ```
   Quick test without a sheet: `python -m outreach search --keywords "AI video tools" --lang en`
5. **GitHub Actions**: add `ANTHROPIC_API_KEY`, `TWITTERAPI_IO_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the whole JSON) and `SHEET_ID` under *Settings → Secrets and variables → Actions*, then run **Daily creator search** from the Actions tab. Uncomment the `schedule` block to run daily.

## Criteria tab

| column | meaning |
| --- | --- |
| enabled | TRUE / FALSE |
| name | short label for this campaign |
| keywords | topic in your own words |
| description | what kind of creator you want |
| language | X language code, e.g. `en`; empty = any |
| min_followers / max_followers | follower range (0 = no max) |
| min_avg_likes | minimum average likes on matched posts |
| max_candidates | how many creators to keep per day |

## Adding another data source or mailbox

X data providers implement `outreach/sources/base.py:XSource`. Mail providers will follow the same adapter pattern (Gmail API first, generic SMTP/IMAP second).

## Responsible use

You are responsible for complying with X's Terms of Service, the terms of any data provider you use, and anti-spam and privacy laws such as CAN-SPAM and GDPR. Send only relevant, personalized messages, keep volumes low, honor opt-outs, and never email anyone who asked you to stop.

## License

MIT
