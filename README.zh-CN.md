# 全平台博主自动化建联工具 (Influencer Outreach: X, YouTube, Instagram, TikTok)

[English](README.md)

**一个帮做网红营销 (influencer marketing) 的自动化助手。** 每天自动在 X（推特）、YouTube、Instagram、TikTok 上找和你话题相关的博主，给每个人打一个匹配分，找到商务邮箱，写好个性化的第一句话；你批准后自动发邮件，并追踪谁回复了。所有结果都在一张 Google 表格里。

> 状态：开发中。所有功能都已写好并通过单元测试 (unit test)，但还没有用真实账号测试过。

## 适合谁用

每周要联系几十到几百个博主的市场 (marketing) 或商务合作 (partnerships) 同学，会一点网页开发 (web coding) 就够：会复制 API key、改配置文件、在 GitHub 上点点按钮。不需要写 Python，日常可以跟 Claude 或 Slack 机器人 (bot) 聊天来操作。

## 你每天要做什么

你只做两件事，其余全自动。

1. **早上：说清楚要找什么人。** 在表格的 *Criteria* 页用大白话写话题，比如“测评 AI 视频工具的博主，英语，1 万到 20 万粉”，再选平台。
2. **自动搜索和筛选**（GitHub Actions 定时运行，免费）：每天筛 400 到 1000 个博主，每人打 0 到 10 分并写理由，找邮箱并验证，写好开场白 (opener)。
3. **你用聊天审批 (approval)。** 在 Slack 或跟 Claude 说：“8 分以上都发，跳过 @foo，@bar 的开场白写轻松点”。机器人先复述它的理解，你回“确认”才执行。
4. **自动发邮件**：从你的 Gmail 和/或公司邮箱发出，分散在一天里发，每个邮箱有每日上限 (daily limit)。
5. **自动追踪回复**：每封回复自动分类（感兴趣、要报价、拒绝、退订……），有意向的会推到 Slack。几天没回复的，会建议发跟进 (follow-up)，你批准后才发。

## 表格里有什么

| 工作表 (tab) | 内容 |
| --- | --- |
| Criteria | 你的话题、平台、国家、粉丝范围、一句话合作介绍 (pitch) |
| Candidates | 每个博主一行：平台、主页链接、粉丝数、平均点赞、简介 (bio)、匹配分和理由、邮箱及来源、开场白、状态（ready 待批准 / approved 已批准 / sent 已发 / replied 已回复 / bounced 退信……） |
| Outreach | 每封发出的邮件和每条回复的记录 (log) |
| Templates | 邮件标题和正文模板，`{name}`、`{opener}` 会按博主自动填入 |

## 用到哪些工具

账号都由你自己注册，工具不会共享你的 key。

| 工具 | 用来做什么 | 是否必需 | 价格 |
| --- | --- | --- | --- |
| Google Sheets | 工作表格 | 必需 | 免费 |
| GitHub + GitHub Actions | 存代码、定时运行 | 必需 | 公开仓库免费 |
| Claude API (Anthropic) | 理解话题、给博主打分、写开场白、读回复 | 必需 | 按量付费 (pay-as-you-go) |
| TwitterAPI.io | 搜索 X | 用 X 才需要 | 每千条推文 $0.15 |
| YouTube Data API | 搜索 YouTube | 用 YouTube 才需要 | 每日免费配额 (quota) |
| EasyKOL **或** Apify | 搜索 Instagram 和 TikTok（EasyKOL 还自带邮箱，也能搜 YouTube） | 用 IG/TikTok 才需要 | EasyKOL API 在 Team 套餐，$500/年；Apify 约每千条 $1 到 $3 |
| MillionVerifier | 发信前验证邮箱，避免退信 (bounce) | 推荐 | $37 买 1 万次，不过期 |
| Hunter | 通过博主自己的网站域名找邮箱 | 可选 | 免费 50 次/月，更多 $49/月 |
| Gmail / Google Workspace 或任意公司邮箱 | 发邮件 | 必需 | Gmail 免费；Workspace 约每个邮箱 $7/月 |
| Slack | 聊天审批 | 可选 | 免费版即可 |

## 预计花多少钱

按每天筛 400 到 1000 个博主、发 100 到 300 封邮件估算。实际花费取决于量的大小，以及表格里已有多少博主（重复的会跳过，不花钱）。

