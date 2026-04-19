import json
import os
import re
import string
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = ROOT / "workspace"
TWEET = WORKSPACE / "tweet_final.txt"
NEWS = WORKSPACE / "news.json"
SEEN = WORKSPACE / "seen.json"
LOG = WORKSPACE / "drafts.log"

load_dotenv(ROOT / ".env")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

DAILY_LIMIT = 6
SEEN_WINDOW = timedelta(hours=48)


def normalize_title(t: str) -> str:
    t = t.lower().strip()
    t = t.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", t)


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_seen():
    if not SEEN.exists():
        return []
    try:
        return json.loads(SEEN.read_text())
    except Exception:
        return []


def save_seen(seen):
    cutoff = datetime.now(timezone.utc) - SEEN_WINDOW
    pruned = [
        s for s in seen
        if datetime.fromisoformat(s["sent_at"]) > cutoff
    ]
    SEEN.write_text(json.dumps(pruned, ensure_ascii=False, indent=2))


def count_today() -> int:
    if not LOG.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    count = 0
    for line in LOG.read_text().splitlines():
        try:
            ts = datetime.fromisoformat(line.split("\t", 1)[0])
            if ts > cutoff:
                count += 1
        except Exception:
            pass
    return count


def main():
    if not TOKEN or not CHAT_ID:
        print("missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        sys.exit(1)

    if not TWEET.exists():
        print("no tweet_final.txt — run humanizer first")
        sys.exit(1)

    tweet = TWEET.read_text().strip()
    if not tweet:
        print("empty tweet")
        sys.exit(1)

    news = json.loads(NEWS.read_text())
    if not news:
        print("no news.json")
        sys.exit(1)
    top = news[0]
    url = top.get("url", "")
    source = top.get("source", "")
    title = top.get("title", "")
    title_key = normalize_title(title)

    seen = load_seen()
    for s in seen:
        if s.get("url") == url or s.get("title_key") == title_key:
            print("duplicate, skipping")
            return

    if count_today() >= DAILY_LIMIT:
        print(f"daily limit {DAILY_LIMIT} reached, skipping")
        return

    body = (
        f"<code>{escape_html(tweet)}</code>\n"
        f"{len(tweet)} chars · {escape_html(source)}"
    )

    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": body,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"telegram error {resp.status_code}: {resp.text}")
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()
    with LOG.open("a") as f:
        f.write(f"{now}\t{source}\t{len(tweet)}\t{url}\n")

    seen.append({
        "sent_at": now,
        "url": url,
        "title_key": title_key,
        "title": title,
    })
    save_seen(seen)
    print("sent ok")


if __name__ == "__main__":
    main()
