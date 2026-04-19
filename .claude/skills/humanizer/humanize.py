import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
IN = WORKSPACE / "tweet_raw.txt"
NEWS = WORKSPACE / "news.json"
OUT = WORKSPACE / "tweet_final.txt"
OPINION_IN = WORKSPACE / "opinion_raw.txt"
OPINION_OUT = WORKSPACE / "opinion_final.txt"

BANNED_WORDS = [
    "delve", "tapestry", "realm", "landscape", "navigate",
    "robust", "seamless",
    "game changer", "game-changer",
    "revolutionary", "unprecedented",
]
BANNED_PHRASES = [
    "в мире криптовалют",
    "стоит отметить",
    "не секрет что",
    "не секрет, что",
    "in the ever-evolving",
    "in the ever evolving",
]

MAX_LEN = 270


def strip_banned_words(text: str) -> str:
    for w in BANNED_WORDS:
        text = re.sub(rf"\b{re.escape(w)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bleverage\s+(?=\w)", "use ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bleveraging\b", "using", text, flags=re.IGNORECASE)
    return text


def strip_banned_phrases(text: str) -> str:
    for p in BANNED_PHRASES:
        text = re.sub(re.escape(p), "", text, flags=re.IGNORECASE)
    return text


def fix_not_x_but_y(text: str) -> str:
    pattern = re.compile(r"не\s+[\w$]+,?\s+а\s+[\w$]+", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if len(matches) <= 1:
        return text
    result = text
    for m in matches[1:][::-1]:
        start, end = m.span()
        inner = m.group(0)
        kept = re.sub(r".*?а\s+", "", inner, flags=re.IGNORECASE)
        result = result[:start] + kept + result[end:]
    return result


def replace_em_dash(text: str) -> str:
    text = text.replace(" — ", ". ")
    text = text.replace("—", "-")
    return text


def collapse_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def get_source_url() -> str:
    try:
        items = json.loads(NEWS.read_text())
        if items:
            return items[0].get("url", "")
    except Exception:
        pass
    return ""


def fit_with_url(text: str, url: str) -> str:
    if not url:
        return text[:MAX_LEN].rstrip()
    budget = MAX_LEN - len(url) - 1
    if len(text) <= budget:
        return text
    cut = text[:budget].rstrip()
    cut = re.sub(r"[,;:\-\s]+$", "", cut)
    if len(cut) > 3:
        cut = cut[:-3] + "..."
    return cut


def clean(text: str) -> str:
    t = strip_banned_phrases(text)
    t = strip_banned_words(t)
    t = fix_not_x_but_y(t)
    t = replace_em_dash(t)
    return collapse_whitespace(t)


def main():
    raw = IN.read_text().strip()
    cleaned = clean(raw)
    url = get_source_url()
    fitted = fit_with_url(cleaned, url)
    OUT.write_text(fitted)
    print(fitted)

    if OPINION_IN.exists():
        op_raw = OPINION_IN.read_text().strip()
        op_clean = clean(op_raw)
        if len(op_clean) > 220:
            op_clean = op_clean[:217].rstrip() + "..."
        OPINION_OUT.write_text(op_clean)
        print("---take---")
        print(op_clean)


if __name__ == "__main__":
    main()
