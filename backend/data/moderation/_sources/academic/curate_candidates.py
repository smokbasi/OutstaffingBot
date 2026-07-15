#!/usr/bin/env python3
"""Curate academic extraction candidates into merge-ready manifests.

Usage (from repo root or this directory):
    python backend/data/moderation/_sources/academic/curate_candidates.py

Reads ``extracted/`` candidate files, applies FP-safe filters, writes ``curated/`` manifests
and ``curation_stats.json``. Live wordlists are updated via ``build_wordlists.py``.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EXTRACTED_DIR = BASE_DIR / "extracted"
CURATED_DIR = BASE_DIR / "curated"
MOD_DIR = BASE_DIR.parent.parent

_BW_PATH = MOD_DIR / "build_wordlists.py"
_EXT_PATH = BASE_DIR / "extract_terms.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_bw = _load_module("build_wordlists", _BW_PATH)
_ext = _load_module("academic_extract_terms", _EXT_PATH)

norm = _bw.norm
is_valid_term = _bw.is_valid_term
is_excluded = _bw.is_excluded
matches_stem = _bw.matches_stem
classify = _bw.classify
DRUG_STEMS = _bw.DRUG_STEMS
SEX_STEMS = _bw.SEX_STEMS
PROFANITY_STEMS = _bw.PROFANITY_STEMS
EXCLUDE_FALSE_POSITIVES = _bw.EXCLUDE_FALSE_POSITIVES
GLOBAL_EXCLUDE = _bw.GLOBAL_EXCLUDE
ACADEMIC_JARGON = _ext.ACADEMIC_JARGON
CONTEXT_REQUIRED_REASONS = _ext.CONTEXT_REQUIRED_REASONS
KNOWN_SEX_PHRASES = _ext.KNOWN_SEX_PHRASES
is_context_required = _ext.is_context_required
is_valid_phrase = _ext.is_valid_phrase
load_existing_wordlists = _ext.load_existing_wordlists

OCR_MOJIBAKE_RE = re.compile(r"[\u0452\u0453\u0491]|г[\u0452\u0453]")
CYRILLIC_HEADWORD_RE = re.compile(r"[а-яё]", re.IGNORECASE)
INFLECTED_VERB_RE = re.compile(
    r"(?:ться|ться|ть|лся|лась|лись|ешь|ишь|ете|ите|ют|ут|ат|ят|ит|ет|"
    r"ать|ять|ить|ывать|ивать|овать|евать|нуть|нуться)$"
)
LATIN_TOKEN_RE = re.compile(r"^[a-z][a-z0-9\-]{2,}$")

# Everyday / job-ad homonyms from academic drug dictionaries (not EXCLUDE_FALSE_POSITIVES yet).
COMMON_HOMONYMS = frozenset(
    norm(x)
    for x in [
        "дом",
        "девушка",
        "аптекарь",
        "аристократ",
        "ан",
        "баллон",
        "баня",
        "беда",
        "бокс",
        "болт",
        "большой",
        "ботаник",
        "белка",
        "банкир",
        "банка",
        "атом",
        "аут",
        "башня",
        "баян",
        "бинт",
        "близнецы",
        "блюдце",
        "боковушка",
        "бомба",
        "борода",
        "бегунок",
        "белые",
        "бен",
        "благородный",
        "блестящие",
        "булавка",
        "вагон",
        "вата",
        "весы",
        "витрина",
        "вода",
        "волна",
        "гитара",
        "глаз",
        "голова",
        "город",
        "гость",
        "гроза",
        "грудь",
        "веревка",
        "вешалка",
        "винтик",
        "волшебник",
        "выборка",
        "выручка",
        "галька",
        "калика",
        "книжка",
        "кобыла",
        "компот",
        "корова",
        "кот",
        "кошка",
        "краска",
        "кресло",
        "кукла",
        "лампа",
        "ложка",
        "машина",
        "медведь",
        "молоток",
        "мост",
        "мышь",
        "нож",
        "огонь",
        "окно",
        "палка",
        "печь",
        "пила",
        "герой",
        "герман",
        "герасим",
        "главный",
        "дура",
        "гербалайф",
        "гердос",
        # wiki/academic homonyms — user curation 2026-07-09
        "абрикос", "аленка", "антенна", "аппаратура", "барсик", "баянист", "боец",
        "булик", "бублики", "бумага", "бутылка", "валек", "варить", "весло", "виталя",
        "витек", "вулкан", "выкупить", "галя", "гараж", "гвоздь", "гильза", "гонец",
        "гонки", "грязь", "гусь", "дед", "дизель", "дима", "дома", "дрова", "зима",
        "знахарь", "камень", "инструмент", "качели", "каша", "кнопка", "ковбой",
        "коделак", "колодец", "колючий", "колючка", "контроль", "конфета", "космонавт",
        "котелок", "красный", "кратер", "крыса", "купец", "ликвид", "медицина", "метла",
        "метро", "москва", "мокрый", "мягкий", "напарить", "настя", "оксана", "парашют",
        "подзаборка", "покрышка", "свин", "свинак", "федя", "фрукт", "часики", "часы",
        "чек", "шланг",
    ]
)

# Marker hits that are still homonyms in outstaffing context.
MARKER_FALSE_POSITIVES = frozenset(
    norm(x)
    for x in [
        "герой",
        "герман",
        "герасим",
        "главный",
        "дура",
        "гербалайф",
        "гердос",
        "автопилот",
        "колеса",
        "колесить",
        "кайф",
        "прокладка",
        "лекарство",
        "импорт",
        "папа",
        "медленный",
        "убойный",
        "дутый",
        "гера",
        "гертруда",
        "гирик",
        "цветочки",
        "витамин",
        "витамины",
    ]
)

# Unambiguous narcotics headword substrings (russki-mat / abannet jargon).
DRUG_SLANG_MARKERS = (
    "абст",
    "гаш",
    "геро",
    "геры",
    "гир",
    "гер",
    "нарк",
    "торч",
    "заклад",
    "клад",
    "спайс",
    "меф",
    "кока",
    "кокс",
    "кокн",
    "анаш",
    "опи",
    "опий",
    "шир",
    "кося",
    "бошк",
    "бош",
    "доз",
    "барыг",
    "шприц",
    "шпан",
    "шмал",
    "гандж",
    "коноп",
    "марих",
    "марух",
    "психостим",
    "первит",
    "эфед",
    "дезоморф",
    "крокод",
    "кетам",
    "фентан",
    "мухомор",
    "амфет",
    "метамф",
    "экстаз",
    "лсд",
    "мдма",
    "морфин",
    "кодеин",
    "трамад",
    "каннаб",
    "глюк",
    "шквар",
    "шпиг",
    "пыр",
    "пых",
    "колот",
    "колес",
    "приход",
    "пробив",
    "прогон",
    "забит",
    "закин",
    "вмаз",
    "втер",
    "дупл",
    "драг",
    "драч",
    "жарех",
    "бодяж",
    "битурат",
    "барбит",
    "нембут",
    "пентобар",
    "феназ",
    "фенил",
    "феноз",
    "турьяк",
    "ханк",
    "чернух",
    "черняш",
    "шняг",
    "опиух",
    "папавер",
    "конар",
    "кокнар",
    "маняг",
    "марц",
    "табак",
    "травк",
    "шиш",
    "закладоч",
    "кладмен",
    "пушер",
    "легалк",
    "нарком",
    "наркош",
    "дозняк",
    "кайф",
    "афган",
    "бензол",
    "ацетон",
    "ампул",
    "инсулинк",
    "канаб",
    "ким-хан",
    "гепарин",
    "бутал",
    "субут",
    "оксик",
    "габап",
    "димедр",
    "доксил",
    "паксил",
    "золофт",
    "трамб",
    "каркен",
    "канонфар",
    "словак",
    "вилар",
    "валокор",
    "адаптол",
    "азафен",
    "аминаз",
    "амитрипт",
    "атарак",
    "беллатам",
    "вмазк",
    "гаидт",
    "глатк",
    "глипт",
    "глотар",
    "дербан",
    "диклоф",
    "доебени",
    "кедрен",
    "колесник",
    "колесман",
    "коксик",
    "нарков",
    "торчок",
    "торчал",
    "абшаб",
    "анашист",
    "анашхор",
    "багрить",
    "барбад",
    "безмаз",
    "бодяжн",
    "внутрян",
    "депресняк",
    "дискотух",
    "эйч",
    "эфедрин",
)

KNOWN_SHORT_DRUG_SLANG = frozenset(norm(x) for x in ("айс", "кет", "бз", "гаш"))

# User override: blind block (not context_required proximity) for unambiguous slang.
FORCE_BLOCK_DRUGS = frozenset(norm(x) for x in ("герыч", "балдеть", "кокос", "косой", "шишки"))

# Abannet/russki_mat headword morphology — relaxed gate after strict reject_* filters.
DRUG_HEADWORD_SUFFIXES = (
    "няк", "няка", "ешник", "ешница", "овка", "ушка", "юха", "юшка",
    "алово", "оген", "алка", "атка", "ишка", "ашен", "башен",
)
DRUG_HEADWORD_PREFIXES = (
    "аб", "нар", "тор", "зак", "клад", "мар", "гаш", "меф", "нарк", "балд",
    "торч", "шпан", "шмал", "амф", "опи", "кок", "геро", "спайс", "перв",
    "эфед", "дур", "шир", "кося", "бош", "глюк", "псих", "стим", "нарко",
)

FULL_JARGON_DRUGS = frozenset(
    term for term, cat in ACADEMIC_JARGON.items() if cat == "drugs"
)

JARGON_DRUGS = frozenset(
    term
    for term, cat in ACADEMIC_JARGON.items()
    if cat == "drugs" and term not in CONTEXT_REQUIRED_REASONS
)

JARGON_SEX = frozenset(
    term for term, cat in ACADEMIC_JARGON.items() if cat == "sex" and term not in CONTEXT_REQUIRED_REASONS
)

# Phrases to drop: OCR/prose fragments, typos, ambiguous or inflected duplicates.
PHRASE_DROP = frozenset(
    norm(x)
    for x in [
        "самодельных психостимуляторов",
        "интим услуг",
        "большая дурь",
        "честных куртизанок",
        "косяка прогонять",
        "забить гвоздь",
        "черный русский",
    ]
)

# Conservative translit from Shlyakhov abbreviations / obfuscation forms.
CURATED_SEX_EXTRA = frozenset(norm(x) for x in ("дивайн", "подстилка"))

CURATED_TRANSLIT_ALLOW = frozenset(
    norm(x)
    for x in [
        "pornh",
        "fak",
        "ped",
        "bzdun",
        "torc",
        "strejt",
        "fen",
        "jwh",
        "jwh-018",
    ]
)

TRANSLIT_DROP = frozenset(
    norm(x)
    for x in [
        "bir",
        "cath",
        "cith",
        "deth",
        "durh",
        "gej",
        "kef",
        "kot",
        "krab",
        "list",
        "lith",
        "masth",
        "mers",
        "nedo-",
        "net",
        "nith",
        "palh",
        "rov",
        "tarc",
        "task",
        "vduth",
        "vhet",
        "vint",
    ]
)

MAX_DRUG_ADDITIONS = 400


@dataclass
class CurationStats:
    rejected: Counter[str] = field(default_factory=Counter)
    accepted: Counter[str] = field(default_factory=Counter)


def parse_token_sections(path: Path) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    category: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# "):
            category = line[2:].strip()
            buckets.setdefault(category, [])
            continue
        if line.strip() and category:
            buckets[category].append(norm(line))
    return buckets


def load_manifest_terms(name: str) -> set[str]:
    path = CURATED_DIR / name
    if not path.exists():
        return set()
    return {
        norm(line.split("#", 1)[0].strip())
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    }


def _homonym_set() -> frozenset[str]:
    return COMMON_HOMONYMS | frozenset(CONTEXT_REQUIRED_REASONS) | EXCLUDE_FALSE_POSITIVES


def reject_drug_token(term: str, *, existing: frozenset[str]) -> str | None:
    """Return rejection reason or None when term should be accepted."""
    t = norm(term)
    if t in FORCE_BLOCK_DRUGS:
        if not is_valid_term(t):
            return "invalid"
        if t in existing:
            return "existing"
        if is_excluded(t):
            return "excluded"
        if OCR_MOJIBAKE_RE.search(t):
            return "ocr_mojibake"
        return None
    if not is_valid_term(t):
        return "invalid"
    if t in existing:
        return "existing"
    if is_excluded(t):
        return "excluded"
    if is_context_required(t):
        return "context_required"
    if OCR_MOJIBAKE_RE.search(t):
        return "ocr_mojibake"
    if len(t) < 3 and t not in KNOWN_SHORT_DRUG_SLANG:
        return "too_short"
    if t in _homonym_set() or t in MARKER_FALSE_POSITIVES:
        return "homonym"
    if INFLECTED_VERB_RE.search(t):
        return "inflected_verb"
    return None


def accept_extracted_drug_headword(term: str) -> bool:
    """Relaxed accept for abannet/russki_mat headwords that passed reject_* filters.

    Prior ``no_stem_or_marker`` gate required DRUG_STEMS/marker substring on every token;
    abannet comma-lists add hundreds of 5–12 char slang headwords without stem hits.
    Still rejects via reject_drug_token: OCR, inflected verbs, homonyms, context_required.
    """
    t = norm(term)
    if t in _homonym_set() or t in MARKER_FALSE_POSITIVES:
        return False
    if t in FULL_JARGON_DRUGS:
        return True
    if len(t) < 5 or len(t) > 35:
        return False
    if not CYRILLIC_HEADWORD_RE.search(t):
        return t in {"coconut"}
    if INFLECTED_VERB_RE.search(t):
        return False
    if any(t.endswith(suffix) for suffix in DRUG_HEADWORD_SUFFIXES):
        return True
    if any(t.startswith(prefix) for prefix in DRUG_HEADWORD_PREFIXES):
        return True
    if len(t) >= 4 and any(marker in t for marker in DRUG_SLANG_MARKERS):
        return True
    # Residual abannet headwords: 6+ chars, already in drugs candidate bucket
    return len(t) >= 6


def accept_drug_token(term: str) -> bool:
    t = norm(term)
    if t in FORCE_BLOCK_DRUGS:
        return True
    if matches_stem(t, DRUG_STEMS) or t in JARGON_DRUGS:
        return True
    if t in KNOWN_SHORT_DRUG_SLANG:
        return True
    if len(t) >= 4 and any(marker in t for marker in DRUG_SLANG_MARKERS):
        return True
    return accept_extracted_drug_headword(t)


def curate_drug_tokens(candidates: list[str], existing: frozenset[str], stats: CurationStats) -> list[str]:
    pool = list(
        dict.fromkeys(
            [
                *sorted(FORCE_BLOCK_DRUGS),
                *candidates,
                *sorted(load_manifest_terms("curated_drugs.txt")),
            ]
        )
    )
    accepted: list[str] = []
    for term in pool:
        if len(accepted) >= MAX_DRUG_ADDITIONS:
            stats.rejected["cap_reached"] += 1
            continue
        reason = reject_drug_token(term, existing=existing)
        if reason:
            stats.rejected[reason] += 1
            continue
        if not accept_drug_token(term):
            stats.rejected["no_stem_or_marker"] += 1
            continue
        if norm(term) not in accepted:
            accepted.append(norm(term))
            stats.accepted["drugs"] += 1
    return sorted(set(accepted))


def curate_sex_tokens(candidates: list[str], existing: frozenset[str], stats: CurationStats) -> list[str]:
    pool = list(
        dict.fromkeys(
            [
                *candidates,
                *sorted(
                    t
                    for t in (JARGON_SEX | CURATED_SEX_EXTRA | load_manifest_terms("curated_sex.txt"))
                    if " " not in t
                ),
            ]
        )
    )
    accepted: list[str] = []
    for term in pool:
        t = norm(term)
        if " " in t:
            stats.rejected["sex_phrase_routed"] += 1
            continue
        if not is_valid_term(t) or t in existing or is_excluded(t) or is_context_required(t):
            stats.rejected["sex_skip"] += 1
            continue
        if classify(t) != "sex" and t not in JARGON_SEX and t not in CURATED_SEX_EXTRA:
            stats.rejected["sex_not_classified"] += 1
            continue
        accepted.append(t)
        stats.accepted["sex"] += 1
    return sorted(set(accepted))


def reject_phrase(phrase: str) -> str | None:
    t = norm(phrase)
    if t in PHRASE_DROP:
        return "garbage_or_ambiguous"
    if not is_valid_phrase(t):
        return "invalid_phrase"
    if t in KNOWN_SEX_PHRASES or matches_stem(t, SEX_STEMS | DRUG_STEMS):
        return None
    return "no_category_match"


def curate_phrases(candidates: list[str], existing: frozenset[str], stats: CurationStats) -> list[str]:
    pinned = {p for p in KNOWN_SEX_PHRASES if reject_phrase(p) is None}
    pool = list(dict.fromkeys([*candidates, *sorted(pinned | load_manifest_terms("curated_phrases.txt"))]))
    accepted: list[str] = []
    for phrase in pool:
        t = norm(phrase)
        if t in existing:
            stats.rejected["phrase_existing"] += 1
            continue
        reason = reject_phrase(t)
        if reason:
            stats.rejected[reason] += 1
            continue
        accepted.append(t)
        stats.accepted["phrases"] += 1
    return sorted(set(accepted))


def curate_translit_tokens(candidates: list[str], existing: frozenset[str], stats: CurationStats) -> list[str]:
    pool = list(
        dict.fromkeys(
            [
                *candidates,
                *sorted(CURATED_TRANSLIT_ALLOW | load_manifest_terms("curated_translit.txt")),
            ]
        )
    )
    accepted: list[str] = []
    for term in pool:
        t = norm(term)
        if not LATIN_TOKEN_RE.match(t) or t in TRANSLIT_DROP:
            stats.rejected["translit_drop"] += 1
            continue
        if t in existing:
            stats.rejected["translit_existing"] += 1
            continue
        if t in CURATED_TRANSLIT_ALLOW or classify(t) == "translit":
            accepted.append(t)
            stats.accepted["translit"] += 1
            continue
        if matches_stem(t, DRUG_STEMS | SEX_STEMS | PROFANITY_STEMS):
            accepted.append(t)
            stats.accepted["translit"] += 1
            continue
        stats.rejected["translit_unclassified"] += 1
    return sorted(set(accepted))


def write_lines(path: Path, terms: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(terms) + ("\n" if terms else ""), encoding="utf-8")
    return len(terms)


def write_context_file(path: Path, context: dict[str, str]) -> int:
    lines = [f"{term}  # {reason}" for term, reason in sorted(context.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def load_baseline_existing() -> frozenset[str]:
    """Existing live terms minus prior curated manifests (idempotent re-runs)."""
    existing = set(load_existing_wordlists())
    for manifest in (
        "curated_drugs.txt",
        "curated_sex.txt",
        "curated_phrases.txt",
        "curated_translit.txt",
    ):
        path = CURATED_DIR / manifest
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            existing.discard(norm(line.split("#", 1)[0].strip()))
    return frozenset(existing)


def load_context_required_candidates() -> dict[str, str]:
    path = EXTRACTED_DIR / "candidates_context_required.txt"
    context: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        term_part, _, comment = line.partition("#")
        term = norm(term_part.strip())
        if term:
            context[term] = comment.strip() or CONTEXT_REQUIRED_REASONS.get(term, "ambiguous homonym")
    return context


def main() -> int:
    tokens_path = EXTRACTED_DIR / "candidates_tokens.txt"
    phrases_path = EXTRACTED_DIR / "candidates_phrases.txt"
    if not tokens_path.exists() or not phrases_path.exists():
        print("Run extract_terms.py first.", file=sys.stderr)
        return 1

    existing = load_baseline_existing()
    stats = CurationStats()
    sections = parse_token_sections(tokens_path)

    curated_drugs = curate_drug_tokens(sections.get("drugs", []), existing, stats)
    curated_sex = curate_sex_tokens(sections.get("sex", []), existing, stats)
    curated_translit = curate_translit_tokens(sections.get("translit", []), existing, stats)

    phrase_candidates = [
        norm(line)
        for line in phrases_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    curated_phrases = curate_phrases(phrase_candidates, existing, stats)

    context_required = load_context_required_candidates()

    counts = {
        "curated_drugs.txt": write_lines(CURATED_DIR / "curated_drugs.txt", curated_drugs),
        "curated_sex.txt": write_lines(CURATED_DIR / "curated_sex.txt", curated_sex),
        "curated_phrases.txt": write_lines(CURATED_DIR / "curated_phrases.txt", curated_phrases),
        "curated_translit.txt": write_lines(CURATED_DIR / "curated_translit.txt", curated_translit),
    }

    stable_context_path = MOD_DIR / "context_required.txt"
    counts["context_required.txt"] = write_context_file(stable_context_path, context_required)
    counts["curated_context_required.txt"] = write_context_file(
        CURATED_DIR / "curated_context_required.txt", context_required
    )

    before_sizes = {
        name: sum(
            1
            for line in (MOD_DIR / name).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        )
        for name in (
            "stop_words_drugs.txt",
            "stop_words_sex.txt",
            "stop_words_translit.txt",
            "stop_words_slang_manual.txt",
        )
    }

    curation_stats = {
        "before_wordlist_sizes": before_sizes,
        "accepted": dict(stats.accepted),
        "rejected": dict(stats.rejected.most_common()),
        "rejected_totals_by_reason": dict(stats.rejected),
        "curated_counts": counts,
        "candidate_totals": {
            "drugs": len(sections.get("drugs", [])),
            "sex": len(sections.get("sex", [])),
            "translit": len(sections.get("translit", [])),
            "phrases": len(phrase_candidates),
            "context_required": len(context_required),
        },
    }
    stats_path = CURATED_DIR / "curation_stats.json"
    stats_path.write_text(json.dumps(curation_stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(curation_stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
