# Influencer Outreach (X, YouTube, Instagram, TikTok)

[中文说明](README.zh-CN.md)

**An automated assistant for influencer marketing.** Every day it finds creators on X (Twitter), YouTube, Instagram and TikTok who talk about your topics, scores how well each one fits your brand, finds their business email, drafts a personalized first line, and after you approve, sends the emails and tracks who replied. Everything lands in one Google Sheet.

## Who it is for

Marketing and partnerships people who contact dozens to hundreds of creators a week and are comfortable with light web coding (copying keys, editing a config file, clicking around GitHub). You do not need to write Python: you can run it by chatting with Claude or a Slack bot.

## What your day looks like

You do two things; the rest runs on its own.

1. **Morning: say what you are looking for.** In the sheet's *Criteria* tab, write a topic in plain words, e.g. "creators who review AI video tools, English, 10k–200k followers", and pick the platforms.
2. **Search and screening run automatically** (GitHub Actions, free): 400–1000 creators screened, each scored 0–10 with a reason, emails found and verified, an opening line drafted.
3. **You approve by chat.** In Slack or with Claude: "send everyone 8+, skip @foo, make @bar's opener more casual". The bot repeats what it understood, and nothing happens until you reply "confirm".
4. **Emails go out automatically** from your Gmail and/or company mailbox, spread across the day and capped per mailbox.
5. **Replies are tracked.** Each reply is labeled (interested, pricing, declined, unsubscribe...). Interested replies show up in Slack. No reply after a few days? It suggests a follow-up for you to approve.

## What you get in the sheet

| tab | what is in it |
| --- | --- |
| Criteria | your topics, platforms, countries, follower range, a one-line pitch |
| Candidates | one row per creator: platform, profile link, followers, average likes, bio, fit score and reason, email and where it came from, drafted opener, status (ready / approved / sent / replied / bounced...), plus X rates (price_post, price_thread, price_retweet, price_quote), leader_review (待审 / 通过 / 不要 dropdown) and leader_note for your leader's review. Two saved filter views: "Leader 审批（待审）" shows every row with a price that the leader hasn't decided yet, "推进中（通过）" shows the approved ones. Columns only the tool uses are hidden. |
| Outreach | log of every email sent and every reply |
| Templates | your email subject and body, with `{name}` and `{opener}` filled in per creator |

## Tools it uses

You sign up for these yourself; the tool never shares your keys.

| tool | used for | needed? | price |
| --- | --- | --- | --- |
| Google Sheets | the working spreadsheet | yes | free |
| GitHub + GitHub Actions | stores the code, runs it on a schedule | yes | free for public repos |
| Claude API (Anthropic) | understands your topic, scores creators, writes openers, reads replies | yes | pay per use |
| TwitterAPI.io | search X | if you use X | $0.15 per 1,000 posts |
| YouTube Data API | search YouTube | if you use YouTube | free daily quota |
| EasyKOL **or** Apify | search Instagram and TikTok (EasyKOL also returns emails, and can cover YouTube) | if you use IG/TikTok | EasyKOL API: Team plan, $500/year; Apify: ~$1–3 per 1,000 results |
| MillionVerifier | checks emails before sending, so you do not bounce | recommended | $37 per 10,000 checks, never expire |
| Hunter | finds emails on a creator's own website domain | optional | free 50/month, $49/month for more |
| Gmail / Google Workspace or any company mailbox | sends the emails | yes | Gmail free; Workspace ~$7 per mailbox/month |
| Slack | chat approval | optional | free plan works |

## How much it costs

Estimates for 400–1000 creators screened per day and 100–300 emails sent per day. Real cost depends on volume and how many creators are already in your sheet (duplicates are skipped for free).

| setup | monthly cost | what it covers |
| --- | --- | --- |
| Trial (first 1–2 weeks, small volume) | about $20–40 | one topic, ~50 creators/day, your personal Gmail |
| Cheapest full setup | about $60–170 | X via TwitterAPI.io, YouTube free API, IG/TikTok via EasyKOL or Apify, Claude Haiku, personal Gmail |
| Full setup with company mailboxes | about $130–400 | adds 4–6 warmed-up Workspace mailboxes, Hunter, optional warm-up service (e.g. Instantly, $47/month) |

