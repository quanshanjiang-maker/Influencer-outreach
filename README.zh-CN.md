# 全平台博主自动化建联工具 (Influencer Outreach: X, YouTube, Instagram, TikTok)

[English](README.md)

每天按话题自动在 X、YouTube、Instagram、TikTok 上找博主，把数据和邮箱整理到 Google Sheets，在 Slack 里用聊天的方式审批，自动发送个性化邮件并追踪回复。

> 状态：开发中，还没有用真实 API key 测试过。建表、四个平台搜索、打分、找邮箱、发信、回复追踪已写好。Slack 机器人 (bot) 是下一步。

## 工作流程 (how it works)

1. 你在表格的 **Criteria** 页写今天的话题和条件。
2. Claude 按平台把每个话题扩展成一组搜索语句 (search queries)：X 用高级搜索语法，YouTube 和 TikTok 用关键词，Instagram 用标签 (hashtag)，包括同义词和产品名。
3. 各平台的数据源适配器 (adapter) 执行搜索（X 用 TwitterAPI.io，YouTube 用官方 YouTube Data API 免费配额，Instagram 和 TikTok 用 Apify；也可以在 `config.yaml` 的 `providers` 里把 YouTube/IG/TikTok 换成 [EasyKOL](https://easykol.com/en/pricing)，它自带语义搜索并返回邮箱），按作者合并，再按粉丝数、语言、互动率 (engagement) 粗筛 (pre-filter)。
4. Claude 读博主的 bio 和近期内容打分，并写个性化开场白 (personalized opener)。
5. 找邮箱（bio、网站、Hunter）并验证 (verify)（MillionVerifier）。
6. 用聊天审批 (approval)：跟 Claude 说“8 分以上都发，跳过 @foo”（Claude Code 会读仓库里的 `CLAUDE.md`），你确认后它运行 `approve`。*（下一步）* 也可以跟 Slack 机器人说。
7. 通过 Gmail API 或任意 SMTP/IMAP 邮箱发信，多个邮箱轮流发 (inbox rotation) 并遵守每日上限 (daily limit)。自动检测回复和退信 (bounce)，并分类（感兴趣、报价、拒绝、退订……）；N 天没回复的标为 `followup_due`，等你批准后发跟进 (follow-up)。

全部跑在 GitHub Actions 上。每个人用自己的 API key，互不共享。

## 费用 (cost)

每天筛 400 到 1000 个博主，大约每月 **$130 到 $400**，主要是数据服务商（按量付费 pay-as-you-go）和 Claude API。最省钱的组合（X 用 TwitterAPI.io，YouTube 用免费官方 API，IG/TikTok 用 EasyKOL 或 Apify）大约每月 $60 到 $170。Google Sheets、Gmail API、公开仓库的 GitHub Actions 都免费。

## 安装 (setup)

1. **Fork** 这个仓库。
2. **Google 表格**：新建一个空表格。在 Google Cloud 创建服务账号 (service account)，开启 *Google Sheets API*，下载 JSON 密钥，并把表格共享给服务账号的邮箱（编辑者权限）。
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

## 合规使用 (responsible use)

使用者需自行遵守 X、YouTube、Instagram、TikTok 的服务条款 (Terms of Service)、所用数据服务商的条款，以及 CAN-SPAM、GDPR 等反垃圾邮件和隐私法律。只发相关、个性化的邮件，控制发送量，尊重退订 (opt-out)。

## 许可证 (license)

MIT
