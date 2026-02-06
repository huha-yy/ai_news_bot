# -*- coding: utf-8 -*-
"""
AI 热点新闻聚合推送系统
- Hacker News 技术热点
- ArXiv AI 论文精选
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


# ========== 配置 ==========
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 抓取数量配置
HN_TOP_N = int(os.getenv("HN_TOP_N", "10"))
ARXIV_TOP_N = int(os.getenv("ARXIV_TOP_N", "5"))

# ArXiv 分类中文映射
CATEGORY_CN = {
    "cs.AI": "人工智能",
    "cs.LG": "机器学习",
    "cs.CL": "自然语言处理",
    "cs.CV": "计算机视觉",
    "cs.RO": "机器人",
    "cs.NE": "神经网络",
    "cs.IR": "信息检索",
    "stat.ML": "统计机器学习",
}


# ========== Hacker News ==========
def fetch_hn_top_stories(n: int = 10) -> List[Dict]:
    """获取 Hacker News 热门文章"""
    try:
        # 获取 Top Stories ID 列表
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        )
        story_ids = resp.json()[:n]

        stories = []
        for sid in story_ids:
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5
                ).json()
                if item and item.get("title"):
                    stories.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "score": item.get("score", 0),
                        "comments": item.get("descendants", 0),
                    })
            except Exception as e:
                print(f"获取 HN 文章 {sid} 失败: {e}")
                continue

        return stories
    except Exception as e:
        print(f"获取 Hacker News 失败: {e}")
        return []


# ========== ArXiv ==========
def fetch_arxiv_papers(categories: List[str] = None, n: int = 5) -> List[Dict]:
    """获取 ArXiv AI 相关论文"""
    if categories is None:
        categories = ["cs.AI", "cs.LG", "cs.CL"]  # AI、机器学习、计算语言学

    try:
        # 构建查询
        cat_query = " OR ".join([f"cat:{cat}" for cat in categories])

        resp = requests.get(
            "http://export.arxiv.org/api/query",
            params={
                "search_query": cat_query,
                "start": 0,
                "max_results": n,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            timeout=15
        )

        # 解析 XML（简单处理）
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)

        papers = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            link = entry.find("atom:id", ns)

            # 获取分类
            categories_elem = entry.findall("atom:category", ns)
            primary_cat = categories_elem[0].get("term") if categories_elem else "cs.AI"

            if title is not None:
                papers.append({
                    "title": " ".join(title.text.split()),  # 清理空白
                    "summary": " ".join(summary.text.split())[:200] + "..." if summary is not None else "",
                    "url": link.text if link is not None else "",
                    "category": primary_cat,
                })

        return papers
    except Exception as e:
        print(f"获取 ArXiv 失败: {e}")
        return []


# ========== 消息格式化 ==========
def format_report(hn_stories: List[Dict], arxiv_papers: List[Dict]) -> str:
    """格式化报告内容"""
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# 📰 AI 热点日报 ({today})",
        "",
    ]

    # Hacker News 部分
    if hn_stories:
        lines.append("## 🔥 技术社区热门（Hacker News）")
        lines.append("")
        for i, story in enumerate(hn_stories, 1):
            lines.append(f"**{i}. [{story['title']}]({story['url']})**")
            lines.append(f"   👍 {story['score']}人点赞 | 💬 {story['comments']}条评论")
            lines.append("")
    else:
        lines.append("## 🔥 技术社区热门（Hacker News）")
        lines.append("暂无数据")
        lines.append("")

    # ArXiv 部分
    if arxiv_papers:
        lines.append("## 📚 AI 前沿论文（ArXiv）")
        lines.append("")
        for i, paper in enumerate(arxiv_papers, 1):
            cat_cn = CATEGORY_CN.get(paper['category'], paper['category'])
            lines.append(f"**{i}. 【{cat_cn}】{paper['title']}**")
            lines.append(f"   {paper['summary']}")
            lines.append(f"   🔗 [查看论文]({paper['url']})")
            lines.append("")
    else:
        lines.append("## 📚 AI 前沿论文（ArXiv）")
        lines.append("暂无数据")
        lines.append("")

    # 数据来源说明
    lines.append("---")
    lines.append("📌 **数据来源：** 技术热点来自 Hacker News 社区，论文来自 ArXiv 学术平台")
    lines.append("")
    lines.append(f"⏰ *生成时间: {datetime.now().strftime('%H:%M')}*")

    return "\n".join(lines)


def format_report_plain(hn_stories: List[Dict], arxiv_papers: List[Dict]) -> str:
    """格式化纯文本报告（用于 Telegram）"""
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"📰 AI 热点日报 ({today})",
        "",
    ]

    # Hacker News 部分
    if hn_stories:
        lines.append("🔥 技术社区热门（Hacker News）")
        lines.append("")
        for i, story in enumerate(hn_stories, 1):
            lines.append(f"{i}. {story['title']}")
            lines.append(f"   👍{story['score']}人点赞 💬{story['comments']}条评论")
            lines.append(f"   {story['url']}")
            lines.append("")

    # ArXiv 部分
    if arxiv_papers:
        lines.append("📚 AI 前沿论文（ArXiv）")
        lines.append("")
        for i, paper in enumerate(arxiv_papers, 1):
            cat_cn = CATEGORY_CN.get(paper['category'], paper['category'])
            lines.append(f"{i}. 【{cat_cn}】{paper['title']}")
            lines.append(f"   {paper['url']}")
            lines.append("")

    lines.append(f"📌 数据来源：Hacker News 社区 + ArXiv 学术平台")
    lines.append(f"⏰ 生成时间: {datetime.now().strftime('%H:%M')}")

    return "\n".join(lines)


# ========== 推送 ==========
def push_to_pushplus(title: str, content: str) -> bool:
    """通过 PushPlus 推送到微信"""
    if not PUSHPLUS_TOKEN:
        print("未配置 PUSHPLUS_TOKEN，跳过微信推送")
        return False

    try:
        resp = requests.post(
            "http://www.pushplus.plus/send",
            json={
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "markdown",
            },
            timeout=10
        )
        result = resp.json()
        if result.get("code") == 200:
            print("✅ PushPlus 推送成功")
            return True
        else:
            print(f"❌ PushPlus 推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ PushPlus 推送异常: {e}")
        return False


def push_to_telegram(content: str) -> bool:
    """通过 Telegram Bot 推送"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("未配置 Telegram，跳过推送")
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": content,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10
        )
        result = resp.json()
        if result.get("ok"):
            print("✅ Telegram 推送成功")
            return True
        else:
            print(f"❌ Telegram 推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ Telegram 推送异常: {e}")
        return False