| 方案 | 每月花费 | 包含什么 |
| --- | --- | --- |
| 试用（前 1 到 2 周，小量） | 约 $20 到 $40 | 一个话题，每天约 50 个博主，用个人 Gmail |
| 最省钱的完整方案 | 约 $60 到 $170 | X 用 TwitterAPI.io，YouTube 用免费官方 API，IG/TikTok 用 EasyKOL 或 Apify，Claude Haiku，个人 Gmail |
| 加公司邮箱的完整方案 | 约 $130 到 $400 | 再加 4 到 6 个预热好的 Workspace 邮箱、Hunter，可选预热服务（如 Instantly，$47/月） |

花钱最多的是博主数据（X 推文、IG/TikTok 结果）和 Claude API。Google Sheets、Gmail API、Slack、GitHub Actions 都不要钱。

## 需要知道的几件事

- **不是每个博主都有公开邮箱。** 大约一到三成能找到邮箱，其余的会保留并标为 `no_email`，你可以去私信 (DM)。
- **新邮箱要预热 (warm-up)。** 每个新邮箱先每天发 10 到 20 封，3 到 4 周慢慢加量。每天发 200 封左右需要 4 到 6 个邮箱。冷邮件 (cold email) 最好用单独的副域名 (secondary domain)，保护公司主域名。
- **一切由你掌控。** 没有你的批准不会发任何邮件；退订和退信的邮箱永远不会再联系；每封邮件都带退订说明 (opt-out)。

## 工作原理（技术说明 technical）

