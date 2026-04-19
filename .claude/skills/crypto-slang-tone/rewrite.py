import json
import random
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
NEWS = WORKSPACE / "news.json"
OUT = WORKSPACE / "tweet_raw.txt"

TICKER_NAMES = {
    "bitcoin": "$BTC", "btc": "$BTC",
    "ethereum": "$ETH", "eth": "$ETH",
    "solana": "$SOL", "sol": "$SOL",
    "ripple": "$XRP", "xrp": "$XRP",
    "dogecoin": "$DOGE", "doge": "$DOGE",
    "cardano": "$ADA", "ada": "$ADA",
    "avalanche": "$AVAX", "avax": "$AVAX",
    "polygon": "$MATIC", "matic": "$MATIC",
    "chainlink": "$LINK", "link": "$LINK",
    "aave": "$AAVE",
    "uniswap": "$UNI", "uni": "$UNI",
    "binance": "$BNB", "bnb": "$BNB",
    "tether": "$USDT",
    "usdc": "$USDC",
    "tron": "$TRX", "trx": "$TRX",
    "polkadot": "$DOT", "dot": "$DOT",
    "shiba": "$SHIB",
    "pepe": "$PEPE",
}

CAP_STOP = {
    "The", "A", "An", "New", "As", "In", "On", "At", "To", "For", "And",
    "Or", "Of", "From", "With", "By", "Is", "Are", "Was", "Were", "This",
    "That", "Over", "After", "Into", "Before", "Through", "Q1", "Q2",
    "Q3", "Q4", "US", "UK", "EU", "AI",
}

EVENT_KEYWORDS = {
    "hack":    ["hack", "hacked", "exploit", "exploited", "drain", "drained", "stolen", "breach"],
    "pump":    ["pump", "surge", "surges", "rally", "rallies", "soars", "soar", "jumps", "jump", "rockets", "skyrockets"],
    "crash":   ["crash", "crashes", "plunge", "plunges", "tanks", "drops", "drop", "collapse", "collapses", "tumbles", "bleed", "dumps"],
    "launch":  ["launch", "launches", "launched", "debuts", "debut", "ships", "shipped", "live", "releases", "unveils"],
    "approve": ["approve", "approves", "approved", "greenlight", "greenlights"],
    "sue":     ["sue", "sues", "sued", "lawsuit", "charges", "charged", "court"],
    "ban":     ["ban", "bans", "banned", "prohibited", "outlawed"],
    "delist":  ["delist", "delists", "delisted", "delisting"],
    "list":    ["list", "lists", "listed", "listing"],
    "partner": ["partners", "partnership", "teams up", "joins forces", "collaborates"],
    "raise":   ["raises", "raised", "funding", "round", "seed"],
}

TEMPLATES = {
    "hack": [
        "{primary} just got rekt{amount}. audit said passed, exploiter said hold my gas. every cycle same lesson, peak defi experience.",
        "another {primary} hack{amount}. TVL is a leaderboard for future victims. ser, diversify your trust, not just your bags.",
        "{primary} drained{amount}. devs rebuilt trust, attacker rebuilt a house. ngmi but here we are anyway.",
        "told you {primary} had strong fundamentals. turns out the fundamentals were for getting exploited{amount}. rekt.",
        "{primary} lost{amount} to a 'previously unknown vector'. translation: we shipped fast and prayed. copium loading.",
    ],
    "exploit": [
        "{primary} hit by an exploit{amount}. another unforeseen edge case that's clearly a product feature at this point.",
        "{primary} drained{amount}. devs shipped fast, attackers shipped faster. third law of crypto.",
        "{primary} rekt{amount}. the bug bounty was smaller than the bounty. classic.",
    ],
    "pump": [
        "{primary} pumping{percent}. retail is late by definition, that's literally the trade.",
        "{primary}{percent} and timeline still calls it bearish. bullish until the first whale remembers what profit is.",
        "{primary} going vertical{percent}. wake me when my bags get the same memo.",
        "{primary}{percent} in a day. either breakout or bull trap, either way bullish for engagement.",
    ],
    "crash": [
        "{primary} bleeding{percent}. the 'long term thesis' is aging in real time. copium rally inbound.",
        "{primary}{percent}. discord posting charts from 2022, textbook copium cycle. ser, zoom out harder.",
        "{primary} down{percent}. diamond hands or bagholder, yes. that's the whole menu.",
        "{primary} tanks{percent}. someone remembered what profit is. everyone else remembered they were never up.",
    ],
    "launch": [
        "new {primary} launch. docs thin, vibes thick, TGE any day now. a classic setup.",
        "{primary} live. probably nothing until it's something, at which point you're already late. few understand.",
        "{primary} just shipped. another L-something for the graveyard, bullish on engagement, bearish on TVL.",
        "{primary} going live. roadmap written in figma, delivered in discord, maintained in copium. send it anyway.",
    ],
    "approve": [
        "{primary} officially approved. regulators arriving three cycles late, as tradition. tradfi keeps trying.",
        "{primary} got the green light. the grown-ups finally arrived. only took a decade and several bear markets.",
        "{primary} approved. bullish for compliance lawyers, mid for everyone else.",
    ],
    "sue": [
        "{primary} heading to court. the real alpha was always the lawyers we retained along the way.",
        "{primary} in legal trouble again. discovery phase more entertaining than any bull run. popcorn arc.",
        "sec vs {primary}. ser, this is a casino with a side of courtroom drama.",
    ],
    "ban": [
        "{primary} banned somewhere new. mempool didn't get the memo, market shrugs. evolution in action.",
        "another jurisdiction says no to {primary}. permissionless tech stays, well, permissionless.",
        "{primary} outlawed. regulators discovering they can't ban math. bullish for vpns.",
    ],
    "list": [
        "{primary} listing incoming. 48h pump, 72h retrace. set your watch.",
        "{primary} on a major cex now. liquidity walks in, exit liquidity follows. textbook.",
        "{primary} listed. congrats to early holders, condolences to late ones.",
    ],
    "delist": [
        "{primary} delisted. rip liquidity, you had a week to read the room. anon, diversify.",
        "{primary} off the menu. listing committee meeting must have been spicy.",
    ],
    "partner": [
        "{primary} announces partnership. in crypto that means the founders followed each other on x.",
        "{primary} collab season. MOU signed, price pumps 2h then dumps 24h. the standard arc.",
        "{primary} teaming up with someone. press release pump, fundamentals unchanged. business as usual.",
    ],
    "raise": [
        "{primary} raising{amount}. VCs funding the next graveyard headstone. bullish for founders, mid for users.",
        "{primary} closed a round{amount}. tier-1 names, thin product, TGE in the deck. you know the script.",
    ],
    "default": [
        "{primary} in the news again. probably nothing, but few understand what probably nothing really means.",
        "{primary} doing {primary} things. ser, zoom out. the charts don't care about your narrative.",
        "{primary} making headlines. another day in the casino. stay degen, stay humble.",
        "{primary} on the timeline. bullish, bearish, delusional, pick one. they're all the same trade.",
    ],
}