# ========== 主函数 ==========
def main():
    print("=" * 50)
    print("🚀 AI 热点新闻聚合系统")
    print("=" * 50)
    print(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    # 1. 获取 Hacker News
    print(f"📡 正在获取 Hacker News Top {HN_TOP_N}...")
    hn_stories = fetch_hn_top_stories(HN_TOP_N)
    print(f"   获取到 {len(hn_stories)} 条")

    # 2. 获取 ArXiv 论文
    print(f"📡 正在获取 ArXiv AI 论文 Top {ARXIV_TOP_N}...")
    arxiv_papers = fetch_arxiv_papers(n=ARXIV_TOP_N)
    print(f"   获取到 {len(arxiv_papers)} 篇")

    # 3. 生成报告
    print("")
    print("📝 正在生成报告...")
    report_md = format_report(hn_stories, arxiv_papers)
    report_plain = format_report_plain(hn_stories, arxiv_papers)

    # 4. 推送
    print("")
    print("📤 正在推送...")

    today = datetime.now().strftime("%Y-%m-%d")
    title = f"AI 热点日报 ({today})"

    # 推送到 PushPlus（微信）
    push_to_pushplus(title, report_md)

    # 推送到 Telegram
    push_to_telegram(report_plain)

    print("")
    print("=" * 50)
    print("✅ 完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
