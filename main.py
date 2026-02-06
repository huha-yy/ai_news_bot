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
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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


# ========== AI 翻译 ==========
TRANSLATE_PROMPT = (
    "请将以下英文文本逐条翻译为简洁的中文，保持编号格式。"
    "只输出翻译结果，不要加任何解释。"
    "专有名词（如公司名、产品名、人名）保留英文原文。\n\n"
)


def _parse_numbered_result(result_text: str, expected_count: int) -> Optional[List[str]]:
    """解析编号格式的翻译结果"""
    translated = []
    for line in result_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 去掉编号前缀如 "1. " "1、" "1."
        for prefix_len in range(1, 5):
            if line[prefix_len:prefix_len+1] in ".、" and line[:prefix_len].isdigit():
                line = line[prefix_len+1:].strip()
                break
        translated.append(line)

    if len(translated) == expected_count:
        return translated
    print(f"翻译结果数量不匹配（期望 {expected_count}，得到 {len(translated)}）")
    return None


def _translate_nvidia(texts: List[str]) -> Optional[List[str]]:
    """使用 NVIDIA Kimi K2.5 翻译"""
    numbered = "\n".join([f"{i+1}. {t}" for i, t in enumerate(texts)])
    try:
        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Accept": "application/json",
            },
            json={
                "model": "moonshotai/kimi-k2.5",
                "messages": [{"role": "user", "content": TRANSLATE_PROMPT + numbered}],
                "max_tokens": 4096,
                "temperature": 0.3,
                "stream": False,
            },
            timeout=60
        )
        data = resp.json()
        result_text = data["choices"][0]["message"]["content"]
        return _parse_numbered_result(result_text, len(texts))
    except Exception as e:
        print(f"NVIDIA Kimi 翻译失败: {e}")
        return None


def _translate_gemini(texts: List[str]) -> Optional[List[str]]:
    """使用 Gemini 翻译"""
    numbered = "\n".join([f"{i+1}. {t}" for i, t in enumerate(texts)])
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": TRANSLATE_PROMPT + numbered}]}]},
            timeout=30
        )
        data = resp.json()
        result_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_numbered_result(result_text, len(texts))
    except Exception as e:
        print(f"Gemini 翻译失败: {e}")
        return None


def translate_texts(texts: List[str]) -> List[str]:
    """批量翻译：优先 NVIDIA Kimi，降级 Gemini，都失败返回原文"""
    if not texts:
        return texts

    # 优先使用 NVIDIA Kimi K2.5
    if NVIDIA_API_KEY:
        print("   使用 NVIDIA Kimi K2.5 翻译...")
        result = _translate_nvidia(texts)
        if result:
            return result
        print("   NVIDIA 翻译失败，尝试 Gemini 降级...")

    # 降级到 Gemini
    if GEMINI_API_KEY:
        print("   使用 Gemini 翻译...")
        result = _translate_gemini(texts)
        if result:
            return result

    print("   翻译不可用，使用英文原文")
    return texts


def has_translate_key() -> bool:
    """检查是否有任意翻译 API Key"""
    return bool(NVIDIA_API_KEY or GEMINI_API_KEY)


def translate_stories(stories: List[Dict]) -> List[Dict]:
    """翻译 HN 文章标题"""
    if not stories or not has_translate_key():
        return stories

    titles = [s["title"] for s in stories]
    translated = translate_texts(titles)
    for i, s in enumerate(stories):
        s["title_cn"] = translated[i]
    return stories


def translate_papers(papers: List[Dict]) -> List[Dict]:
    """翻译 ArXiv 论文标题和摘要"""
    if not papers or not has_translate_key():
        return papers

    all_texts = []
    for p in papers:
        all_texts.append(p["title"])
        all_texts.append(p["summary"])

    translated = translate_texts(all_texts)
    for i, p in enumerate(papers):
        p["title_cn"] = translated[i * 2]
        p["summary_cn"] = translated[i * 2 + 1]
    return papers


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
            title_display = story.get('title_cn', story['title'])
            lines.append(f"**{i}. [{title_display}]({story['url']})**")
            if title_display != story['title']:
                lines.append(f"   原标题：{story['title']}")
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
            title_display = paper.get('title_cn', paper['title'])
            summary_display = paper.get('summary_cn', paper['summary'])
            lines.append(f"**{i}. 【{cat_cn}】{title_display}**")
            lines.append(f"   {summary_display}")
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
            title_display = story.get('title_cn', story['title'])
            lines.append(f"{i}. {title_display}")
            lines.append(f"   👍{story['score']}人点赞 💬{story['comments']}条评论")
            lines.append(f"   {story['url']}")
            lines.append("")

    # ArXiv 部分
    if arxiv_papers:
        lines.append("📚 AI 前沿论文（ArXiv）")
        lines.append("")
        for i, paper in enumerate(arxiv_papers, 1):
            cat_cn = CATEGORY_CN.get(paper['category'], paper['category'])
            title_display = paper.get('title_cn', paper['title'])
            lines.append(f"{i}. 【{cat_cn}】{title_display}")
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

    # 3. AI 翻译为中文
    if has_translate_key():
        provider = "NVIDIA Kimi" if NVIDIA_API_KEY else "Gemini"
        print("")
        print(f"🌐 正在翻译为中文（{provider}）...")
        hn_stories = translate_stories(hn_stories)
        print(f"   HN 标题翻译完成")
        arxiv_papers = translate_papers(arxiv_papers)
        print(f"   论文翻译完成")
    else:
        print("\n⚠️ 未配置翻译 API Key（NVIDIA_API_KEY 或 GEMINI_API_KEY），跳过中文翻译")

    # 4. 生成报告
    print("")
    print("📝 正在生成报告...")
    report_md = format_report(hn_stories, arxiv_papers)
    report_plain = format_report_plain(hn_stories, arxiv_papers)

    # 5. 推送
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
