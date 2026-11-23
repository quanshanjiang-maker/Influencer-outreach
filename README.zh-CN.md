# X 博主自动化建联工具 (X Influencer Outreach)

[English](README.md)

每天按话题自动在 X 上找博主，把数据和邮箱整理到 Google Sheets，在 Slack 里用聊天的方式审批，自动发送个性化邮件并追踪回复。

> 状态：开发中。第 1 步（建表 + 搜索博主）已可用。打分、找邮箱、发信、回复追踪和 Slack 机器人 (bot) 是接下来的步骤。

## 工作流程 (how it works)

1. 你在表格的 **Criteria** 页写今天的话题和条件。
2. Claude 把每个话题扩展成一组 X 高级搜索语句 (advanced-search queries)，包括同义词、产品名、标签 (hashtag)。
3. [TwitterAPI.io](https://twitterapi.io) 执行搜索，按作者合并，再按粉丝数、语言、互动率 (engagement) 粗筛 (pre-filter)。
4. *（下一步）* Claude 读博主的 bio 和近期推文打分，并写个性化开场白 (personalized opener)。
5. *（下一步）* 找邮箱（bio、网站、Hunter）并验证 (verify)（MillionVerifier）。
6. *（下一步）* Slack 机器人推送名单，你用大白话回复（“8 分以上都发，跳过 @foo”），确认后发出。
7. *（下一步）* 通过 Gmail API 或任意 SMTP/IMAP 邮箱发信，自动检测并分类回复。

全部跑在 GitHub Actions 上。每个人用自己的 API key，互不共享。

## 费用 (cost)

每天筛 400 到 1000 个博主，大约每月 **$130 到 $400**，主要是 X 数据（按量付费 pay-as-you-go）和 Claude API。Google Sheets、Gmail API、公开仓库的 GitHub Actions 都免费。

## 安装 (setup)

1. **Fork** 这个仓库。
2. **Google 表格**：新建一个空表格。在 Google Cloud 创建服务账号 (service account)，开启 *Google Sheets API*，下载 JSON 密钥，并把表格共享给服务账号的邮箱（编辑者权限）。
3. **密钥**：申请 [Anthropic API key](https://console.anthropic.com) 和 [TwitterAPI.io](https://twitterapi.io) key。
4. **本地运行**：
   ```bash
   pip install -r requirements.txt
   cp .env.example .env            # 填好各项
   cp config.example.yaml config.yaml
   python -m outreach setup-sheet  # 自动建好 4 个工作表
   # 修改 Criteria 页后：
   python -m outreach search --dry-run   # 先预览
   python -m outreach search             # 写入 Candidates 页
   ```
   不建表快速试用：`python -m outreach search --keywords "AI video tools" --lang en`
5. **GitHub Actions**：在 *Settings → Secrets and variables → Actions* 添加 `ANTHROPIC_API_KEY`、`TWITTERAPI_IO_KEY`、`GOOGLE_SERVICE_ACCOUNT_JSON`（粘贴整段 JSON）和 `SHEET_ID`，然后在 Actions 页手动运行 **Daily creator search**。取消注释 `schedule` 即可每天自动运行。

## 合规使用 (responsible use)

使用者需自行遵守 X 的服务条款 (Terms of Service)、所用数据服务商的条款，以及 CAN-SPAM、GDPR 等反垃圾邮件和隐私法律。只发相关、个性化的邮件，控制发送量，尊重退订 (opt-out)。

## 许可证 (license)

MIT