def detect_event(text: str) -> str:
    t = " " + text.lower() + " "
    best_event = "default"
    best_pos = len(t)
    for event, kws in EVENT_KEYWORDS.items():
        for kw in kws:
            idx = t.find(f" {kw}")
            if idx != -1 and idx < best_pos:
                best_event = event
                best_pos = idx
    return best_event


def extract_primary(title: str, summary: str) -> str:
    combined = title + " " + summary

    for name, ticker in TICKER_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", combined, re.IGNORECASE):
            return ticker

    m = re.search(r"\b([A-Z]{2,6})\b\s+(?:token|coin)", combined)
    if m and m.group(1) not in CAP_STOP:
        return f"${m.group(1)}"

    m = re.search(r"\$([A-Z]{2,6})\b", combined)
    if m:
        return f"${m.group(1)}"

    words = title.split()
    for i, w in enumerate(words):
        clean = re.sub(r"[^\w]", "", w)
        if not clean or not clean[0].isupper() or clean in CAP_STOP:
            continue
        parts = [clean]
        for j in range(i + 1, min(i + 3, len(words))):
            nxt = re.sub(r"[^\w]", "", words[j])
            if nxt and nxt[0].isupper() and nxt not in CAP_STOP:
                parts.append(nxt)
            else:
                break
        return " ".join(parts)
    return "this"


def extract_amount(text: str) -> str:
    m = re.search(
        r"\$\d[\d.,]*\s*(?:billion|million|trillion|[BMTkK])?",
        text,
    )
    if not m:
        return ""
    return " for " + m.group(0).strip()


def extract_percent(text: str, direction: str | None) -> str:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not m:
        return ""
    num = m.group(1)
    if direction == "up":
        return f" +{num}%"
    if direction == "down":
        return f" -{num}%"
    return f" {num}%"


def build_tweet(item) -> str:
    title = item.get("title", "")
    summary = item.get("summary", "")
    combined = f"{title} {summary}"

    event = detect_event(combined)
    primary = extract_primary(title, summary)
    amount = extract_amount(combined)
    direction = "up" if event == "pump" else ("down" if event == "crash" else None)
    percent = extract_percent(combined, direction)

    pool = list(TEMPLATES.get(event, TEMPLATES["default"]))
    random.shuffle(pool)

    chosen = None
    for tpl in pool:
        if "{amount}" in tpl and not amount:
            continue
        if "{percent}" in tpl and not percent:
            continue
        chosen = tpl
        break
    if not chosen:
        chosen = pool[0]

    out = chosen.format(primary=primary, amount=amount, percent=percent)
    out = re.sub(r"\s+", " ", out).strip()
    if len(out) > 270:
        out = out[:267].rstrip() + "..."
    return out


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
