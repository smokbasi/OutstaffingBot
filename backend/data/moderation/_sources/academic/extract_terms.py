#!/usr/bin/env python3
"""Extract moderation term candidates from academic txt sources.

Usage (from repo root or this directory):
    python backend/data/moderation/_sources/academic/extract_terms.py

Outputs land in ``extracted/`` next to this script.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TXT_DIR = BASE_DIR / "txt"
OUT_DIR = BASE_DIR / "extracted"
MOD_DIR = BASE_DIR.parent.parent

# Load build_wordlists helpers without package import path hacks
_BW_PATH = MOD_DIR / "build_wordlists.py"
_spec = importlib.util.spec_from_file_location("build_wordlists", _BW_PATH)
assert _spec and _spec.loader
_bw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bw)

classify = _bw.classify
norm = _bw.norm
is_valid_term = _bw.is_valid_term
is_excluded = _bw.is_excluded
matches_stem = _bw.matches_stem
DRUG_STEMS = _bw.DRUG_STEMS
SEX_STEMS = _bw.SEX_STEMS
PROFANITY_STEMS = _bw.PROFANITY_STEMS
EXCLUDE_FALSE_POSITIVES = _bw.EXCLUDE_FALSE_POSITIVES
GLOBAL_EXCLUDE = _bw.GLOBAL_EXCLUDE

WORDLIST_FILES = (
    "stop_words_profanity.txt",
    "stop_words_sex.txt",
    "stop_words_drugs.txt",
    "stop_words_translit.txt",
    "stop_words_slang_manual.txt",
)

CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
LATIN_TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]{2,}", re.IGNORECASE)
CYR_TOKEN_RE = re.compile(r"[а-яё][а-яё\-]{1,}", re.IGNORECASE)
CYR_PHRASE_RE = re.compile(
    r"[а-яё][а-яё0-9\-]{1,}(?:\s+[а-яё0-9][а-яё0-9\-]{1,}){1,7}",
    re.IGNORECASE,
)

# Dictionary entry: headword —/-/: definition
DICT_ENTRY_RE = re.compile(
    r"^([A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9\s,\-()/]{0,78}?)\s*"
    r"(?:—|–|-(?=\s)|:)\s*(.+)$"
)

# researchgate / dembska phrase markers
PHRASEOLOGISM_RE = re.compile(
    r"фразеологизм(?:ом)?\s+([«\"]?[а-яё][^»\";\n]{2,60}[»\"]?)",
    re.IGNORECASE,
)
QUOTED_RU_PHRASE_RE = re.compile(r"[«\"]([а-яё][^»\"]{2,60})[»\"]", re.IGNORECASE)
IN_VALUE_RE = re.compile(
    r"(?:в\s+знач\.|знач\.\s*|в\s+значении)\s*[«\"]?([^»\";\n]{2,60})",
    re.IGNORECASE,
)

SHLYAKHOV_DRUG_SEX_MARKERS = re.compile(
    r"\b(?:drug|drugs|narcotic|heroin|cocaine|marijuana|cannabis|"
    r"prostitut|whore|whorehouse|brothel|pimp|narcotics|morphine|"
    r"amphetamine|LSD|MDMA|narcotic)\b",
    re.IGNORECASE,
)

HF_SEX_PHRASE_SEEDS = (
    "ночн",
    "проститут",
    "шлюх",
    "эскорт",
    "куртизан",
    "интим",
    "бордел",
    "пимп",
    "vip девуш",
    "массаж",
    "красн",
    "фонар",
    "легк",
    "кавалер",
    "жриц",
    "любви",
    "публичн",
    "содержан",
)

# Section hints from abannet / russki-mat headings → category override
SECTION_CATEGORY_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"героин", re.I), "drugs"),
    (re.compile(r"марихуан|коноп|анаш", re.I), "drugs"),
    (re.compile(r"кокаин|крэк|крек", re.I), "drugs"),
    (re.compile(r"опi?й|маков|сырца", re.I), "drugs"),
    (re.compile(r"таблет", re.I), "drugs"),
    (re.compile(r"шприц|инъекц|игл", re.I), "drugs"),
    (re.compile(r"психостимул|первитин|эфедрон", re.I), "drugs"),
    (re.compile(r"общие\s+слова|наркотическ", re.I), "drugs"),
    (re.compile(r"проститут|эвфем|фразеолог", re.I), "sex"),
)

# Dembska UMK footnotes: домохозяйка6 - żartobliwie o prostytutce...
UMK_FOOTNOTE_HEADWORD_RE = re.compile(
    r"(?:^|[\s\n])([а-яё][а-яё\-]{2,})(\d+)\s*(?:\([^)]{0,120}\))?\s*-\s*",
    re.IGNORECASE | re.MULTILINE,
)
UMK_PROSTITUTION_GLOSS_MARKERS = (
    "prostytut",
    "lekkich obyczaj",
    "prostytucj",
    "seksie oralnym",
    "kobiecie lekkich",
    "o prostytutce",
)

# Homonym prostitution euphemisms — route to context_required, not bare block
SEX_CONTEXT_HOMONYMS = frozenset(
    norm(x)
    for x in [
        "домохозяйка", "грелка", "мочалка", "липучка", "кожа", "тётка",
    ]
)

# Known jargon from academic drug lists (classify even when stems miss)
ACADEMIC_JARGON: dict[str, str] = {
    norm(x): cat
    for x, cat in [
        ("кекс", "drugs"), ("снег", "drugs"), ("снежок", "drugs"), ("герыч", "drugs"),
        ("гера", "drugs"), ("гертруда", "drugs"), ("гирик", "drugs"), ("мука", "drugs"),
        ("кокос", "drugs"), ("кокс", "drugs"), ("кэг", "drugs"),
        ("лошадь", "drugs"), ("перец", "drugs"), ("энергия", "drugs"),
        ("белый", "drugs"), ("черный", "drugs"), ("светлый", "drugs"), ("скучный", "drugs"),
        ("грустный", "drugs"), ("хлеб", "drugs"), ("молоко", "drugs"), ("пластилин", "drugs"),
        ("табакерка", "drugs"), ("шала", "drugs"), ("шан", "drugs"), ("марго", "drugs"),
        ("маруся", "drugs"), ("маруха", "drugs"), ("маняга", "drugs"), ("драч", "drugs"),
        ("жареха", "drugs"), ("бошки", "drugs"), ("гандж", "drugs"),
        ("гарик", "drugs"), ("дурь", "drugs"), ("дым", "drugs"), ("трава", "drugs"),
        ("травка", "drugs"), ("шишки", "drugs"), ("шмаль", "drugs"), ("план", "drugs"),
        ("пласт", "drugs"), ("косой", "drugs"), ("дутый", "drugs"), ("сырой", "drugs"),
        ("свежий", "drugs"), ("ускоритель", "drugs"), ("кикер", "drugs"), ("нос", "drugs"),
        ("эйч", "drugs"), ("ковырялка", "drugs"), ("мультяшка", "drugs"),
        ("султан", "drugs"), ("убойный", "drugs"), ("медленный", "drugs"), ("главный", "drugs"),
        ("большой", "drugs"), ("большая дурь", "drugs"), ("лекарство", "drugs"),
        ("жмых", "drugs"), ("кокнар", "drugs"), ("конар", "drugs"),
        ("мача", "drugs"), ("мачье", "drugs"), ("опиуха", "drugs"),
        ("папа", "drugs"), ("папавер", "drugs"), ("турьяк", "drugs"), ("ханка", "drugs"),
        ("чернуха", "drugs"), ("черняшка", "drugs"), ("шняга", "drugs"),
        ("колеса", "drugs"), ("колесить", "drugs"), ("танцульки", "drugs"), ("тарелки", "drugs"),
        ("цветочки", "drugs"), ("экстаз", "drugs"), ("импорт", "drugs"),
        ("абстяга", "drugs"), ("абстяг", "drugs"), ("абстяк", "drugs"),
        ("абшабашенный", "drugs"), ("абшабиваться", "drugs"), ("айс", "drugs"),
        ("анашист", "drugs"), ("анашхор", "drugs"),
        ("апер", "drugs"), ("апиын", "drugs"), ("антрацит", "drugs"), ("афганка", "drugs"),
        ("багрить", "drugs"), ("барбадос", "drugs"),
        ("ночная бабочка", "sex"), ("ночные бабочки", "sex"),
        ("жрица любви", "sex"), ("жрицы любви", "sex"),
        ("честная куртизанка", "sex"), ("легкая кавалерия", "sex"),
        ("красный фонарь", "sex"), ("дом под красным фонарем", "sex"),
        ("дама из амстердама", "sex"), ("легкая жизнь", "sex"),
        ("прокурсетка", "sex"), ("институтка", "sex"), ("легкотрудница", "sex"),
        ("тутка", "sex"), ("чеханка", "sex"), ("фрилавка", "sex"), ("подстилка", "sex"),
        ("сверхурочница", "sex"), ("цырва", "sex"),
        ("заправить трубу", "drugs"), ("зеленая наркота", "drugs"),
    ]
}

PHRASE_STOPWORDS = frozenset(
    norm(x)
    for x in [
        "без", "для", "которого", "которой", "которые", "который", "может", "быть",
        "или", "врач", "и", "на", "не", "их", "в", "по", "из", "от", "до", "как",
        "качестве", "используемый", "используемая", "употребляемый", "употребляемая",
        "употребляют", "относится", "меняющий", "вытаращенные", "действия", "опьянения",
        "назвать", "называют", "самодельные", "психостимуляторы", "таблетки",
    ]
)

PHRASE_FRAGMENT_START = re.compile(
    r"^(?:обознач|бывает|после|перед|что|кто|если|когда|немного|"
    r"параллельно|исто|мысл|действ|вызыва|пренеб|«|')"
)

KNOWN_SEX_PHRASES = frozenset(
    norm(x)
    for x in [
        "жрица любви", "жрицы любви", "жрица наемной любви",
        "жрица продажной любви", "жрица придорожной любви",
        "честная куртизанка", "легкая кавалерия", "ночная бабочка",
        "ночные бабочки", "красный фонарь", "дом под красным фонарем",
        "дама из амстердама", "продажная любовь", "наемная любовь",
        "легкие нравы", "девушки любви", "дома любви", "продавщицы любви",
        "красная вечеринка", "кормиться за счет своей груди",
        "заниматься проституцией", "vip девушки", "интим услуги",
        "массаж 18", "эскорт услуги", "happy ending",
    ]
)

# Ambiguous tokens — exact block alone causes FP in job ads
CONTEXT_REQUIRED_REASONS: dict[str, str] = {
    norm(x): reason
    for x, reason in [
        ("кекс", "кокаин jargon vs bakery"),
        ("ляля", "drug/sex slang vs name"),
        ("лялька", "drug slang vs diminutive name"),
        ("ласточка", "drug slang vs bird/name"),
        ("снег", "кокаин jargon vs weather"),
        ("снежок", "экстази brand vs weather"),
        ("лед", "meth jargon vs ice/water"),
        ("белый", "heroin color vs neutral adjective"),
        ("мука", "cocaine jargon vs baking"),
        ("сахар", "drug diluent vs food"),
        ("кокс", "cocaine vs coke fuel/metallurgy"),
        ("план", "marijuana vs schedule/plan"),
        ("кристалл", "meth vs neutral noun"),
        ("кристалы", "meth plural vs neutral"),
        ("крис", "crystal meth vs name"),
        ("крисы", "crystal meth plural"),
        ("доза", "drug dose vs medical/business"),
        ("агрегат", "syringe jargon vs equipment"),
        ("болтанка", "drug prep vs machinery"),
        ("болтушка", "drug prep vs medicine"),
        ("варево", "drug brew vs food"),
        ("канюля", "needle vs medical device"),
        ("карбид", "low-grade drug vs chemistry"),
        ("кикер", "cocaine vs furniture/sport"),
        ("кумар", "withdrawal vs surname"),
        ("натур", "drug quality vs nature"),
        ("оттянуться", "get high vs relax"),
        ("пинки", "drug hits vs kicks"),
        ("пласт", "hash slab vs material"),
        ("подзаправиться", "use drugs vs refuel"),
        ("расколбаситься", "get high vs colloquial"),
        ("стимульнуться", "stimulant vs generic"),
        ("треснуться", "OD slang vs crack"),
        ("ужалиться", "inject vs sting"),
        ("ускоритель", "cocaine vs accelerator"),
        ("мача", "opium raw vs matcha"),
        ("мулька", "low-grade drug vs generic"),
        ("шала", "marijuana vs name"),
        ("жмых", "opium residue vs food"),
        ("брахман", "drug vs caste"),
        ("гарик", "marijuana vs name"),
        ("марго", "marijuana vs name"),
        ("вторяк", "spent raw material vs second-hand"),
        ("духарь", "drug user vs generic"),
        ("калики", "pills vs name"),
        ("килики", "pills vs name"),
        ("миксы", "drug mix vs audio/food"),
        ("торты", "drug shapes vs bakery — needs context"),
        ("аптека", "paraphernalia vs pharmacy job"),
        ("база", "drug stash vs database/base"),
        ("бабочка", "IV catheter vs insect/name"),
        ("автомат", "syringe vs machine/gun"),
        ("аппарат", "syringe vs equipment"),
        ("балда", "drugs vs fool/name"),
        ("быстрый", "speed drug vs neutral adjective"),
        ("белая", "heroin vs neutral adjective"),
        ("черный", "heroin grade vs neutral"),
        ("светлый", "heroin grade vs neutral"),
        ("скучный", "heroin grade vs boring"),
        ("грустный", "heroin grade vs sad"),
        ("хлеб", "heroin vs food"),
        ("лошадь", "heroin dose vs animal"),
        ("перец", "drug vs spice"),
        ("энергия", "stimulant vs neutral"),
        ("соль", "synthetic drug vs cooking — high FP"),
        ("коса", "heroin vs braid/tool"),
        ("свежий", "drug quality vs food"),
        ("сырой", "raw drug vs uncooked"),
        ("дурь", "drug vs generic harm word"),
        ("дым", "marijuana smoke vs neutral"),
        ("трава", "marijuana vs lawn/plant"),
        ("травка", "marijuana vs generic grass"),
        ("шишка", "cannabis bud vs bump on head"),
        ("пластилин", "hash vs toy clay"),
        ("молоко", "marijuana/opium vs dairy"),
        ("табакерка", "marijuana container vs snuff box"),
        ("конопа", "cannabis vs hemp industry"),
        ("дорога", "vein injection track slang vs road"),
        ("дорожка", "injection track marks vs path"),
        ("конопель", "cannabis vs hemp"),
        ("девочку", "sex objectification — legitimate job ads use «девочка/девочек»"),
        ("домохозяйка", "prostitution euphemism vs housewife job ads"),
        ("грелка", "prostitution euphemism vs hot water bottle"),
        ("мочалка", "prostitution euphemism vs sponge/scouring pad"),
        ("липучка", "prostitution euphemism vs Velcro/sticker"),
        ("кожа", "prostitution euphemism vs skin/leather trade"),
        ("тётка", "prostitution euphemism vs aunt/family"),
    ]
}

# Extend with EXCLUDE_FALSE_POSITIVES not already documented
for _fp in EXCLUDE_FALSE_POSITIVES:
    if _fp not in CONTEXT_REQUIRED_REASONS and CYRILLIC_RE.search(_fp):
        CONTEXT_REQUIRED_REASONS.setdefault(_fp, "EXCLUDE_FALSE_POSITIVES homonym")


@dataclass
class ExtractionStats:
    per_source_raw: Counter[str] = field(default_factory=Counter)
    per_source_new: Counter[str] = field(default_factory=Counter)
    skipped_existing: int = 0
    skipped_invalid: int = 0
    skipped_unclassified: int = 0
    skipped_context_routed: int = 0


def load_existing_wordlists() -> set[str]:
    existing: set[str] = set()
    for name in WORDLIST_FILES:
        path = MOD_DIR / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            t = norm(line.split("#", 1)[0].strip())
            if t:
                existing.add(t)
    return existing


def read_source_text(path: Path) -> str:
    raw = path.read_bytes()
    best_text = ""
    best_score = -1
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        cyr = len(CYRILLIC_RE.findall(text[:8000]))
        if cyr > best_score:
            best_score = cyr
            best_text = text
    if best_score == 0 and raw:
        try:
            latin = raw.decode("latin-1")
            recovered = latin.encode("latin-1").decode("cp1251", errors="replace")
            if CYRILLIC_RE.search(recovered[:8000]):
                best_text = recovered
        except Exception:
            pass
    if best_text:
        return best_text
    return raw.decode("utf-8", errors="replace")


def section_hint(section_label: str) -> str | None:
    for pattern, cat in SECTION_CATEGORY_HINTS:
        if pattern.search(section_label):
            return cat
    return None


def classify_term(term: str, hint: str | None = None) -> str | None:
    t = norm(term)
    if hint:
        return hint
    if t in ACADEMIC_JARGON:
        return ACADEMIC_JARGON[t]
    if t in KNOWN_SEX_PHRASES:
        return "sex"
    return classify(t)


def is_valid_phrase(phrase: str, hint: str | None = None) -> bool:
    t = norm(phrase)
    words = t.split()
    if t in KNOWN_SEX_PHRASES or t in ACADEMIC_JARGON:
        return True
    if any(c in t for c in "«»\"'[]()"):
        return False
    if "—" in t or "–" in t:
        return False
    if PHRASE_FRAGMENT_START.match(t):
        return False
    if re.search(r"\d{2,}", t):
        return False
    if len(words) < 2 or len(words) > 5:
        return False
    if any(w in PHRASE_STOPWORDS for w in words):
        return False
    if len(words) > 4:
        return False
    if not any(matches_stem(w, SEX_STEMS | DRUG_STEMS | PROFANITY_STEMS) for w in words):
        return False
    return classify(t) in ("sex", "drugs", "profanity", "translit")


def add_headwords(payload: str, out: list[tuple[str, str | None]], hint: str | None) -> None:
    for part in re.split(r",\s*", payload):
        part = part.strip()
        part = re.sub(r"^\d+\.\s*", "", part)
        part = re.sub(r"\s+", " ", part)
        if part and len(part) <= 80:
            out.append((part, hint))


def split_comma_terms(payload: str) -> list[str]:
    parts: list[str] = []
    for chunk in re.split(r"[,;]", payload):
        chunk = chunk.strip()
        chunk = re.sub(r"^\d+\.\s*", "", chunk)
        chunk = re.sub(r"\([^)]*\)", "", chunk).strip()
        chunk = re.sub(r"\s+", " ", chunk)
        if chunk:
            parts.append(chunk)
    return parts


def is_abannet_comma_list_line(stripped: str) -> bool:
    """True for inline comma-separated slang lists, not dictionary definition prose."""
    if re.search(r"\s(?:—|–|-)\s", stripped):
        return False
    if stripped and stripped[0].islower() and not re.match(r"^[a-z]", stripped):
        # lowercase Cyrillic slang lists are OK; skip prose continuation lines
        if stripped.count(",") < 2:
            return False
    low = stripped.lower()
    if any(
        x in low
        for x in (
            " что ", " который ", " которые ", " когда ", " если ", " чтобы ",
            " как ", " также ", " часто ", " может ", " при ", " после ", " перед ",
            " http", " www", " характерные обороты", " отсюда ",
        )
    ):
        return False
    if "," not in stripped or len(stripped) > 180:
        return False
    parts = split_comma_terms(stripped)
    valid = [p for p in parts if CYRILLIC_RE.search(p) and 2 <= len(p) <= 40]
    if len(valid) < 2:
        return False
    return all(len(p.split()) <= 4 for p in valid)


def preprocess_abannet_text(text: str) -> str:
    """Join wrapped section headers and headword — definition lines."""
    text = re.sub(
        r"Сленговые\s+(?:\r?\n\s*)+слова(?:,\s*(?:\r?\n\s*)+используемые[^\n:]*)?:",
        "Сленговые слова, используемые наркоманами, которые употребляют самодельные психостимуляторы:",
        text,
        flags=re.IGNORECASE,
    )
    lines = text.splitlines()
    merged: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if (
            i + 2 < len(lines)
            and re.match(r"^[A-Za-zА-Яа-яЁё0-9][\w\s,\-()/]{0,70}$", line)
            and lines[i + 1].strip() in ("—", "–", "-")
        ):
            rest = lines[i + 2].strip()
            j = i + 3
            while (
                j < len(lines)
                and lines[j].strip()
                and not re.match(r"^[A-Za-zА-Яа-яЁё0-9]", lines[j].strip()[:1])
                and "—" not in lines[j]
                and "–" not in lines[j]
                and len(lines[j].strip()) < 120
            ):
                rest = f"{rest} {lines[j].strip()}"
                j += 1
            merged.append(f"{line} — {rest}")
            i = j
            continue
        merged.append(line)
        i += 1
    return "\n".join(merged)


def extract_umk_footnote_terms(text: str) -> list[tuple[str, str | None]]:
    """Single-word RU slang from Dembska UMK footnote glosses (prostitution context)."""
    out: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for m in UMK_FOOTNOTE_HEADWORD_RE.finditer(text):
        word = norm(m.group(1))
        if word in seen or not is_valid_term(word):
            continue
        gloss = text[m.end() : m.end() + 280].lower()
        if not any(marker in gloss for marker in UMK_PROSTITUTION_GLOSS_MARKERS):
            continue
        seen.add(word)
        out.append((word, "sex"))
    return out


def extract_cyrillic_terms(text: str) -> set[str]:
    found: set[str] = set()
    for m in CYR_PHRASE_RE.finditer(text):
        found.add(norm(m.group(0)))
    for m in CYR_TOKEN_RE.finditer(text):
        found.add(norm(m.group(0)))
    return found


def is_context_required(term: str) -> bool:
    t = norm(term)
    if " " in t:
        return False
    if t in SEX_CONTEXT_HOMONYMS or t in CONTEXT_REQUIRED_REASONS:
        return True
    # Single short common word classified as drug/sex but not stem-unique
    if len(t) <= 6 and t in EXCLUDE_FALSE_POSITIVES:
        return True
    return False


def route_term(
    term: str,
    *,
    existing: set[str],
    phrases: set[str],
    tokens: dict[str, set[str]],
    context_required: dict[str, str],
    stats: ExtractionStats,
    source: str,
    hint: str | None = None,
) -> None:
    t = norm(term)
    stats.per_source_raw[source] += 1
    if any(c in t for c in "«»\"'[]"):
        stats.skipped_invalid += 1
        return
    if not is_valid_term(t):
        stats.skipped_invalid += 1
        return
    if t in existing or is_excluded(t):
        stats.skipped_existing += 1
        return
    cat = classify_term(t, hint)
    if cat is None:
        stats.skipped_unclassified += 1
        return
    if " " in t:
        if not is_valid_phrase(t, hint):
            stats.skipped_unclassified += 1
            return
        phrases.add(t)
        stats.per_source_new[source] += 1
        return
    if is_context_required(t):
        context_required.setdefault(t, CONTEXT_REQUIRED_REASONS.get(t, "ambiguous homonym"))
        stats.skipped_context_routed += 1
        stats.per_source_new[source] += 1
        return
    tokens[cat].add(t)
    stats.per_source_new[source] += 1


def parse_dictionary_entries(text: str, hint: str | None = "drugs") -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("http") or len(line) > 500:
            i += 1
            continue
        if re.match(r"^[А-ЯA-ZЁ]$", line):
            i += 1
            continue
        m = DICT_ENTRY_RE.match(line)
        if m:
            add_headwords(m.group(1), out, hint)
            i += 1
            continue
        if (
            i + 1 < len(lines)
            and (lines[i + 1].strip().startswith(":") or re.match(r"^-\s", lines[i + 1].strip()))
            and re.match(r"^[A-Za-zА-Яа-яЁё0-9]", line)
            and len(line) < 80
        ):
            add_headwords(line, out, hint)
            i += 2
            continue
        colon_match = re.match(r"^([A-Za-zА-Яа-яЁё0-9,\s\-()]+)\s*:\s*", line)
        if colon_match:
            add_headwords(colon_match.group(1), out, hint)
            i += 1
            continue
        dash_match = re.match(r"^([A-Za-zА-Яа-яЁё0-9,\s\-()]{2,60}?)\s*(?:—|–)\s*", line)
        if dash_match:
            add_headwords(dash_match.group(1), out, hint)
            i += 1
            continue
        if re.search(r"\s-\s", line):
            left = re.split(r"\s*(?:—|–|-)\s*", line, maxsplit=1)[0]
            if left and len(left) < 60:
                for part in split_comma_terms(left):
                    if len(part.split()) <= 8:
                        out.append((part, hint))
        i += 1
    return out


def parse_russki_mat(text: str) -> list[tuple[str, str | None]]:
    return parse_dictionary_entries(text, hint="drugs")


def parse_abannet(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    text = preprocess_abannet_text(text)
    section_re = re.compile(
        r"^Сленговые\s+(?:названия\s+(.+?)|слова(?:,\s*используемые.+?)?):\s*$",
        re.IGNORECASE,
    )
    general_section_re = re.compile(r"^Общие\s+слова", re.IGNORECASE)
    stim_section_re = re.compile(r"^\d+\.\s*(?:Первитин|Эфедрон)", re.IGNORECASE)
    current_hint: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if general_section_re.match(stripped):
            current_hint = "drugs"
            continue
        if stim_section_re.match(stripped):
            current_hint = "drugs"
            continue
        sec = section_re.match(stripped)
        if sec:
            label = sec.group(1) or stripped
            current_hint = section_hint(label) or "drugs"
            continue
        if stripped.startswith("Сленговые") and ":" in stripped:
            header, payload = stripped.split(":", 1)
            current_hint = section_hint(header) or current_hint or "drugs"
            for part in split_comma_terms(payload):
                out.append((part, current_hint))
            continue
        for term, hint in parse_dictionary_entries(stripped, current_hint or "drugs"):
            out.append((term, hint))
        if current_hint and is_abannet_comma_list_line(stripped):
            for part in split_comma_terms(stripped):
                if 2 <= len(part) <= 40 and CYRILLIC_RE.search(part):
                    out.append((part, current_hint))
    return out


def parse_newlit_shkarin(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if i + 1 < len(lines) and re.match(r"^-\s", lines[i + 1].strip()):
            head = line.strip()
            if CYRILLIC_RE.search(head) and len(head) < 60:
                out.append((head, "drugs"))
            i += 2
            continue
        m = re.match(r"^(.+?)\s*-\s*(.+)$", line)
        if m and len(m.group(1)) < 60 and CYRILLIC_RE.search(m.group(1)):
            out.append((m.group(1).strip(), "drugs"))
        i += 1
    return out


def parse_prostitution_papers(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    sex_hint = "sex"
    for phrase in KNOWN_SEX_PHRASES:
        if phrase.replace("ё", "е") in text.lower().replace("ё", "е"):
            out.append((phrase, sex_hint))
    for m in re.finditer(
        r"(жриц\w*\s+любви|честн\w+\s+куртизан\w+|легк\w+\s+кавалер\w+|"
        r"ночн\w+\s+бабоч\w+|красн\w+\s+фонар\w+|"
        r"дом\s+под\s+красным\s+фонар\w+|дам\w+\s+из\s+амстердам\w+|"
        r"легк\w+\s+жизн\w+|легк\w+\s+нрав\w+|"
        r"продажн\w+\s+люб\w+|наемн\w+\s+люб\w+)",
        text,
        re.IGNORECASE,
    ):
        out.append((m.group(0), sex_hint))
    for m in PHRASEOLOGISM_RE.finditer(text):
        raw = m.group(1).strip("«»\"' ")
        raw = re.sub(r"\s+", " ", raw)
        if raw in KNOWN_SEX_PHRASES or (
            CYRILLIC_RE.search(raw) and 2 <= len(raw.split()) <= 5
        ):
            out.append((raw, sex_hint))
    out.extend(extract_umk_footnote_terms(text))
    return out


def parse_shlyakhov(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^[A-Z][A-Z\s,/\-]{1,40},\s", line.strip()):
            block = [line]
            j = i + 1
            while j < len(lines) and j < i + 8:
                nxt = lines[j].strip()
                if re.match(r"^[A-Z][A-Z\s,/\-]{1,40},\s", nxt):
                    break
                block.append(lines[j])
                j += 1
            block_text = " ".join(block)
            if SHLYAKHOV_DRUG_SEX_MARKERS.search(block_text) or matches_stem(
                block_text.lower(), DRUG_STEMS | SEX_STEMS | PROFANITY_STEMS
            ):
                for cyr in extract_cyrillic_terms(block_text):
                    out.append((cyr, None))
                head = line.strip().split(",", 1)[0]
                for tok in LATIN_TOKEN_RE.findall(head):
                    if len(tok) >= 3:
                        out.append((tok, "translit"))
            i = j
            continue
        if CYRILLIC_RE.search(line) and matches_stem(
            line.lower(), DRUG_STEMS | SEX_STEMS | PROFANITY_STEMS
        ):
            for cyr in extract_cyrillic_terms(line):
                out.append((cyr, None))
        i += 1
    return out


def parse_hf_sensitive(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for line in text.splitlines():
        low = line.lower()
        for m in re.finditer(
            r"(?:ночн\w*\s+бабоч\w+|vip\s+девуш\w+|интим\s+услу\w+|"
            r"красн\w+\s+фонар\w+|жриц\w+\s+любви|массаж\s+18\+?)",
            low,
        ):
            out.append((m.group(0), "sex"))
    return out


def parse_bayramova_review(text: str) -> list[tuple[str, str | None]]:
    """Bayramova txt is a book review, not the dictionary — extract quoted drug terms."""
    out: list[tuple[str, str | None]] = []
    for m in re.finditer(r"\(([а-яё][^)]{2,40})\)", text, re.IGNORECASE):
        inner = m.group(1)
        if matches_stem(inner, DRUG_STEMS):
            out.append((inner, "drugs"))
    for m in re.finditer(
        r"(?:angel dust|bad bundle|coconut|bin laden|twin towers|"
        r"pig killer|killer joint|lethal weapon)",
        text,
        re.IGNORECASE,
    ):
        out.append((m.group(0), "drugs"))
    return out


def parse_cuni_bppr(text: str) -> list[tuple[str, str | None]]:
    """Czech drug slang dictionary — skip; occasional RU fragments only."""
    return []


def generic_dictionary_parser(text: str) -> list[tuple[str, str | None]]:
    return parse_dictionary_entries(text, hint=None)


SOURCE_PARSERS: dict[str, callable] = {
    "russki_mat_narc.txt": parse_russki_mat,
    "abannet_narcotics.txt": parse_abannet,
    "newlit_shkarin.txt": parse_newlit_shkarin,
    "researchgate_euphemisms.txt": parse_prostitution_papers,
    "umk_dembska.txt": parse_prostitution_papers,
    "shlyakhov_adler_dict.txt": parse_shlyakhov,
    "hf_sensitive_topics.txt": parse_hf_sensitive,
    "cyberleninka_bayramova.txt": parse_bayramova_review,
    "cuni_bppr_2014.txt": parse_cuni_bppr,
}


def write_tokens(path: Path, tokens: dict[str, set[str]]) -> int:
    order = ("drugs", "sex", "profanity", "translit")
    lines: list[str] = []
    total = 0
    for cat in order:
        bucket = sorted(tokens.get(cat, set()))
        if not bucket:
            continue
        lines.append(f"# {cat}")
        lines.extend(bucket)
        lines.append("")
        total += len(bucket)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return total


def write_lines(path: Path, terms: set[str]) -> int:
    ordered = sorted(terms)
    path.write_text("\n".join(ordered) + ("\n" if ordered else ""), encoding="utf-8")
    return len(ordered)


def write_context(path: Path, context: dict[str, str]) -> int:
    lines: list[str] = []
    for term in sorted(context):
        reason = context[term]
        lines.append(f"{term}  # {reason}")
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def dedupe_file_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            out.append(line)
            continue
        term = norm(line.split("#", 1)[0].strip())
        if term in seen:
            continue
        seen.add(term)
        out.append(line)
    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing_wordlists()
    stats = ExtractionStats()

    phrases: set[str] = set()
    tokens: dict[str, set[str]] = defaultdict(set)
    context_required: dict[str, str] = {}

    txt_files = sorted(TXT_DIR.glob("*.txt"))
    if not txt_files:
        print(f"No txt sources in {TXT_DIR}", file=sys.stderr)
        return 1

    for path in txt_files:
        source = path.name
        parser = SOURCE_PARSERS.get(source, generic_dictionary_parser)
        text = read_source_text(path)
        raw_terms = parser(text)
        for term, hint in raw_terms:
            route_term(
                term,
                existing=existing,
                phrases=phrases,
                tokens=tokens,
                context_required=context_required,
                stats=stats,
                source=source,
                hint=hint,
            )

    # Remove any phrase that landed in context (shouldn't happen)
    context_terms = set(context_required)
    phrases -= context_terms

    counts = {
        "candidates_phrases.txt": write_lines(OUT_DIR / "candidates_phrases.txt", phrases),
        "candidates_tokens.txt": write_tokens(OUT_DIR / "candidates_tokens.txt", tokens),
        "candidates_context_required.txt": write_context(
            OUT_DIR / "candidates_context_required.txt", context_required
        ),
    }

    per_cat = {cat: len(bucket) for cat, bucket in tokens.items()}
    extraction_stats = {
        "sources": {p.name: SOURCE_PARSERS.get(p.name, generic_dictionary_parser).__name__ for p in txt_files},
        "per_source_raw_hits": dict(stats.per_source_raw),
        "per_source_new_candidates": dict(stats.per_source_new),
        "totals": {
            "phrases": counts["candidates_phrases.txt"],
            "tokens": sum(per_cat.values()),
            "tokens_by_category": per_cat,
            "context_required": counts["candidates_context_required.txt"],
        },
        "skipped": {
            "existing_or_excluded": stats.skipped_existing,
            "invalid": stats.skipped_invalid,
            "unclassified": stats.skipped_unclassified,
            "routed_to_context": stats.skipped_context_routed,
            "duplicates_in_existing_wordlists": stats.skipped_existing,
        },
        "existing_wordlist_size": len(existing),
    }
    (OUT_DIR / "extraction_stats.json").write_text(
        json.dumps(extraction_stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(extraction_stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
