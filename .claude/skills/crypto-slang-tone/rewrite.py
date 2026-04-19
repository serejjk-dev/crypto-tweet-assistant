import json
import random
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
NEWS = WORKSPACE / "news.json"
OUT = WORKSPACE / "tweet_raw.txt"
OPINION_OUT = WORKSPACE / "opinion_raw.txt"

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

TAKES_BY_EVENT = {
    "hack": [
        "audit report said 'passed'. the exploiter said 'hold my gas'. peak defi experience.",
        "if it has a bridge or a multisig, it eventually leaks. third law of crypto.",
        "TVL is just a leaderboard for future victims. anon, diversify your trust.",
        "insurance funds always look fine until you actually need them.",
    ],
    "exploit": [
        "another week, another 'unforeseen edge case'. the edge cases are the product.",
        "devs shipped fast. attackers shipped faster. ngmi.",
    ],
    "pump": [
        "bullish until the first whale remembers what profit is.",
        "retail is late by definition. that's literally the trade.",
        "either a breakout or a bull trap. bullish for engagement either way.",
    ],
    "crash": [
        "copium futures hitting ATH while spot bleeds out.",
        "'long term' is a coping mechanism with a timeline.",
        "bagholders discovering that conviction has a price chart too.",
    ],
    "approve": [
        "regulators arriving three cycles late, as is tradition.",
        "tradfi keeps trying to price crypto. crypto keeps pricing tradfi.",
    ],
    "launch": [
        "docs thin, vibes thick, TGE soon. a classic setup.",
        "another L1/L2/L3 for the graveyard. innovate or airdrop trying.",
        "roadmap written in Figma, delivered in discord, maintained in copium.",
    ],
    "sue": [
        "the real alpha was always the lawyers we retained along the way.",
        "discovery phase will be more entertaining than any bull run.",
    ],
    "ban": [
        "jurisdiction says no. mempool says yes. market shrugs.",
        "banned in country X = listed on chain Y. evolution in action.",
    ],
    "list": [
        "listing pump, 48h retrace. set your watch.",
        "liquidity walks in, exit liquidity follows. textbook.",
    ],
    "delist": [
        "rip liquidity. you had a week to read the memo.",
        "listing committee meeting must have been spicy.",
    ],
    "partner": [
        "in crypto, 'strategic partnership' means the founders followed each other on X.",
        "MOU signed, price pumped 2h, dumped 24h. the standard arc.",
    ],
    "default": [
        "probably nothing. few understand. business as usual.",
        "zoom out: nothing. zoom in: still nothing. bullish.",
        "ser, the charts don't care about your narrative.",
    ],
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


def build_take(item) -> str:
    event = detect_event(item["title"] + " " + item.get("summary", ""))
    pool = TAKES_BY_EVENT.get(event, TAKES_BY_EVENT["default"])
    return random.choice(pool)


def main():
    items = json.loads(NEWS.read_text())
    if not items:
        print("no news")
        return
    top = items[0]
    tweet = build_tweet(top)
    take = build_take(top)
    OUT.write_text(tweet)
    OPINION_OUT.write_text(take)
    print(tweet)
    print("---take---")
    print(take)


if __name__ == "__main__":
    main()
