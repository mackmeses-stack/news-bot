import os
import asyncio
import logging
import feedparser
import anthropic
import re
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ── تنظیمات ─────────────────────────────────────────────────────────────────
BOT_TOKEN         = os.environ.get("BOT_TOKEN", "8773445175:AAEoblQH6pMmM3sFFgfRTxtUMas2_n1DnTE")
CHAT_ID           = os.environ.get("CHAT_ID", "7697981347")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_NEWS_PER_FEED = 5

RSS_FEEDS = [
    {"name": "BBC فارسی",        "url": "https://feeds.bbci.co.uk/persian/rss.xml"},
    {"name": "ایران اینترنشنال", "url": "https://www.iranintl.com/rss"},
    {"name": "رادیو فردا",       "url": "https://www.radiofarda.com/api/epiqq"},
    {"name": "دویچه وله فارسی",  "url": "https://rss.dw.com/rdf/rss-fa-all"},
    {"name": "العالم",           "url": "https://www.alalam.ir/rss.xml"},
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def fetch_news():
    all_news = []
    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries:
                if count >= MAX_NEWS_PER_FEED:
                    break
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", " ", summary)
                summary = re.sub(r"\s+", " ", summary).strip()[:500]
                if title:
                    all_news.append({"source": feed_info["name"], "title": title, "summary": summary})
                    count += 1
            log.info("✅ %s — %d خبر", feed_info["name"], count)
        except Exception as e:
            log.error("❌ %s: %s", feed_info["name"], e)
    return all_news


def summarize_news(news_list):
    if not news_list:
        return "📭 خبر جدیدی دریافت نشد."
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += f"{i}. [{n['source']}] {n['title']}\n{n['summary']}\n\n"
    prompt = (
        "لطفاً خلاصه‌ای مفید از اخبار زیر به زبان فارسی بنویس.\n"
        "اخبار مهم را دسته‌بندی کن. برای هر خبر یک بند کوتاه بنویس و از ایموجی استفاده کن.\n"
        "در انتها یک جمله جمع‌بندی بنویس.\n\n" + news_text
    )
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("دریافت اخبار...")
    news    = fetch_news()
    summary = summarize_news(news)
    now     = datetime.now().strftime("%Y/%m/%d  %H:%M")
    message = f"📰 *خلاصه اخبار*\n🕐 {now}\n{'─'*28}\n\n{summary}"
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        await bot.send_message(chat_id=CHAT_ID, text=chunk, parse_mode=ParseMode.MARKDOWN)
    log.info("✅ ارسال شد.")


if __name__ == "__main__":
    asyncio.run(main())
