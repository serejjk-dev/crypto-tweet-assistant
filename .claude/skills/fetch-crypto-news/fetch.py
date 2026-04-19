import json
import re
import string
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

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
    "collapses", "plunges", "jumps", "surges", "soars", "tumbles",
    "raises", "dumps", "drains", "drained", "tanks", "rockets",
    "plummets", "slashes", "unveils", "debuts", "ships",
}
BIG_TICKERS = {
    "btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xrp", "ripple",
}
CRYPTO_TERMS = {
    "crypto", "cryptocurrency", "blockchain", "defi", "dao", "nft",
    "token", "tokens", "coin", "coins", "wallet", "wallets",
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp",
    "stablecoin", "stablecoins", "cex", "dex", "cefi",
    "protocol", "protocols", "chain", "web3", "ledger",
    "staking", "mining", "miner", "miners", "dapp", "dapps",
    "airdrop", "validator", "validators", "onchain", "on-chain",
    "ethereum", "binance", "coinbase", "kraken", "ftx",
    "usdt", "usdc", "bnb", "doge", "shib", "pepe", "ada",
    "aave", "uniswap", "chainlink", "polygon", "avalanche",
    "rollup", "rollups", "l1", "l2", "layer", "bridge", "tvl",
    "memecoin", "memecoins", "altcoin", "altcoins", "degen",
    "wallet", "sec", "etf",
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


ATOM_NS = "{http://www.w3.org/2005/Atom}"


def parse_rfc_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def text_of(el, *names) -> str:
    if el is None:
        return ""
    for n in names:
        child = el.find(n)
        if child is not None and child.text:
            return child.text.strip()
    return ""


def _strip_cdata(s: str) -> str:
    if not s:
        return ""
    s = s.replace("<![CDATA[", "").replace("]]>", "")
    return s.strip()


def _parse_lenient_rss(xml_text: str, source: str):
    items = []
    for m in re.finditer(r"<item\b[^>]*>(.*?)</item>", xml_text, re.DOTALL | re.IGNORECASE):
        inner = m.group(1)
        def grab(tag):
            mt = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", inner, re.DOTALL | re.IGNORECASE)
            return _strip_cdata(mt.group(1)) if mt else ""
        title = grab("title")
        link = grab("link")
        pub = grab("pubDate") or grab("dc:date")
        raw_summary = grab("description") or grab("content:encoded")
        published = parse_rfc_date(pub)
        if not published or not title or not link:
            continue
        summary = re.sub(r"<[^>]+>", "", raw_summary)[:300].strip()
        items.append({
            "title": title,
            "url": link,
            "source": source,
            "summary": summary,
            "published_at": published.isoformat(),
        })
        if len(items) >= 40:
            break
    return items


def fetch_rss(url: str, source: str):
    items = []
    xml_bytes = b""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
    except Exception as ex:
        print(f"[{source}] fetch error: {ex}")
        return items

    try:
        root = ET.fromstring(xml_bytes)
        entries = root.findall(".//item")
        is_atom = False
        if not entries:
            entries = root.findall(f".//{ATOM_NS}entry")
            is_atom = True

        for e in entries[:40]:
            if is_atom:
                title = text_of(e, f"{ATOM_NS}title")
                link_el = e.find(f"{ATOM_NS}link")
                link = (link_el.get("href") if link_el is not None else "") or ""
                pub = text_of(e, f"{ATOM_NS}published", f"{ATOM_NS}updated")
                raw_summary = text_of(e, f"{ATOM_NS}summary", f"{ATOM_NS}content")
            else:
                title = text_of(e, "title")
                link = text_of(e, "link")
                pub = text_of(e, "pubDate", "{http://purl.org/dc/elements/1.1/}date")
                raw_summary = text_of(e, "description", "{http://purl.org/rss/1.0/modules/content/}encoded")

            published = parse_rfc_date(pub)
            if not published:
                continue
            summary = re.sub(r"<[^>]+>", "", raw_summary)[:300].strip()
            items.append({
                "title": (title or "").strip(),
                "url": (link or "").strip(),
                "source": source,
                "summary": summary,
                "published_at": published.isoformat(),
            })
    except ET.ParseError as ex:
        print(f"[{source}] strict parse failed ({ex}), falling back to lenient")
        try:
            text = xml_bytes.decode("utf-8", errors="ignore")
            items = _parse_lenient_rss(text, source)
        except Exception as ex2:
            print(f"[{source}] lenient parse error: {ex2}")
    except Exception as ex:
        print(f"[{source}] parse error: {ex}")
    return items


def fetch_cryptocompare():
    items = []
    try:
        r = requests.get(
            "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
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


def fetch_reddit():
    items = []
    try:
        req = urllib.request.Request(
            "https://www.reddit.com/r/CryptoCurrency/hot.json?limit=40",
            headers={"User-Agent": "crypto-tweet-bot/1.0 (contact via github)"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("stickied") or d.get("over_18"):
                continue
            ts = d.get("created_utc")
            if not ts:
                continue
            title = (d.get("title") or "").strip()
            url = d.get("url_overridden_by_dest") or ("https://reddit.com" + d.get("permalink", ""))
            summary = (d.get("selftext") or "")[:300].strip()
            items.append({
                "title": title,
                "url": url,
                "source": "Reddit/r/CryptoCurrency",
                "summary": summary,
                "published_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            })
    except Exception as ex:
        print(f"[Reddit] error: {ex}")
    return items


def fetch_google_news(query: str, label: str):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    return fetch_rss(url, f"GoogleNews/{label}")


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
    all_items = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = [
            ex.submit(fetch_google_news, "bitcoin OR ethereum OR crypto", "crypto"),
            ex.submit(fetch_google_news, "defi OR solana OR altcoin", "defi"),
            ex.submit(fetch_reddit),
            ex.submit(fetch_cryptocompare),
            ex.submit(fetch_rss, "https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
            ex.submit(fetch_rss, "https://decrypt.co/feed", "Decrypt"),
        ]
        for f in futures:
            all_items.extend(f.result())

    fresh = []
    for it in all_items:
        if not it["title"] or not it["url"]:
            continue
        published = datetime.fromisoformat(it["published_at"])
        if NOW - published > MAX_AGE:
            continue
        blob = (it["title"] + " " + it.get("summary", "")).lower()
        blob_words = set(re.findall(r"[a-z0-9]+", blob))
        if not (blob_words & CRYPTO_TERMS):
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
