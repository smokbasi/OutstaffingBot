"""Content moderation: wordlist matching with normalization (Phase 9.1–9.4)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

MODERATION_DIR = Path(__file__).resolve().parents[2] / "data" / "moderation"

CONTENT_REJECTED_MESSAGE = (
    "Текст не прошёл проверку на недопустимое содержание. "
    "Измените формулировки и попробуйте снова."
)

_LEET_TRANSLATION = str.maketrans(
    {
        "@": "a",
        "0": "o",
        "$": "s",
        "3": "e",
        "1": "i",
        "!": "i",
    }
)

# Latin letters that visually match Cyrillic — used for homoglyph / mixed-script evasion.
_HOMOGLYPH_LATIN_TO_CYRILLIC = str.maketrans(
    {
        "a": "а",
        "b": "в",
        "c": "с",
        "e": "е",
        "h": "н",
        "k": "к",
        "m": "м",
        "o": "о",
        "p": "р",
        "t": "т",
        "x": "х",
        "y": "у",
    }
)

_CYRILLIC_TO_LATIN_HOMOGLYPH = str.maketrans(
    {
        "а": "a",
        "в": "b",
        "с": "c",
        "е": "e",
        "н": "h",
        "к": "k",
        "м": "m",
        "о": "o",
        "р": "p",
        "т": "t",
        "х": "x",
        "у": "y",
        "и": "i",
    }
)

# Full phonetic map for mixed-script tokens (e.g. пидor → pidor).
_CYRILLIC_PHONETIC_TO_LATIN = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "sh",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)

# Latin translit → canonical Cyrillic before wordlist match (Phase 9.3).
_TRANSLIT_TO_CYRILLIC: dict[str, str] = {
    "blyad": "блядь",
    "bliad": "блядь",
    "blat": "блять",
    "bljat": "блять",
    "blyat": "блять",
    "ebal": "ебал",
    "ebat": "ебать",
    "govno": "говно",
    "heroin": "героин",
    "hui": "хуй",
    "huilo": "хуйло",
    "huy": "хуй",
    "jopa": "жопа",
    "kladmen": "кладмен",
    "mefedron": "мефедрон",
    "mephedron": "мефедрон",
    "mephedrone": "мефедрон",
    "mudak": "мудак",
    "nahui": "нахуй",
    "nahuy": "нахуй",
    "pidor": "пидор",
    "pizd": "пизд",
    "pizda": "пизда",
    "pizdec": "пиздец",
    "pizdets": "пиздец",
    "prostitut": "проститут",
    "suka": "сука",
    "syka": "сука",
    "cyka": "сука",
    "xuy": "хуй",
    "xyi": "хуй",
    "yeban": "ебан",
    "yebat": "ебать",
    "zaklad": "заклад",
    "zakladka": "закладка",
    "zhopa": "жопа",
}

_COMPANY_BRAND_TERMS = frozenset(
    {
        "kfc",
        "mcdonald's",
        "mcdonalds",
        "mcdonald",
        "burger king",
        "starbucks",
        "subway",
        "domino's",
        "dominos",
    }
)

_LATIN_LETTERS = re.compile(r"[a-z]", re.IGNORECASE)
_CYRILLIC_LETTERS = re.compile(r"[а-яё]", re.IGNORECASE)

_WORD_BOUNDARY_BEFORE = r"(?<![a-zа-яё0-9])"
_WORD_BOUNDARY_AFTER = r"(?![a-zа-яё0-9])"

# Whole parenthetical groups; legitimacy is decided by inner content.
_PAREN_GROUP = re.compile(r"\(([^)]{3,})\)")

# Address-style abbreviations inside parentheses: (стр. 2), (корп. 3), (д. 5), (лит. А).
_ADDRESS_ABBREV = re.compile(
    r"^(стр|корп|д|лит|оф|кв|пом|подъезд)\.\s*\S",
    re.IGNORECASE,
)

# Token possibly containing obfuscation chars between letter runs.
_OBFUSCATED_TOKEN = re.compile(
    r"[a-zа-яё0-9]+(?:[\[\]{}.\-_|$@03!]*[a-zа-яё0-9@$03!]+)*",
    re.IGNORECASE,
)

_OBFUSCATION_BETWEEN_LETTERS = re.compile(
    r"(?<=[a-zа-я0-9])[\[\]{}]+(?=[a-zа-я0-9])|"
    r"(?<=[a-zа-я0-9])[.\-_|$]+(?=[a-zа-я0-9])"
)

# contact_info segmentation (Phase 9.4): skip wordlist on email / telegram only.
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_TELEGRAM_URL_RE = re.compile(
    r"(?:https?://)?t\.me/[a-zA-Z][a-zA-Z0-9_]{4,31}",
    re.IGNORECASE,
)
_TELEGRAM_HANDLE_RE = re.compile(r"@[a-zA-Z][a-zA-Z0-9_]{4,31}")
_PHONE_RE = re.compile(
    r"(?:\+7|8)(?:[\s\-().]*\d){10}"
    r"|(?:\+\d{1,3}[\s\-().]*)?\(?\d{2,4}\)?(?:[\s\-().]*\d){6,}",
)

ContactSegmentKind = Literal["email", "telegram", "phone", "text"]
_SKIP_WORDLIST_KINDS = frozenset({"email", "telegram"})


@dataclass(frozen=True, slots=True)
class ContactSegment:
    kind: ContactSegmentKind
    value: str


@dataclass(frozen=True, slots=True)
class ModerationViolation:
    field: str
    matched_term: str
    normalized_snippet: str
    raw_snippet: str
    category: str | None = None


class ContentRejectedError(Exception):
    def __init__(self, violation: ModerationViolation) -> None:
        self.violation = violation
        super().__init__(CONTENT_REJECTED_MESSAGE)


def _load_terms(filename: str) -> frozenset[str]:
    path = MODERATION_DIR / filename
    return frozenset(
        line.strip().lower().replace("ё", "е")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


@lru_cache(maxsize=1)
def _wordlists() -> tuple[frozenset[str], frozenset[str], frozenset[str], frozenset[str], frozenset[str]]:
    return (
        _load_terms("stop_words_profanity.txt"),
        _load_terms("stop_words_sex.txt"),
        _load_terms("stop_words_drugs.txt"),
        _load_terms("stop_words_translit.txt"),
        _load_terms("allow_words_alcohol.txt"),
    )


def _block_terms() -> frozenset[str]:
    profanity, sex, drugs, translit, _ = _wordlists()
    return profanity | sex | drugs | translit


def _alcohol_allow_terms() -> frozenset[str]:
    return _wordlists()[4]


@lru_cache(maxsize=1)
def _alcohol_allow_terms_by_length() -> tuple[str, ...]:
    """Longest alcohol phrases first so multi-word entries mask before single tokens."""
    return tuple(sorted(_alcohol_allow_terms(), key=len, reverse=True))


def _is_legitimate_paren_phrase(inner: str) -> bool:
    """True when parentheses wrap a whole phrase, not obfuscation inside one word."""
    stripped = inner.strip()
    if len(stripped) < 3:
        return False
    if re.search(r"\s", stripped):
        return True
    return _ADDRESS_ABBREV.match(stripped) is not None


def _mask_legitimate_parentheses(text: str) -> tuple[str, dict[str, str]]:
    """Replace legitimate parenthetical phrases with placeholders before token normalize."""
    placeholders: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        inner = match.group(1)
        if not _is_legitimate_paren_phrase(inner):
            return match.group(0)
        key = f"\x00LEG{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    return _PAREN_GROUP.sub(_replace, text), placeholders


def _deobfuscate_token(token: str) -> str:
    """Collapse obfuscation chars inside a single suspicious token."""
    lowered = token.lower().replace("ё", "е").translate(_LEET_TRANSLATION)
    lowered = re.sub(r"(?<=[a-zа-я0-9])[.\-_|$]+(?=[a-zа-я0-9])", "", lowered)
    lowered = re.sub(r"(?<=[a-zа-я0-9])[\[\]{}]+(?=[a-zа-я0-9])", "", lowered)
    return lowered


def _token_has_obfuscation_markers(token: str) -> bool:
    lowered = token.lower()
    return _OBFUSCATION_BETWEEN_LETTERS.search(lowered) is not None


def _deobfuscated_matches_block_term(token: str) -> bool:
    """True when brackets/separators split a known bad stem (e.g. зак[лад]ка)."""
    deobfuscated = _deobfuscate_token(token)
    if deobfuscated == token.lower().replace("ё", "е"):
        return False
    for term in _block_terms():
        if _is_allowed_alcohol_term(term):
            continue
        if term == deobfuscated or term in deobfuscated:
            return True
    return False


def _should_deobfuscate_token(token: str) -> bool:
    return _token_has_obfuscation_markers(token) or _deobfuscated_matches_block_term(token)


def _token_has_latin(token: str) -> bool:
    return _LATIN_LETTERS.search(token) is not None


def _token_has_cyrillic(token: str) -> bool:
    return _CYRILLIC_LETTERS.search(token) is not None


def _token_is_mixed_script(token: str) -> bool:
    return _token_has_latin(token) and _token_has_cyrillic(token)


def _latinize_for_translit_lookup(token: str) -> str:
    """Map homoglyphs / phonetics to latin ascii for translit dictionary lookup."""
    lowered = token.lower().replace("ё", "е")
    if _token_is_mixed_script(token):
        return lowered.translate(_CYRILLIC_PHONETIC_TO_LATIN)
    return lowered.translate(_CYRILLIC_TO_LATIN_HOMOGLYPH)


def _apply_translit_map(token: str) -> str:
    """Convert a latin / mixed-script token to canonical Cyrillic when recognized."""
    latin_form = _latinize_for_translit_lookup(token)
    if latin_form in _TRANSLIT_TO_CYRILLIC:
        return _TRANSLIT_TO_CYRILLIC[latin_form]

    converted = latin_form
    for key in sorted(_TRANSLIT_TO_CYRILLIC, key=len, reverse=True):
        if key in converted:
            converted = converted.replace(key, _TRANSLIT_TO_CYRILLIC[key])
    if converted != latin_form:
        return converted

    if _token_is_mixed_script(token):
        return token.translate(_HOMOGLYPH_LATIN_TO_CYRILLIC)
    return token.lower().replace("ё", "е")


def _should_normalize_translit_token(token: str) -> bool:
    if not _token_has_latin(token):
        return False
    if _token_is_mixed_script(token):
        return True
    latin_form = _latinize_for_translit_lookup(token)
    if latin_form in _TRANSLIT_TO_CYRILLIC:
        return True
    return any(key in latin_form for key in _TRANSLIT_TO_CYRILLIC)


def _normalize_translit_tokens(text: str) -> str:
    def _replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        if _should_normalize_translit_token(token):
            return _apply_translit_map(token)
        return token.lower().replace("ё", "е")

    return _OBFUSCATED_TOKEN.sub(_replace_token, text)


def _is_allowed_company_brand(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower().replace("ё", "е")).strip()
    normalized = normalized.replace("'", "'").replace("`", "'")
    if normalized in _COMPANY_BRAND_TERMS:
        return True
    return any(brand in normalized for brand in _COMPANY_BRAND_TERMS)


def _normalize_obfuscated_tokens(text: str) -> str:
    def _replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        if _should_deobfuscate_token(token):
            return _deobfuscate_token(token)
        return token.lower().replace("ё", "е")

    return _OBFUSCATED_TOKEN.sub(_replace_token, text)


def normalize_for_matching(text: str) -> str:
    """Normalize text for wordlist matching without altering stored user content."""
    normalized = text.lower().replace("ё", "е")
    masked, placeholders = _mask_legitimate_parentheses(normalized)
    if not placeholders:
        normalized = _normalize_obfuscated_tokens(masked)
    else:
        keys_pattern = "|".join(re.escape(key) for key in placeholders)
        segments = re.split(f"({keys_pattern})", masked)
        normalized = "".join(
            placeholders[segment]
            if segment in placeholders
            else _normalize_obfuscated_tokens(segment)
            for segment in segments
        )
    normalized = _normalize_translit_tokens(normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_allowed_alcohol_term(term: str) -> bool:
    return term in _alcohol_allow_terms()


def _mask_alcohol_terms(text: str) -> str:
    """Remove allowed alcohol phrases before block-term matching (Phase 9.5)."""
    masked = text
    for term in _alcohol_allow_terms_by_length():
        pattern = re.compile(
            _WORD_BOUNDARY_BEFORE + re.escape(term) + _WORD_BOUNDARY_AFTER,
            re.IGNORECASE,
        )
        masked = pattern.sub(" ", masked)
    masked = re.sub(r"\s+", " ", masked).strip()
    if not re.search(r"[a-zа-яё0-9]", masked, re.IGNORECASE):
        return ""
    return masked


def _span_overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < range_end and end > range_start for range_start, range_end in ranges)


def _phone_spans_in_text(text: str, blocked_ranges: list[tuple[int, int]]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _PHONE_RE.finditer(text):
        start, end = match.span()
        if _span_overlaps(start, end, blocked_ranges):
            continue
        spans.append((start, end, match.group(0)))
    return spans


def _gap_segments(gap: str, base_offset: int = 0) -> list[tuple[int, int, ContactSegmentKind, str]]:
    """Split non-email/telegram gap into phone and plain-text spans."""
    if not gap:
        return []

    phone_spans = _phone_spans_in_text(gap, [])
    if not phone_spans:
        stripped = gap.strip()
        if stripped:
            return [(base_offset, base_offset + len(gap), "text", gap)]
        return []

    segments: list[tuple[int, int, ContactSegmentKind, str]] = []
    cursor = 0
    for start, end, value in sorted(phone_spans, key=lambda item: item[0]):
        if start > cursor:
            text_value = gap[cursor:start]
            if text_value.strip():
                segments.append(
                    (base_offset + cursor, base_offset + start, "text", text_value)
                )
        segments.append((base_offset + start, base_offset + end, "phone", value))
        cursor = end

    if cursor < len(gap):
        text_value = gap[cursor:]
        if text_value.strip():
            segments.append((base_offset + cursor, base_offset + len(gap), "text", text_value))

    return segments


def parse_contact_info_segments(text: str) -> tuple[ContactSegment, ...]:
    """Split contact_info into email, telegram, phone, and free-text segments."""
    if not text.strip():
        return ()

    typed_spans: list[tuple[int, int, ContactSegmentKind, str]] = []
    email_ranges: list[tuple[int, int]] = []

    for match in _EMAIL_RE.finditer(text):
        start, end = match.span()
        typed_spans.append((start, end, "email", match.group(0)))
        email_ranges.append((start, end))

    for match in _TELEGRAM_URL_RE.finditer(text):
        start, end = match.span()
        if not _span_overlaps(start, end, email_ranges):
            typed_spans.append((start, end, "telegram", match.group(0)))

    telegram_ranges = [(start, end) for start, end, kind, _ in typed_spans if kind == "telegram"]
    blocked_for_handles = email_ranges + telegram_ranges
    for match in _TELEGRAM_HANDLE_RE.finditer(text):
        start, end = match.span()
        if not _span_overlaps(start, end, blocked_for_handles):
            typed_spans.append((start, end, "telegram", match.group(0)))

    typed_spans.sort(key=lambda item: (item[0], -(item[1] - item[0])))

    merged: list[tuple[int, int, ContactSegmentKind, str]] = []
    for span in typed_spans:
        start, end, kind, value = span
        if merged and start < merged[-1][1]:
            continue
        merged.append(span)

    segments: list[ContactSegment] = []
    cursor = 0
    for start, end, kind, value in merged:
        if start > cursor:
            for _, _, gap_kind, gap_value in _gap_segments(text[cursor:start], cursor):
                segments.append(ContactSegment(kind=gap_kind, value=gap_value))
        segments.append(ContactSegment(kind=kind, value=value))
        cursor = end

    if cursor < len(text):
        for _, _, gap_kind, gap_value in _gap_segments(text[cursor:], cursor):
            segments.append(ContactSegment(kind=gap_kind, value=gap_value))

    return tuple(segments)


def _check_contact_info(field: str, text: str) -> ModerationViolation | None:
    for segment in parse_contact_info_segments(text):
        if segment.kind in _SKIP_WORDLIST_KINDS:
            continue
        violation = _find_violation(segment.value, field)
        if violation is not None:
            return violation
    return None


def _category_for_term(term: str) -> str | None:
    profanity, sex, drugs, translit, _ = _wordlists()
    if term in sex:
        return "sex"
    if term in drugs:
        return "drugs"
    if term in translit:
        return "translit"
    if term in profanity:
        return "profanity"
    return None


def _find_violation(text: str, field: str) -> ModerationViolation | None:
    if not text.strip():
        return None

    normalized = normalize_for_matching(text)
    masked = _mask_alcohol_terms(normalized)
    if not masked:
        return None

    for term in sorted(_block_terms(), key=len, reverse=True):
        if _is_allowed_alcohol_term(term):
            continue
        pattern = re.compile(
            _WORD_BOUNDARY_BEFORE + re.escape(term) + _WORD_BOUNDARY_AFTER,
            re.IGNORECASE,
        )
        if pattern.search(masked):
            return ModerationViolation(
                field=field,
                matched_term=term,
                normalized_snippet=normalized[:200],
                raw_snippet=text[:500],
                category=_category_for_term(term),
            )
    return None


def check_text(field: str, text: str | None) -> ModerationViolation | None:
    if text is None:
        return None
    if field == "company_name" and _is_allowed_company_brand(text):
        return None
    if field == "contact_info":
        return _check_contact_info(field, text)
    return _find_violation(text, field)


def check_fields(fields: dict[str, str | None]) -> ModerationViolation | None:
    for field, value in fields.items():
        violation = check_text(field, value)
        if violation is not None:
            return violation
    return None


def require_clean_fields(fields: dict[str, str | None]) -> None:
    violation = check_fields(fields)
    if violation is not None:
        raise ContentRejectedError(violation)


def moderate_job_for_publish(
    *,
    title: str,
    description: str,
    address: str | None = None,
    dress_code: str | None = None,
    contact_info: str | None = None,
) -> None:
    require_clean_fields(
        {
            "title": title,
            "description": description,
            "address": address,
            "dress_code": dress_code,
            "contact_info": contact_info,
        }
    )


def moderate_company_name(company_name: str) -> None:
    require_clean_fields({"company_name": company_name})


def moderate_worker_experience(role_title: str, description: str | None = None) -> None:
    require_clean_fields({"role_title": role_title, "description": description})
