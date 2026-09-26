from __future__ import annotations

import re
import unicodedata

RATING_MAP = {
    "true": 1.0,
    "verdadeiro": 1.0,
    "correto": 1.0,
    "mostly true": 0.75,
    "majoritariamente verdadeiro": 0.75,
    "partly true": 0.5,
    "half true": 0.5,
    "meia verdade": 0.5,
    "mixed": 0.5,
    "impreciso": 0.5,
    "mostly false": 0.25,
    "majoritariamente falso": 0.25,
    "misleading": 0.25,
    "enganoso": 0.25,
    "false": 0.0,
    "falso": 0.0,
    "fake": 0.0,
}


def normalize_rating(textual_rating: str | None) -> float | None:
    if not textual_rating:
        return None
    normalized = normalize_text(textual_rating)
    if normalized in RATING_MAP:
        return RATING_MAP[normalized]
    for key, value in RATING_MAP.items():
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return value
    return None


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()