1. 你在表格的 **Criteria** 页写今天的话题和条件。
2. Claude 按平台把每个话题扩展成一组搜索语句 (search queries)：X 用高级搜索语法，YouTube 和 TikTok 用关键词，Instagram 用标签 (hashtag)，包括同义词和产品名。
3. 各平台的数据源适配器 (adapter) 执行搜索（X 用 TwitterAPI.io，YouTube 用官方 YouTube Data API 免费配额，Instagram 和 TikTok 用 Apify；也可以在 `config.yaml` 的 `providers` 里把 YouTube/IG/TikTok 换成 [EasyKOL](https://easykol.com/en/pricing)，它自带语义搜索并返回邮箱），按作者合并，再按粉丝数、语言、互动率 (engagement) 粗筛 (pre-filter)。
4. Claude 读博主的 bio 和近期内容打分，并写个性化开场白 (personalized opener)。
5. 找邮箱（bio、网站、Hunter）并验证 (verify)（MillionVerifier）。
6. 用聊天审批 (approval)：跟 Claude 说“8 分以上都发，跳过 @foo”（Claude Code 会读仓库里的 `CLAUDE.md`），你确认后它运行 `approve`。也可以在 Slack 机器人每天发的名单子线程里回复，它会先复述它的理解，你回“确认”后才执行。
7. 通过 Gmail API 或任意 SMTP/IMAP 邮箱发信，多个邮箱轮流发 (inbox rotation) 并遵守每日上限 (daily limit)。自动检测回复和退信 (bounce)，并分类（感兴趣、报价、拒绝、退订……）；N 天没回复的标为 `followup_due`，等你批准后发跟进 (follow-up)。

全部跑在 GitHub Actions 上。每个人用自己的 API key，互不共享。

## 安装 (setup)

1. **Fork** 这个仓库。
2. **Google 表格**：新建一个空表格。在 Google Cloud 创建服务账号 (service account)，开启 *Google Sheets API*，下载 JSON 密钥，并把表格共享给服务账号的邮箱（编辑者权限）。
   *如果 Google 提示“服务账号密钥建立功能已停用”（组织政策 organization policy）*，改用你自己的 Google 登录授权 (OAuth)：设置 OAuth 同意屏幕 (consent screen)，选“外部 (External)”，把自己加为测试用户 (test user)，再点“发布应用 (Publish app)”，这样令牌 (token) 不会 7 天就过期。然后创建 OAuth 客户端，类型选“网页应用 (Web application)”，重定向网址 (redirect URI) 填 `https://developers.google.com/oauthplayground`。接着在 [OAuth Playground](https://developers.google.com/oauthplayground) 点齿轮，勾选 *Use your own OAuth credentials*，授权这三个范围 (scopes)：`https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly`，换取刷新令牌 (refresh token)。把 `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_REFRESH_TOKEN` 存成 Secrets。同一个令牌也能用这个 Gmail 发信。
3. **密钥**：申请 [Anthropic API key](https://console.anthropic.com)，再按需申请各平台的 key：[TwitterAPI.io](https://twitterapi.io)、YouTube Data API key（Google Cloud 开启 *YouTube Data API v3* 后创建 API key）、[Apify](https://apify.com) token（Instagram/TikTok 用）。Criteria 页的 platforms 列填 `x,youtube,instagram,tiktok` 选择平台。
4. **本地运行**：
   ```bash
   pip install -r requirements.txt
   cp .env.example .env            # 填好各项
   cp config.example.yaml config.yaml
   python -m outreach setup-sheet  # 自动建好 4 个工作表
   # 修改 Criteria 页后：
   python -m outreach search --dry-run   # 先预览
   python -m outreach search             # 写入 Candidates 页
   python -m outreach score --dry-run    # 预览打分和开场白
   python -m outreach score              # 写入分数、理由、标签、开场白
   python -m outreach emails             # 找邮箱并验证，状态变为 ready 或 no_email
   python -m outreach approve --min-score 8        # 或 --handles alice,youtube:bob
   python -m outreach send --dry-run     # 预览邮件
   python -m outreach send               # 发送已批准的
   python -m outreach replies            # 查回复、退信、该跟进的
   ```
   不建表快速试用：`python -m outreach search --keywords "AI video tools" --lang en --platforms x,youtube`
5. **GitHub Actions**：在 *Settings → Secrets and variables → Actions* 添加 `ANTHROPIC_API_KEY`、你用到的平台 key（`TWITTERAPI_IO_KEY`、`YOUTUBE_API_KEY`、`APIFY_TOKEN`）、`GOOGLE_SERVICE_ACCOUNT_JSON`（粘贴整段 JSON）和 `SHEET_ID`，然后在 Actions 页手动运行 **Daily creator pipeline**。取消注释 `schedule` 即可每天自动运行。

## 发信邮箱 (mailboxes)

在 `config.yaml` 的 `mailboxes:` 里列出发信邮箱；密钥只放环境变量或 GitHub Secrets，名字写在 `*_env` 字段里。

- **Gmail / Google Workspace**（`type: gmail`）：在 Google Cloud 开启 *Gmail API*，创建 OAuth 客户端 (OAuth client，类型选 Desktop app) 并下载，每个邮箱运行一次 `python -m outreach gmail-auth --client-secret client_secret.json`，把打印出来的刷新令牌 (refresh token) 存成 Secret。
- **其他任何服务商**（`type: smtp`）：微软 365、腾讯企业邮、Zoho、Fastmail 等，填 `smtp_host`、`imap_host` 和应用专用密码 (app password)。

`daily_limit` 先设低一点（新邮箱每天 10 到 20 封，几周内慢慢加，即预热 warm-up），配好 SPF/DKIM/DMARC，冷邮件 (cold email) 最好用副域名 (secondary domain)。在 Templates 页改 `default` 和 `followup` 两行模板，`{name}`、`{opener}`、`{username}`、`{platform}` 会自动填入。

## Slack 机器人（可选）

1. 在 api.slack.com/apps 选 *From a manifest*，粘贴仓库里的 `slack-app-manifest.yml` 创建应用 (app)，安装到工作区 (workspace)，再把机器人邀请进一个频道 (channel)：`/invite @outreach-bot`。
2. 添加 Secrets：`SLACK_BOT_TOKEN`（xoxb- 开头）和 `SLACK_CHANNEL_ID`（频道详情最下方）。
3. 每天的流程会把名单发到频道（`python -m outreach slack digest`）。你在子线程 (thread) 里用大白话回复：“8 分以上都发，跳过 @foo”、“@bar 的开场白写轻松点”、“跟进都发”、“谁回复了”。
4. 默认由 GitHub Actions 的 **Slack bot (polling)** 每 15 分钟读一次回复（免费，取消注释 schedule 即可）。想秒回的话，在一台常驻小服务器上 `pip install slack_bolt`，配好 `SLACK_APP_TOKEN`（xapp- 开头，Socket Mode），运行 `python -m outreach slack listen`。

机器人只改表格（批准、跳过、改开场白），邮件在下一次 `send` 定时运行时发出。

## 合规使用 (responsible use)

使用者需自行遵守 X、YouTube、Instagram、TikTok 的服务条款 (Terms of Service)、所用数据服务商的条款，以及 CAN-SPAM、GDPR 等反垃圾邮件和隐私法律。只发相关、个性化的邮件，控制发送量，尊重退订 (opt-out)。

## 许可证 (license)

MIT
