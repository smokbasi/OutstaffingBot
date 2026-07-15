"""Russian lemmatization for content moderation (Phase 9 — lemma layer)."""

from __future__ import annotations

import re
from functools import lru_cache

_CYRILLIC_ONLY_TOKEN = re.compile(r"^[а-яё]+$", re.IGNORECASE)
_MIN_LEMMA_TOKEN_LEN = 3


@lru_cache(maxsize=1)
def _morph_analyzer():
    import pymorphy3

    return pymorphy3.MorphAnalyzer()


@lru_cache(maxsize=8192)
def lemmatize_ru_token(token: str) -> str:
    """Return dictionary lemma for a Cyrillic token; passthrough otherwise."""
    lowered = token.lower().replace("ё", "е")
    if len(lowered) < _MIN_LEMMA_TOKEN_LEN or not _CYRILLIC_ONLY_TOKEN.match(lowered):
        return lowered

    parsed = _morph_analyzer().parse(lowered)
    if not parsed:
        return lowered

    return parsed[0].normal_form.replace("ё", "е")


def clear_lemma_cache() -> None:
    """Test helper — reset memoized lemmas."""
    lemmatize_ru_token.cache_clear()