The biggest costs are creator data (X posts, Instagram/TikTok results) and the Claude API. Google Sheets, Gmail API, Slack and GitHub Actions cost nothing.

## Good to know

- **Not every creator has a public email.** Expect roughly 10–30% of screened creators to be emailable; the rest are kept and marked `no_email` so you can DM them.
- **New mailboxes need warming up.** Start at 10–20 emails per mailbox per day and grow over 3–4 weeks. Sending ~200/day needs about 4–6 mailboxes. Use a separate domain for cold email so your main company domain is protected.
- **You stay in control.** Nothing is emailed without your approval, unsubscribes and bounces are never contacted again, and every email includes an opt-out line.

## How it works (technical)

1. You write today's topics in the **Criteria** tab of a Google Sheet.
2. Claude expands each topic into search queries written for each platform: X advanced search, YouTube keywords, Instagram hashtags, TikTok keywords (synonyms, product names, hashtags).
3. Each platform's adapter runs the searches; authors are grouped and filtered by followers, language and engagement.

| platform | data source | key | rough price |
| --- | --- | --- | --- |
| X | [TwitterAPI.io](https://twitterapi.io) | `TWITTERAPI_IO_KEY` | $0.15 / 1k tweets |
| YouTube | official YouTube Data API v3 | `YOUTUBE_API_KEY` | free daily quota |
| Instagram | [Apify Instagram Scraper](https://apify.com/apify/instagram-scraper) | `APIFY_TOKEN` | $1.50–2.70 / 1k results |
| TikTok | [Apify TikTok Scraper](https://apify.com/clockworks/tiktok-scraper) | `APIFY_TOKEN` | ~$1.00–3.00 / 1k results |
| YouTube / Instagram / TikTok (alternative) | [EasyKOL](https://easykol.com/en/pricing) [API](https://github.com/iftechio/easykol-skills/blob/main/docs/api.md) | `EASYKOL_API_KEY`, `EASYKOL_API_EMAIL` | your EasyKOL plan's task points; returns emails |

Pick the provider per platform under `providers:` in `config.yaml`.

4. Claude scores each creator's bio and recent posts for relevance and writes a personalized opener.
5. Emails are found (bio, website, Hunter) and verified (MillionVerifier).
6. You approve by chat: tell Claude (Claude Code reads `CLAUDE.md`) "send everyone 8+, skip @foo", and it runs `approve` after you confirm. Or reply to the Slack bot's daily shortlist thread; it restates what it understood and acts only after you say "confirm".
7. Emails go out through the Gmail API or any SMTP/IMAP mailbox, rotating across mailboxes within daily limits. Replies and bounces are detected and classified (interested, pricing, declined, unsubscribe...), and rows with no reply after N days become `followup_due` for your approval.

Everything runs on GitHub Actions. You bring your own API keys; nothing is shared.


## Setup

1. **Fork** this repository.
2. **Google Sheet**: create an empty sheet. In Google Cloud, create a service account, enable the *Google Sheets API*, download its JSON key, and share the sheet with the service account's email (Editor).
   *If Google says "service account key creation is disabled" (an organization policy),* use your own Google login instead: set up the OAuth consent screen (External, add yourself as a test user, then *Publish app* so the token does not expire after 7 days), create an OAuth client of type *Web application* with redirect URI `https://developers.google.com/oauthplayground`, then in the [OAuth Playground](https://developers.google.com/oauthplayground) click the gear, tick *Use your own OAuth credentials*, authorize the scopes `https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly`, and exchange the code for a refresh token. Save `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_REFRESH_TOKEN` as secrets. The same token also sends from that Gmail.
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
   python -m outreach score --dry-run    # preview scores and openers
   python -m outreach score              # write score, reason, tags, opener
   python -m outreach emails             # find + verify emails; status becomes ready or no_email
   python -m outreach approve --min-score 8        # or --handles alice,youtube:bob
   python -m outreach send --dry-run     # preview the emails
   python -m outreach send               # send approved rows
   python -m outreach replies            # check replies, bounces, follow-ups due
   ```
   Quick test without a sheet: `python -m outreach search --keywords "AI video tools" --lang en --platforms x,youtube`
5. **GitHub Actions**: add `ANTHROPIC_API_KEY`, the platform keys you use (`TWITTERAPI_IO_KEY`, `YOUTUBE_API_KEY`, `APIFY_TOKEN`), `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the whole JSON) and `SHEET_ID` under *Settings → Secrets and variables → Actions*, then run **Daily creator pipeline** from the Actions tab. Uncomment the `schedule` block to run daily.

## Mailboxes

List sending mailboxes under `mailboxes:` in `config.yaml`; secrets stay in env vars / GitHub Secrets named by the `*_env` fields.

- **Gmail / Google Workspace** (`type: gmail`): in Google Cloud enable the *Gmail API*, create an OAuth client (Desktop app), download it, then run `python -m outreach gmail-auth --client-secret client_secret.json` once per mailbox and store the printed refresh token as a secret.
- **Any other provider** (`type: smtp`): Microsoft 365, Tencent Exmail, Zoho, Fastmail etc. Fill `smtp_host`, `imap_host` and an app password.

Keep `daily_limit` low (start at 10–20 per new mailbox and warm up over weeks), set up SPF/DKIM/DMARC, and prefer a secondary domain for cold email. Edit the `default` and `followup` rows in the Templates tab; `{name}`, `{opener}`, `{username}`, `{platform}` are filled in.

## Slack bot (optional)

1. Create a Slack app from `slack-app-manifest.yml` (api.slack.com/apps → *From a manifest*), install it to your workspace, and invite it to a channel (`/invite @outreach-bot`).
2. Add secrets `SLACK_BOT_TOKEN` (xoxb-...) and `SLACK_CHANNEL_ID` (channel details → bottom).
3. The daily pipeline posts the shortlist (`python -m outreach slack digest`). Reply in its thread in plain language: "send everyone 8+, skip @foo", "make @bar's opener more casual", "send the follow-ups", "who replied?".
4. Replies are read by **Slack bot (polling)** every 15 minutes on GitHub Actions (free; uncomment its schedule). For instant answers, run `pip install slack_bolt` and `python -m outreach slack listen` on a small always-on server with `SLACK_APP_TOKEN` (xapp-..., Socket Mode).

The bot only changes the sheet (approve, skip, edit openers); emails go out on the next `send` run.

## Criteria tab

| column | meaning |
| --- | --- |
| enabled | TRUE / FALSE |
| name | short label for this campaign |
| platforms | comma list: `x,youtube,instagram,tiktok` |
| regions | optional ISO country codes, e.g. `US,GB` (used by EasyKOL) |
| keywords | topic in your own words |
| description | what kind of creator you want |
| language | language code, e.g. `en`; empty = any |
| min_followers / max_followers | follower range (0 = no max) |
| min_avg_likes | minimum average likes on matched posts |
| max_candidates | how many creators to keep per day |
| rules | optional free-text hard rules, exclusions and ICP tiers for the scorer |
| queries | optional fixed X searches, one per line as `Label: query` (e.g. a competitor's name); skips query expansion and fills the `competitor` and `competitor_post` columns |
| since_days | X only: only posts from the last N days (0 = no limit) |
| pages_per_query | optional override of `search.pages_per_query` for this row |

## Adding another data source or mailbox

Data providers implement `outreach/sources/base.py:Source` and register in `outreach/sources/__init__.py`. Mailboxes implement `outreach/mail/base.py:Mailbox` (`send`, `replies`) and register in `outreach/mail/__init__.py`.

## Responsible use

You are responsible for complying with the Terms of Service of X, YouTube, Instagram and TikTok, the terms of any data provider you use, and anti-spam and privacy laws such as CAN-SPAM and GDPR. Send only relevant, personalized messages, keep volumes low, honor opt-outs, and never email anyone who asked you to stop.

## License

MIT
