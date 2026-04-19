import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
IN = WORKSPACE / "tweet_raw.txt"
OUT = WORKSPACE / "tweet_final.txt"

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


def clean(text: str) -> str:
    t = strip_banned_phrases(text)
    t = strip_banned_words(t)
    t = fix_not_x_but_y(t)
    t = replace_em_dash(t)
    return collapse_whitespace(t)


def main():
    raw = IN.read_text().strip()
    cleaned = clean(raw)
    if len(cleaned) > MAX_LEN:
        cleaned = cleaned[:MAX_LEN - 3].rstrip() + "..."
    OUT.write_text(cleaned)
    print(cleaned)


if __name__ == "__main__":
    main()
