import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
NEWS = WORKSPACE / "news.json"
OUT = WORKSPACE / "tweet_raw.txt"

TICKERS = {
    "bitcoin": "$BTC", "btc": "$BTC",
    "ethereum": "$ETH", "eth": "$ETH",
    "solana": "$SOL", "sol": "$SOL",
    "ripple": "$XRP", "xrp": "$XRP",
    "dogecoin": "$DOGE", "doge": "$DOGE",
    "cardano": "$ADA", "ada": "$ADA",
}

SLANG_BY_EVENT = {
    "hack":   ["rekt", "ngmi", "probably nothing"],
    "exploit": ["rekt", "ngmi"],
    "pump":   ["wagmi", "bullish af", "degen szn"],
    "crash":  ["rekt", "copium", "bagholders in shambles"],
    "approve": ["bullish", "few understand"],
    "launch": ["probably nothing", "few understand"],
    "sue":    ["ser, this is a casino", "anon, not again"],
    "ban":    ["ngmi", "copium"],
    "list":   ["bullish", "wagmi"],
    "delist": ["rekt", "ngmi"],
    "partner": ["bullish", "probably nothing"],
}


def detect_event(text: str) -> str:
    t = text.lower()
    for key in ("hack", "exploit", "pump", "crash", "approve",
                "launch", "sue", "ban", "list", "delist", "partner"):
        if key in t:
            return key
    return "launch"


def tickerize(text: str) -> str:
    def repl(m):
        w = m.group(0)
        return TICKERS.get(w.lower(), w)
    pattern = r"\b(" + "|".join(re.escape(k) for k in TICKERS.keys()) + r")\b"
    return re.sub(pattern, repl, text, flags=re.IGNORECASE)


def strip_loud(text: str) -> str:
    text = re.sub(r"\bBREAKING[:\s]*", "", text, flags=re.IGNORECASE)
    def lower_caps(m):
        w = m.group(0)
        return w.lower() if w.isupper() and len(w) > 3 else w
    return re.sub(r"\b[A-Z]{4,}\b", lower_caps, text)


def build_tweet(item) -> str:
    title = strip_loud(item["title"])
    title = tickerize(title).rstrip(".?!")
    event = detect_event(item["title"] + " " + item.get("summary", ""))
    slang = SLANG_BY_EVENT.get(event, ["probably nothing"])[0]

    base = f"{title}. {slang}."
    base = re.sub(r"\s+", " ", base).strip()

    if len(base) < 180:
        summary = tickerize(strip_loud(item.get("summary", ""))).split(".")[0]
        summary = re.sub(r"\s+", " ", summary).strip()
        if summary and summary.lower() not in base.lower():
            candidate = f"{title}. {summary}. {slang}."
            if len(candidate) <= 240:
                base = candidate

    if len(base) > 240:
        base = base[:237].rstrip() + "..."

    if len(base) < 180:
        tail_options = [" few understand.", " ser.", " ngmi.", " bullish."]
        for extra in tail_options:
            if 180 <= len(base + extra) <= 240:
                base = base + extra
                break

    return base


def main():
    items = json.loads(NEWS.read_text())
    if not items:
        print("no news")
        return
    top = items[0]
    tweet = build_tweet(top)
    OUT.write_text(tweet)
    print(tweet)


if __name__ == "__main__":
    main()
