# 🤖 AI 热点新闻聚合推送

每日自动抓取 AI/技术领域热点新闻，推送到微信或 Telegram。

## 数据源

- **Hacker News** - 技术社区热门文章
- **ArXiv** - AI/ML 领域最新论文

## 快速部署（GitHub Actions）

### 1. Fork 本仓库

### 2. 配置 Secrets

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

| Secret 名称 | 说明 | 必填 |
|------------|------|:----:|
| `PUSHPLUS_TOKEN` | PushPlus Token（[获取地址](https://www.pushplus.plus)） | 推荐 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 可选 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 可选 |

### 3. 启用 Actions

`Actions` → `I understand my workflows, go ahead and enable them`

### 4. 手动测试

`Actions` → `AI热点新闻推送` → `Run workflow`

## 推送时间

默认每天 **北京时间 08:00 和 20:00** 自动推送。

可在 `.github/workflows/daily_news.yml` 中修改 cron 表达式。

## 推送效果示例

```
🤖 AI 热点日报 (2026-02-05)

📰 Hacker News Top 10
1. 🔥 [856↑] OpenAI announces GPT-5
2. 🔥 [654↑] Show HN: I built an AI code reviewer
...

📚 ArXiv AI 论文精选
1. [cs.AI] Scaling Laws for Neural Language Models
   作者: Author1, Author2
   摘要: We study empirical scaling laws...
...

⏰ 生成时间: 08:00
```

## 本地运行

```bash
cp .env.example .env
# 编辑 .env 填入 Token
pip install -r requirements.txt
python main.py
```

## License

MIT
