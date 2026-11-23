# Influencer Outreach (X, YouTube, Instagram, TikTok)

[中文说明](README.zh-CN.md)

Find creators on X (Twitter), YouTube, Instagram and TikTok by topic every day, collect their stats and emails into Google Sheets, approve them by chatting with a Slack bot, send personalized emails, and track replies.

> Status: early development. Step 1 (sheet setup + creator search) works. Scoring, email finding, sending, reply tracking and the Slack bot are next.

## How it works

1. You write today's topics in the **Criteria** tab of a Google Sheet.
2. Claude expands each topic into a set of X advanced-search queries (synonyms, product names, hashtags).
3. Each platform's adapter runs the searches; authors are grouped and filtered by followers, language and engagement.

| platform | data source | key | rough price |
| --- | --- | --- | --- |
| X | [TwitterAPI.io](https://twitterapi.io) | `TWITTERAPI_IO_KEY` | $0.15 / 1k tweets |
| YouTube | official YouTube Data API v3 | `YOUTUBE_API_KEY` | free daily quota |
| Instagram | [Apify Instagram Scraper](https://apify.com/apify/instagram-scraper) | `APIFY_TOKEN` | $1.50–2.70 / 1k results |
| TikTok | [Apify TikTok Scraper](https://apify.com/clockworks/tiktok-scraper) | `APIFY_TOKEN` | ~$1.00–3.00 / 1k results |
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
3. **Keys**: get an [Anthropic API key](https://console.anthropic.com), plus keys for the platforms you use: [TwitterAPI.io](https://twitterapi.io), a YouTube Data API key (Google Cloud → enable *YouTube Data API v3* → API key), and an [Apify](https://apify.com) token for Instagram/TikTok.
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
   Quick test without a sheet: `python -m outreach search --keywords "AI video tools" --lang en --platforms x,youtube`
5. **GitHub Actions**: add `ANTHROPIC_API_KEY`, the platform keys you use (`TWITTERAPI_IO_KEY`, `YOUTUBE_API_KEY`, `APIFY_TOKEN`), `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the whole JSON) and `SHEET_ID` under *Settings → Secrets and variables → Actions*, then run **Daily creator search** from the Actions tab. Uncomment the `schedule` block to run daily.

## Criteria tab

| column | meaning |
| --- | --- |
| enabled | TRUE / FALSE |
| name | short label for this campaign |
| platforms | comma list: `x,youtube,instagram,tiktok` |
| keywords | topic in your own words |
| description | what kind of creator you want |
| language | X language code, e.g. `en`; empty = any |
| min_followers / max_followers | follower range (0 = no max) |
| min_avg_likes | minimum average likes on matched posts |
| max_candidates | how many creators to keep per day |

## Adding another data source or mailbox

Data providers implement `outreach/sources/base.py:Source` and register in `outreach/sources/__init__.py`. Mail providers will follow the same adapter pattern (Gmail API first, generic SMTP/IMAP second).

## Responsible use

You are responsible for complying with the Terms of Service of X, YouTube, Instagram and TikTok, the terms of any data provider you use, and anti-spam and privacy laws such as CAN-SPAM and GDPR. Send only relevant, personalized messages, keep volumes low, honor opt-outs, and never email anyone who asked you to stop.

## License

MIT
