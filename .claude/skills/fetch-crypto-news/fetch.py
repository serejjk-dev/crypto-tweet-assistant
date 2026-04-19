import json
import re
import string
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
WORKSPACE.mkdir(exist_ok=True)
OUT = WORKSPACE / "news.json"
SEEN = WORKSPACE / "seen.json"

MAX_AGE = timedelta(hours=12)
NOW = datetime.now(timezone.utc)

LOUD_VERBS = {
    "hacked", "launches", "approves", "sues", "lists", "delists",
    "pumps", "crashes", "partners", "files", "rugs", "freezes", "bans",
    "exploits", "exploited", "seizes", "raids", "halts",
}
BIG_TICKERS = {
    "btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xrp", "ripple",
}
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "by", "from", "as", "at", "is", "are", "was", "were", "be",
    "been", "has", "have", "had", "will", "would", "could", "should",
    "this", "that", "these", "those", "says", "said", "new", "its", "his",
    "her", "who", "what", "when", "where", "why", "how", "over", "after",
    "into", "about",
}
JACCARD_THRESHOLD = 0.5


def content_words(title: str) -> set[str]:
    words = re.findall(r"[a-z$]+", title.lower())
    return {w for w in words if len(w) >= 4 and w not in STOPWORDS}


def is_similar(a: set[str], b: set[str]) -> bool:
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= JACCARD_THRESHOLD


def normalize_title(t: str) -> str:
    t = t.lower().strip()
    t = t.translate(str.maketrans("", "", string.punctuation))
    t = re.sub(r"\s+", " ", t)
    return t


def parse_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return None


def fetch_rss(url: str, source: str):
    items = []
    try:
        feed = feedparser.parse(url)
        for e in feed.entries[:40]:
            published = parse_date(e)
            if not published:
                continue
            items.append({
                "title": (e.get("title") or "").strip(),
                "url": (e.get("link") or "").strip(),
                "source": source,
                "summary": re.sub(r"<[^>]+>", "", e.get("summary", ""))[:300].strip(),
                "published_at": published.isoformat(),
            })
    except Exception as ex:
        print(f"[{source}] error: {ex}")
    return items


def fetch_cryptocompare():
    items = []
    try:
        r = requests.get(
            "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
            timeout=15,
        )
        data = r.json().get("Data") or []
        for n in data[:40]:
            ts = n.get("published_on")
            if not ts:
                continue
            items.append({
                "title": (n.get("title") or "").strip(),
                "url": (n.get("url") or "").strip(),
                "source": f"CryptoCompare/{n.get('source', '')}",
                "summary": (n.get("body") or "")[:300].strip(),
                "published_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            })
    except Exception as ex:
        print(f"[cryptocompare] error: {ex}")
    return items


def score(item) -> int:
    s = 0
    title_low = item["title"].lower()
    words = set(re.findall(r"[a-z]+", title_low))
    if words & LOUD_VERBS:
        s += 3
    if words & BIG_TICKERS:
        s += 2
    published = datetime.fromisoformat(item["published_at"])
    if NOW - published < timedelta(hours=3):
        s += 1
    return s


def main():
    jobs = [
        (fetch_rss, "https://cryptopanic.com/news/rss/", "CryptoPanic"),
        (fetch_rss, "https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
        (fetch_rss, "https://decrypt.co/feed", "Decrypt"),
        (fetch_cryptocompare, None, None),
    ]
    all_items = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = []
        for job in jobs:
            fn = job[0]
            if fn is fetch_cryptocompare:
                futures.append(ex.submit(fn))
            else:
                futures.append(ex.submit(fn, job[1], job[2]))
        for f in futures:
            all_items.extend(f.result())

    fresh = []
    for it in all_items:
        if not it["title"] or not it["url"]:
            continue
        published = datetime.fromisoformat(it["published_at"])
        if NOW - published > MAX_AGE:
            continue
        fresh.append(it)

    seen_in_batch = {}
    for it in fresh:
        key = normalize_title(it["title"])
        if key and key not in seen_in_batch:
            seen_in_batch[key] = it
    unique = list(seen_in_batch.values())

    already_sent = []
    if SEEN.exists():
        try:
            already_sent = json.loads(SEEN.read_text())
        except Exception:
            already_sent = []
    sent_urls = {s.get("url", "") for s in already_sent}
    sent_keys = {s.get("title_key", "") for s in already_sent}
    sent_bags = [content_words(s.get("title", "")) for s in already_sent]

    filtered = []
    for it in unique:
        if it["url"] in sent_urls:
            continue
        if normalize_title(it["title"]) in sent_keys:
            continue
        bag = content_words(it["title"])
        if any(is_similar(bag, prev) for prev in sent_bags):
            continue
        filtered.append(it)

    filtered.sort(key=lambda x: (score(x), x["published_at"]), reverse=True)
    top = filtered[:3]

    OUT.write_text(json.dumps(top, ensure_ascii=False, indent=2))
    print(f"Saved {len(top)} items -> {OUT}")
    for i, it in enumerate(top, 1):
        print(f"  {i}. [{it['source']}] {it['title']}")


if __name__ == "__main__":
    main()
