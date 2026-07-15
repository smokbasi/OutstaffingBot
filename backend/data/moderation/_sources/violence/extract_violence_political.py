#!/usr/bin/env python3
"""Regenerate violence/political candidate wordlists from multi-source web research.

Usage (from repo root):
    python backend/data/moderation/_sources/violence/extract_violence_political.py

Reads vendored + downloaded sources in sources/, krugozor, kugimiya.
Writes candidates ONLY — never touches live stop_words_*.txt.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCES_DIR = BASE / "sources"
PARENT_SOURCES = BASE.parent
KRUGOZOR = PARENT_SOURCES / "krugozor_stopwords.php"
KUGIMIYA = PARENT_SOURCES / "kugimiya_banlist.yaml"

OUT_TOKENS = BASE / "candidates_violence.txt"
OUT_PHRASES = BASE / "candidates_violence_phrases.txt"
OUT_CONTEXT = BASE / "candidates_context_required.txt"
OUT_REGEX = BASE / "candidates_violence_regex.txt"
OUT_TOPICS = BASE / "candidates_violence_topics.md"
OUT_STATS = BASE / "extraction_stats.json"

# Curated exclusions — HurtLex/web FP + vsecoder stem leaks; survives regen
EXCLUDE_TERMS_RAW: list[str] = [
    "изделие", "мог", "чоп", "белых", "болгарин", "болгарка", "болгарский", "болгары",
    "бош", "вороной", "горчичник", "джерри", "китаец", "китайский", "китайцы", "китаянка",
    "колорад", "колорадка", "латиноамериканцем",
    "монгол", "монголка", "монголоид", "монголоидов", "монголоиды", "монголы", "монгольский",
    "мужик", "мужлан", "остгот", "остготов", "остготы", "остроготы", "помесь", "рома",
    "селекционер", "скиталец", "скрещивании", "скрещивания", "скрещивать",
    "странник", "странница", "тические", "черный", "яростный",
    "найду", "крышка",
    # vsecoder/web artifacts — not dictionary tokens
    "деhumanизация",
]

# Manual war/SVO tokens (not auto-extracted or previously in skip)
MANUAL_WAR_TOKENS: dict[str, str] = {
    "араб": "manual review — Middle East war discourse",
    "израиль": "manual review — Israel/Palestine war discourse",
    "сво": "manual review — СВО abbreviation (war context), NOT pronoun сво/своё",
}

# Topic routing for web source files
WEB_SOURCE_ROUTES: dict[str, str] = {
    "web_terrorism_urfu.txt": "terrorism/extremism",
    "web_cyberleninka_igil.txt": "terrorism/extremism",
    "web_war_glossary_ru.txt": "war/SVO/Ukraine",
    "web_dfrlab_rkn_tags.txt": "war/SVO/Ukraine",
    "web_protests_legal.txt": "protests/political actions",
    "web_police_slang.txt": "law enforcement (slang)",
    "web_political_figures.txt": "political figures/titles",
    "web_hate_speech.txt": "hate speech / ethnic slurs",
    "web_islamism_terms.txt": "terrorism/extremism",
    "web_torture_violence.txt": "torture/violence verbs",
    "web_weapons_drones.txt": "weapons/explosives/drones",
}

SECTION_ORDER = [
    "terrorism/extremism",
    "war/SVO/Ukraine",
    "weapons/explosives/drones",
    "protests/political actions",
    "law enforcement (slang)",
    "political figures/titles",
    "hate speech / ethnic slurs",
    "torture/violence verbs",
    "suicide/self-harm",
]

# Phrases by topic (multi-word; not auto-extracted from single-line sources)
PHRASES_BY_TOPIC: dict[str, list[str]] = {
    "torture/violence verbs": [
        "убью тебя", "убью вас", "убил бы тебя", "пришью тебя", "придушу тебя",
        "порешу тебя", "грохну тебя", "зарежу тебя", "застрелю тебя",
        "найду тебя", "найду вас", "хана тебе", "крышка тебе", "конец тебе",
        "голову оторву", "голову оторв", "башку оторву", "башку оторв",
        "впиздячу тебя", "изобью до полусмерти", "сдохни уже", "сдохни скорее",
        "оторву башку", "впиздячу по полной", "убью на месте", "убью если",
        "зарежу если", "расстреляю всех", "прирежу тебя", "добью тебя",
        "заколю тебя", "пытать до смерти", "изнасилую тебя", "изнасилую если",
        "изнасилую вас",
    ],
    "war/SVO/Ukraine": [
        "нет войне", "нет мобилизации", "не хочу воевать", "отказ от мобилизации",
        "спецоперация на украине", "частичная мобилизация", "отдать крым",
        "крымнаш", "слава украине", "героям слава", "смерть путину", "путин вор",
        "путин убийца", "зеленский наркоман", "мы вместе с россией",
        "Zа наших", "Zа победу", "шайка наркоманов", "неонацисты киева",
        "фейки о войне", "ложная информация о спецоперации", "дискредитация армии",
        "дискредитация вооруженных сил", "массовая мобилизация",
        "майданный игил", "укроигил", "православный игил",
    ],
    "protests/political actions": [
        "выходите на митинг", "выходите на протест", "призыв к митингу",
        "призыв к протесту", "все на митинг", "несогласованный митинг",
        "несанкционированный митинг", "акция протеста", "марш протеста",
        "гражданский протест", "приходите на пикет", "призывы к протесту",
        "насильственный переворот", "свержение власти", "захват власти",
    ],
    "weapons/explosives/drones": [
        "ракетный удар", "удар дронами", "fpv дрон", "fpv-дрон", "дрон-камикадзе",
        "самодельная бомба", "взрывное устройство", "взрывчатое вещество",
        "устроить теракт", "пойду на теракт", "взорвать фсб", "расстрелять полиц",
    ],
    "political figures/titles": [
        "путин вор", "путин убийца", "путин диктатор", "путин предатель",
        "путин расист", "путин гитлер", "смерть путину", "зеленский наркоман",
        "господин зеленский", "оскорбление президента",
    ],
    "terrorism/extremism": [
        "исламский терроризм", "исламский экстремизм", "радикальный исламизм",
        "политический ислам", "хайль игил",
    ],
}

CONTEXT_REQUIRED: dict[str, str] = {
    "убить": "threat vs neutral (убить баг)",
    "убивать": "threat vs neutral",
    "добить": "threat vs sports",
    "застрелить": "threat vs hunting license context",
    "зарезать": "threat vs cooking",
    "порезать": "threat vs budget/cooking",
    "забить": "threat vs nails",
    "избить": "threat vs sports",
    "автомат": "gun vs machine",
    "кровь": "threat vs medicine",
    "расстрел": "threat vs photography",
    "насилие": "threat vs anti-violence advocacy",
    "огнестрел": "weapon vs security license",
    "травмат": "weapon vs trauma medicine",
    "дубинка": "weapon vs security gear",
    "убью": "threat vs idiom",
    "ислам": "religion/halal vs islamism",
    "протест": "legal dissent vs riot incitement",
    "украина": "geography/logistics vs war propaganda",
    "президент": "corporate title vs political figure",
    "война": "history vs warmongering",
    "мобилизация": "HR vs draft evasion",
    "спецоперация": "medical vs SVO euphemism",
    "дрон": "delivery jobs vs weaponized UAV",
    "бпла": "commercial UAV vs military",
    "ракета": "space vs missile; drug slang",
    "взрыв": "demolition vs terror",
    "полиция": "security jobs vs anti-police",
    "депутат": "neutral vs campaigning",
    "фсб": "clearance vs agency threat",
    "крым": "tourism vs territorial propaganda",
    "митинг": "corporate vs street protest",
    "демонстрация": "product demo vs demonstration",
    "мусор": "waste vs police slang",
    "изнасиловать": "legal reporting vs threat",
    "пытать": "fiction/legal vs torture threat",
    "теракт": "news vs planning",
    "силовик": "journalism vs derogatory",
    "бомба": "demolition engineering vs terror device",
    "граната": "sports trophy vs weapon",
    "мина": "HR onboarding vs landmine",
    "снайпер": "esports vs combat role",
    "казнь": "history vs threat",
    "расизм": "anti-racism advocacy vs hate speech",
    "нацизм": "history education vs glorification",
    "фашизм": "history education vs glorification",
    "джихад": "religious term vs extremism",
    "шахид": "memorial context vs terror glorification",
    "путин": "neutral mention vs incitement",
    "зеленский": "news vs slur campaigns",
    "вагнер": "corporate name vs PMC",
    "орки": "fantasy/gaming vs dehumanization",
    "ватник": "clothing vs slur",
}

SKIP_PHRASES: list[str] = [
    "смерть", "рецепт", "донор", "убью время", "убить баг", "убить двух зайцев",
    "отбить атаку", "смертность", "донор крови", "рецепт успеха", "забить гвоздь",
    "порезать бюджет", "порезать овощи", "президент компании", "президент фирмы",
    "президент банка", "исламский банк", "халяль", "протест против насилия",
    "протест против коррупции", "логистика украина", "работа украина",
    "доставка дронами", "оператор дрона", "космическая ракета",
    "демонстрация продукта", "демонстрация оборудования", "корпоративный митинг",
    "митинг акционеров", "медицинская спецоперация",
    "спецоперация на позвоночник", "туризм крым", "отдых крым",
    "своё", "свой", "своя", "свои", "милдронат", "феромон",
    "вывоз мусора", "утилизация мусора", "мусорный контейнер",
]

KRUGOZOR_ROUTES: dict[str, str] = {
    "игил": "terrorism/extremism", "игиловец": "terrorism/extremism",
    "аль-каида": "terrorism/extremism", "алькаида": "terrorism/extremism",
    "талибан": "terrorism/extremism", "исламизм": "terrorism/extremism",
    "джихад": "terrorism/extremism", "ваххабизм": "terrorism/extremism",
    "халифат": "terrorism/extremism", "моджахед": "terrorism/extremism",
    "шахид": "terrorism/extremism", "нацизм": "terrorism/extremism",
    "фашизм": "terrorism/extremism", "свастика": "terrorism/extremism",
    "зиг-хайль": "terrorism/extremism", "зигхайль": "terrorism/extremism",
    "майн-кампф": "terrorism/extremism", "mein-kampf": "terrorism/extremism",
    "фюрер": "terrorism/extremism", "исламское-государство": "terrorism/extremism",
    "бандеровец": "war/SVO/Ukraine", "бандеровцы": "war/SVO/Ukraine",
    "русофобия": "terrorism/extremism", "сепаратизм": "terrorism/extremism",
    "колорад": "war/SVO/Ukraine", "огнестрел": "weapons/explosives/drones",
    "травмат": "weapons/explosives/drones", "шокер": "weapons/explosives/drones",
    "электрошокер": "weapons/explosives/drones", "кастет": "weapons/explosives/drones",
    "дубинка": "weapons/explosives/drones", "ружье": "weapons/explosives/drones",
    "суицид": "suicide/self-harm", "суизид": "suicide/self-harm",
    "самоубийство": "suicide/self-harm", "эвтаназия": "suicide/self-harm",
    "снотворное": "suicide/self-harm", "выпилиться": "suicide/self-harm",
    "харакири": "suicide/self-harm",
}

KUGIMIYA_ROUTES: dict[str, str] = {
    "митинг": "protests/political actions", "протест": "protests/political actions",
    "террор": "terrorism/extremism", "джихад": "terrorism/extremism",
    "игил": "terrorism/extremism", "шахид": "terrorism/extremism",
    "украин": "war/SVO/Ukraine", "киев": "war/SVO/Ukraine", "крым": "war/SVO/Ukraine",
    "луганск": "war/SVO/Ukraine", "донецк": "war/SVO/Ukraine",
    "путин": "political figures/titles", "зеленск": "political figures/titles",
    "навальн": "political figures/titles", "лукашенко": "political figures/titles",
    "собянин": "political figures/titles", "шойгу": "political figures/titles",
    "вагнер": "war/SVO/Ukraine", "президент": "political figures/titles",
    "теракт": "terrorism/extremism", "пытк": "torture/violence verbs",
    "изнасил": "torture/violence verbs", "фсб": "law enforcement (slang)",
    "хач": "hate speech / ethnic slurs", "чурк": "hate speech / ethnic slurs",
    "жид": "hate speech / ethnic slurs", "хохл": "hate speech / ethnic slurs",
    "гитлер": "terrorism/extremism", "адольф": "terrorism/extremism",
    "донбас": "war/SVO/Ukraine", "бандер": "war/SVO/Ukraine",
    "пиндос": "hate speech / ethnic slurs", "рашк": "hate speech / ethnic slurs",
    "русн": "hate speech / ethnic slurs",
}

PHP_STRING_RE = re.compile(r"'([^']+)'")
KUGIMIYA_ROOT_RE = re.compile(r"\( \|^\)([а-яёa-z\-]+)")
KUGIMIYA_PLAIN_RE = re.compile(r"^\s*-\s+([а-яёa-z\-]+)\s*$", re.MULTILINE)
VSECODER_PATTERN_RE = re.compile(r"r'\\b([^']+)'")
HURTLEX_VIOLENCE_CATS = {"re", "ps"}
# HurtLex RE is mostly legal/crime vocabulary — keep violence-relevant lemmas only
HURTLEX_RE_ALLOW_SUBSTR = (
    "террор", "убий", "насил", "пыт", "изнасил", "взрыв", "бомб", "расстрел",
    "казн", "истяз", "зарез", "застрел", "расчлен", "обезглав", "похищ",
    "поджог", "диверс", "насиль", "преступ", "убив", "теракт", "пытк",
    "сексуальн", "нападен", "убийц", "убийств", "человекоубий",
)

REGEX_PATTERN_MARKERS = re.compile(r"[\[\]\?\*\+\|]")
_EXCLUDE_TERMS: frozenset[str] | None = None
_SKIP_TOKENS: frozenset[str] | None = None


# Combining marks stripped as stress accents (HurtLex), not й-breve (U+0306)
_STRESS_COMBINING = frozenset("\u0301\u0300\u0304")


def norm(term: str) -> str:
    t = term.strip().lower().replace("ё", "е")
    # strip bidi / format controls (e.g. U+202A/U+202C in HurtLex lemmas)
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    # Remove vowel stress marks only; preserve й (и + U+0306 breve)
    parts: list[str] = []
    for c in unicodedata.normalize("NFD", t):
        if unicodedata.category(c) == "Mn" and c in _STRESS_COMBINING:
            continue
        parts.append(c)
    return unicodedata.normalize("NFC", "".join(parts))


def exclude_terms() -> frozenset[str]:
    global _EXCLUDE_TERMS
    if _EXCLUDE_TERMS is None:
        _EXCLUDE_TERMS = frozenset(norm(t) for t in EXCLUDE_TERMS_RAW)
    return _EXCLUDE_TERMS


def skip_tokens() -> frozenset[str]:
    global _SKIP_TOKENS
    if _SKIP_TOKENS is None:
        _SKIP_TOKENS = frozenset(norm(s) for s in SKIP_PHRASES)
    return _SKIP_TOKENS


def is_regex_pattern(raw: str) -> bool:
    """vsecoder patterns with character classes / quantifiers — not exact-match tokens."""
    return bool(REGEX_PATTERN_MARKERS.search(raw)) or r"\s" in raw


def is_valid_token(term: str) -> bool:
    t = norm(term)
    if len(t) < 3:
        return False
    if " " in t:
        return False
    if t in skip_tokens():
        return False
    if t in exclude_terms():
        return False
    return True


def load_web_txt(path: Path, section: str, bucket: dict[str, dict[str, set[str]]]) -> int:
    count = 0
    src = path.name
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        term = norm(line)
        if not is_valid_token(term):
            continue
        bucket[section][term].add(src)
        count += 1
    return count


def parse_krugozor(bucket: dict[str, dict[str, set[str]]]) -> int:
    text = KRUGOZOR.read_text(encoding="utf-8")
    count = 0
    for raw in PHP_STRING_RE.findall(text):
        term = norm(raw)
        section = KRUGOZOR_ROUTES.get(term)
        if section and is_valid_token(term):
            bucket[section][term].add("krugozor_stopwords.php")
            count += 1
    return count


def parse_kugimiya(bucket: dict[str, dict[str, set[str]]]) -> int:
    text = KUGIMIYA.read_text(encoding="utf-8")
    roots: set[str] = set()
    for m in KUGIMIYA_ROOT_RE.finditer(text):
        roots.add(norm(m.group(1)))
    for m in KUGIMIYA_PLAIN_RE.finditer(text):
        roots.add(norm(m.group(1)))
    count = 0
    for root in roots:
        for prefix, section in KUGIMIYA_ROUTES.items():
            if root.startswith(prefix) or prefix.startswith(root):
                if is_valid_token(root):
                    bucket[section][root].add("kugimiya_banlist.yaml")
                    count += 1
                break
    return count


def parse_vsecoder(
    bucket: dict[str, dict[str, set[str]]],
    regex_bucket: dict[str, dict[str, set[str]]],
) -> tuple[int, int]:
    path = SOURCES_DIR / "vsecoder_make_multilabel.py"
    if not path.exists():
        return 0, 0
    text = path.read_text(encoding="utf-8")
    token_count = 0
    regex_count = 0
    in_threat = False
    in_identity = False
    for line in text.splitlines():
        if "THREAT_IMPERATIVE" in line or "THREAT_DIRECTIONAL" in line:
            in_threat = True
            in_identity = False
        elif "IDENTITY" in line and "=" in line:
            in_identity = True
            in_threat = False
        elif line.strip().startswith("]"):
            in_threat = in_identity = False
        if not (in_threat or in_identity):
            continue
        section = (
            "hate speech / ethnic slurs" if in_identity else "torture/violence verbs"
        )
        for m in VSECODER_PATTERN_RE.finditer(line):
            raw = m.group(1)
            if is_regex_pattern(raw):
                regex_bucket[section][raw].add("vsecoder_make_multilabel.py")
                regex_count += 1
                continue
            # strip regex suffixes like \s+тебя
            stem = re.split(r"\\s|\\b", raw)[0].strip()
            term = norm(stem)
            if not is_valid_token(term):
                continue
            bucket[section][term].add("vsecoder_make_multilabel.py")
            token_count += 1
    return token_count, regex_count


def parse_hurtlex(bucket: dict[str, dict[str, set[str]]]) -> int:
    path = SOURCES_DIR / "hurtlex_ru_12.tsv"
    if not path.exists():
        return 0
    count = 0
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            cat = (row.get("category") or "").lower()
            if cat not in HURTLEX_VIOLENCE_CATS:
                continue
            lemma = norm(row.get("lemma") or "")
            if not is_valid_token(lemma):
                continue
            if cat == "re" and not any(s in lemma for s in HURTLEX_RE_ALLOW_SUBSTR):
                continue
            section = (
                "hate speech / ethnic slurs" if cat == "ps" else "torture/violence verbs"
            )
            bucket[section][lemma].add("hurtlex_ru_12.tsv")
            count += 1
    return count


def collect_all() -> tuple[
    dict[str, dict[str, set[str]]],
    dict[str, dict[str, set[str]]],
    dict[str, int],
    list[str],
]:
    # section -> term -> set[sources]
    bucket: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    regex_bucket: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    source_counts: dict[str, int] = {}

    for fname, section in WEB_SOURCE_ROUTES.items():
        path = SOURCES_DIR / fname
        if path.exists():
            source_counts[fname] = load_web_txt(path, section, bucket)

    source_counts["krugozor_stopwords.php"] = parse_krugozor(bucket)
    source_counts["kugimiya_banlist.yaml"] = parse_kugimiya(bucket)
    vsec_tokens, vsec_regex = parse_vsecoder(bucket, regex_bucket)
    source_counts["vsecoder_make_multilabel.py"] = vsec_tokens
    source_counts["vsecoder_make_multilabel.py (regex)"] = vsec_regex
    source_counts["hurtlex_ru_12.tsv"] = parse_hurtlex(bucket)

    for term, note in MANUAL_WAR_TOKENS.items():
        t = norm(term)
        if is_valid_token(t):
            bucket["war/SVO/Ukraine"][t].add(f"manual: {note}")

    all_phrases: list[str] = []
    for section, phrases in PHRASES_BY_TOPIC.items():
        for p in phrases:
            all_phrases.append(norm(p))

    return bucket, regex_bucket, source_counts, sorted(set(all_phrases))


def write_tokens(path: Path, bucket: dict[str, dict[str, set[str]]]) -> dict[str, int]:
    header = """# proposed — NOT in live wordlists yet
# Review before merge into stop_words_violence.txt
# AUTO-GENERATED by extract_violence_political.py — multi-source web research 2026-07-09
# Sources: 10+ per topic — NOT only Krugozor+vsecoder (see candidates_violence_topics.md)

"""
    lines = [header.rstrip(), ""]
    counts: dict[str, int] = {}
    for section in SECTION_ORDER:
        terms = bucket.get(section, {})
        if not terms:
            continue
        lines.append(f"## tokens — {section}")
        if section == "hate speech / ethnic slurs":
            lines.append("# WARNING: SENSITIVE ethnic pejoratives — legal review before merge")
        for term in sorted(terms):
            srcs = sorted(terms[term])
            comment = ", ".join(srcs[:3])
            if len(srcs) > 3:
                comment += f" +{len(srcs) - 3}"
            lines.append(f"{term}  # source: {comment}")
        lines.append("")
        counts[section] = len(terms)

    lines.append("## skip / homonym")
    lines.append("# See candidates_context_required.txt + inline skip below")
    for s in SKIP_PHRASES:
        lines.append(s)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return counts


def write_regex(path: Path, regex_bucket: dict[str, dict[str, set[str]]]) -> int:
    header = """# proposed regex patterns — phrase engine only, NOT exact token match
# AUTO-GENERATED by extract_violence_political.py from vsecoder_make_multilabel.py
#
# These are Python regex fragments (character classes, quantifiers, \\s anchors).
# They match word VARIANTS in context — e.g. ватн[аеуо][^_] catches ватник/ватна,
# чурк[аиое] catches ethnic slur inflections, оторв[уе]м? catches threat imperatives.
# Do NOT merge into stop_words_violence.txt as literal dictionary tokens.

"""
    lines = [header.rstrip(), "", "## regex_patterns (phrase engine only, NOT exact match)"]
    total = 0
    for section in SECTION_ORDER:
        patterns = regex_bucket.get(section, {})
        if not patterns:
            continue
        lines.append(f"# section: {section}")
        for pattern in sorted(patterns):
            srcs = sorted(patterns[pattern])
            comment = ", ".join(srcs[:2])
            lines.append(f"{pattern}  # source: {comment}")
            total += 1
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total


def write_phrases(path: Path, phrases: list[str]) -> int:
    header = """# proposed threat + political phrases — NOT in live wordlists yet
# AUTO-GENERATED by extract_violence_political.py — 50+ phrases from multi-source research

"""
    body = []
    for p in phrases:
        body.append(f"{p}  # source: extract_violence_political.py")
    path.write_text(header + "\n".join(body) + "\n", encoding="utf-8")
    return len(phrases)


def write_context(path: Path) -> int:
    header = """# proposed context_required — violence + political homonyms
# AUTO-GENERATED by extract_violence_political.py

"""
    lines = [header.rstrip(), ""]
    for term in sorted(CONTEXT_REQUIRED):
        lines.append(f"{term}  # {CONTEXT_REQUIRED[term]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(CONTEXT_REQUIRED)


def write_topics_report(
    path: Path,
    bucket: dict[str, dict[str, set[str]]],
    source_counts: dict[str, int],
    phrase_count: int,
    token_counts: dict[str, int],
) -> None:
    total_unique = sum(token_counts.values())
    lines = [
        "# Violence candidates — detailed per-topic research report",
        "",
        "Дата: 2026-07-09. **Candidates only** — не в live `stop_words_violence.txt`.",
        "",
        f"**Итого уникальных токенов:** {total_unique} | **Фраз:** {phrase_count}",
        "",
        "---",
        "",
    ]

    topic_reports = [
        {
            "name": "1. Terrorism / extremism RU",
            "queries": [
                "терроризм словарь модерация русский стоп слова github",
                "экстремизм стоп слова список РКН запрещённые термины",
                "IGIL исламское государство русский жаргон термины",
                "игилизация игиловщина cyberleninka",
                "security.urfu.ru основные термины экстремизм",
            ],
            "urls": [
                "https://github.com/Vasiliy-Makogon/RussianBadWords",
                "https://minjust.gov.ru/ru/extremist-materials/",
                "https://cyberleninka.ru/article/n/novaya-religiozno-politicheskaya-leksika-v-rossiyskih-smi-i-internet-diskurse-na-primere-proizvodnyh-slova-igil",
                "https://security.urfu.ru/ru/protivodeistvie-ehkstremizmu-i-terrorizmu/osnovnye-terminy-i-opredelenija/",
                "https://ru.wikipedia.org/wiki/Терроризм",
            ],
            "sources": ["web_terrorism_urfu.txt", "web_cyberleninka_igil.txt", "web_islamism_terms.txt", "krugozor_stopwords.php", "kugimiya_banlist.yaml"],
            "section": "terrorism/extremism",
            "notes": "MinJust публикует реестр материалов, не готовый wordlist. UrFU glossary + CyberLeninka IGIL derivatives — лучшие открытые RU термины. Islamism отделён от религии.",
        },
        {
            "name": "2. SVO / war",
            "queries": [
                "сво стоп слова модерация спецоперация",
                "мобилизация запрещённые фразы военная цензура слова россия",
                "спецоперация модерация дискредитация армии",
                "globalvoices российская пропаганда новояз война",
                "svoboda.org военная цензура год",
            ],
            "urls": [
                "https://ru.globalvoices.org/2023/02/06/114977/",
                "https://ru.wikipedia.org/wiki/Цензура_в_России_во_время_вторжения_на_Украину",
                "https://www.svoboda.org/a/32293987.html",
                "https://praguesupport.com/wp-content/uploads/2025/09/war-glossary_full-version_for-printing_13092025.pdf",
                "https://ru.ruwiki.ru/wiki/Жаргон_участников_СВО",
            ],
            "sources": ["web_war_glossary_ru.txt", "web_dfrlab_rkn_tags.txt", "kugimiya_banlist.yaml"],
            "section": "war/SVO/Ukraine",
            "notes": "Нет публичного RU stop-list от РКН. Prague Support war glossary (~500+ RU/UA slang pairs) + DFRLab/iStories Vepr tags — основной массив. FP: «спецоперация» медицинская.",
        },
        {
            "name": "3. Ukraine conflict",
            "queries": [
                "украина модерация telegram бандера сленг термины",
                "неонацизм украина термины русский словарь",
                "бандерівці wikipedia propaganda",
                "OPORA насильницька риторика telegram",
                "vk habr фильтр враждебных высказываний",
            ],
            "urls": [
                "https://uk.wikipedia.org/wiki/бандерівці",
                "https://oporaua.org/viyna/nasil-nic-ka-ritorika-v-ukrayins-komu-segmenti-telegram-final-niy-zvit-26048",
                "https://habr.com/ru/companies/vk/articles/546186/",
                "https://github.com/hse-scila/ethnohate-project",
            ],
            "sources": ["web_war_glossary_ru.txt", "web_hate_speech.txt", "vsecoder_make_multilabel.py", "hurtlex_ru_12.tsv"],
            "section": "war/SVO/Ukraine",
            "notes": "Этнические слаги (хохол, ватник, колорад) — высокий FP в нейтральном контексте; только hate_speech секция. OPORA — датасет риторики, не wordlist.",
        },
        {
            "name": "4. Drones / rockets / explosions",
            "queries": [
                "бпла дрон террор взрывчатка сленг русский",
                "теракт терминология русский словарь модерация",
                "war glossary fpv камикадзе шахед",
                "rub-in.ru угроза бпла терроризм дронов",
                "kuban24 птичник бпла сво",
            ],
            "urls": [
                "https://praguesupport.com/wp-content/uploads/2025/09/war-glossary_full-version_for-printing_13092025.pdf",
                "https://www.rub-in.ru/news/novye-realnosti-terrorizm-ugrozy-bpla-i-nashi-deti-pora-reshat/",
                "https://kuban24.tv/item/tonkosti-upravleniya-dronami-na-svo-kto-takoj-ptichnik-i-chem-razlichayutsya-bpla",
                "https://ukodeksrf.ru/ch-2/rzd-9/gl-24/st-205-uk-rf",
            ],
            "sources": ["web_weapons_drones.txt", "web_war_glossary_ru.txt", "krugozor_stopwords.php"],
            "section": "weapons/explosives/drones",
            "notes": "War glossary даёт 80+ drone/bomb tokens. ContentShield RU (404 на raw) — не извлечён. FP: дрон-доставка, космическая ракета.",
        },
        {
            "name": "5. Protests / meetings",
            "queries": [
                "митинг протест запрещённые слова несанкционированный митинг",
                "пикетирование модерация стоп слова россия",
                "54-ФЗ публичное мероприятие уведомление",
                "20.2 КоАП митинг демонстрация",
                "istories vepr protest moods monitoring",
            ],
            "urls": [
                "https://www.consultant.ru/document/cons_doc_LAW_48103/",
                "https://www.consultant.ru/document/cons_doc_LAW_34661/c77bf52af28dfd8f9de192b9faf0999c023256d2/",
                "https://istories.media/en/stories/2023/02/08/inside-the-censorship-machine/",
                "https://habr.com/ru/articles/384021/",
            ],
            "sources": ["web_protests_legal.txt", "web_dfrlab_rkn_tags.txt", "kugimiya_banlist.yaml"],
            "section": "protests/political actions",
            "notes": "Закон не публикует banned words — только legal terms + incitement phrases. RKN мониторит «призывы к протесту» как тег.",
        },
        {
            "name": "6. Police / siloviki",
            "queries": [
                "мусора сленг полиция омон росгвардия жаргон",
                "силовики оскорбления словарь россия",
                "cyberleninka оскорбление представителей власти мусор мент",
                "politicwar.ru силовики политсленг",
                "molomo.ru мусор сленг",
            ],
            "urls": [
                "https://www.eg.ru/culture/500105-pochemu-policeyskih-nazyvayut-musorami-i-legavymi/",
                "https://cyberleninka.ru/article/n/ob-uchastii-lingvista-v-sudebnyh-zasedaniyah-po-delam-ob-oskorblenii-predstaviteley-vlasti",
                "http://www.politicwar.ru/politika/266249.html",
                "https://www.molomo.ru/sleng-m/musor",
            ],
            "sources": ["web_police_slang.txt", "kugimiya_banlist.yaml"],
            "section": "law enforcement (slang)",
            "notes": "«мусор» — омоним с waste management (context_required). ACAB/околофутбол — protest subculture.",
        },
        {
            "name": "7. Political figures / titles",
            "queries": [
                "путин зеленский модерация блок оскорбления словарь",
                "istories oculus insult president photoshop dictionary",
                "unian путин зеленский риторика",
                "videocensor api insults extremism categories",
                "kugimiya banlist путин зеленск",
            ],
            "urls": [
                "https://istories.media/en/stories/2023/02/08/inside-the-censorship-machine/",
                "https://www.unian.net/world/vladimir-putin-rezko-izmenil-ton-upominaya-zelenskogo-13377765.html",
                "https://videocensor.ru/developers/docs",
                "https://citizenlab.ca/research/an-analysis-of-in-platform-censorship-on-russias-vkontakte/",
            ],
            "sources": ["web_political_figures.txt", "web_dfrlab_rkn_tags.txt", "kugimiya_banlist.yaml"],
            "section": "political figures/titles",
            "notes": "RKN Oculus dictionary: insults comparing Putin to Hitler/dictator/traitor. FP: «президент компании».",
        },
        {
            "name": "8. Racism / hate speech RU",
            "queries": [
                "hate speech русский словарь github этнические оскорбления",
                "xenophobia lexicon russian RuEthnoHate dataset",
                "hurtlex PS category russian",
                "vsecoder IDENTITY rules github",
                "habr vk токсичность protected identities",
            ],
            "urls": [
                "https://github.com/hse-scila/ethnohate-project",
                "https://github.com/valeriobasile/hurtlex/tree/master/lexica/RU/1.2",
                "https://github.com/vsecoder/ru-toxic-messages-classification",
                "https://habr.com/ru/companies/vk/articles/546186/",
                "https://scila.hse.ru/ethnohate",
            ],
            "sources": ["web_hate_speech.txt", "hurtlex_ru_12.tsv", "vsecoder_make_multilabel.py"],
            "section": "hate speech / ethnic slurs",
            "notes": "RuEthnoHate — annotated texts, не static list. Hurtlex PS + vsecoder IDENTITY дали основную массу. bars38/ContentShield — 404 при fetch.",
        },
        {
            "name": "9. Islam / religious extremism",
            "queries": [
                "исламизм экстремизм термины русский словарь",
                "mediascope исламизм ваххабизм экстремизм синонимы",
                "wikipedia исламизм политический ислам",
                "security.urfu ваххабиты джихадист",
                "bigenc.ru исламское государство игил",
            ],
            "urls": [
                "http://www.mediascope.ru/node/2081",
                "https://ru.wikipedia.org/wiki/Исламизм",
                "https://security.urfu.ru/ru/protivodeistvie-ehkstremizmu-i-terrorizmu/osnovnye-terminy-i-opredelenija/",
                "https://bigenc.ru/c/islamskoe-gosudarstvo-bf9101",
            ],
            "sources": ["web_islamism_terms.txt", "web_terrorism_urfu.txt", "krugozor_stopwords.php"],
            "section": "terrorism/extremism",
            "notes": "Религия (ислам, мусульманин, коран) намеренно исключена. Mediascope: исламизм ≠ экстремизм синонимы.",
        },
        {
            "name": "10. Torture / violence",
            "queries": [
                "пытки термины насилие словарь угроз русский",
                "hurtlex RE category russian",
                "vsecoder THREAT rules github",
                "ukodeksrf статья 205 террористический акт",
                "law.niv.ru пытка определение",
            ],
            "urls": [
                "https://github.com/valeriobasile/hurtlex/tree/master/lexica/RU/1.2",
                "https://github.com/vsecoder/ru-toxic-messages-classification",
                "https://law.niv.ru/doc/dictionary/large-legal/articles/839/pytka.htm",
                "https://ukodeksrf.ru/ch-2/rzd-9/gl-24/st-205-uk-rf",
            ],
            "sources": ["web_torture_violence.txt", "hurtlex_ru_12.tsv", "vsecoder_make_multilabel.py"],
            "section": "torture/violence verbs",
            "notes": "Hurtlex RE много юридических FP (Пират, шалунья) — отфильтровано is_valid_token. vsecoder threat directional требует 2-е лицо.",
        },
    ]

    for report in topic_reports:
        section = report["section"]
        count = token_counts.get(section, 0)
        lines.extend([
            f"## {report['name']}",
            "",
            f"**Токенов в секции:** {count}",
            "",
            "### WebSearch queries",
        ])
        for q in report["queries"]:
            lines.append(f"- `{q}`")
        lines.extend(["", "### Source URLs"])
        for u in report["urls"]:
            lines.append(f"- {u}")
        lines.extend(["", "### Local extracts"])
        for s in report["sources"]:
            c = source_counts.get(s, "—")
            lines.append(f"- `{s}` — {c} raw lines/terms")
        lines.extend(["", f"**Quality notes:** {report['notes']}", "", "---", ""])

    lines.extend([
        "## Tokens vs regex patterns",
        "",
        "**Токены** (`candidates_violence.txt`) — точное совпадение слов/лемм для wordlist merge.",
        "**Regex** (`candidates_violence_regex.txt`) — фрагменты из vsecoder THREAT/IDENTITY",
        "с классами символов (`[аеуо]`, `?`, `\\s`) — только для phrase-engine, не в stop-list.",
        "Примеры: `ватн[аеуо][^_]` (варианты «ватник»), `чурк[аиое]` (склонения),",
        "`оторв[уе]м?\\s` (угроза «оторвём»). Артефакты вроде `деhumanизация` и bidi-`пытка`",
        "отфильтрованы; чистый токен `пытка` остаётся в torture-секции.",
        "",
        "## Additional cross-topic sources",
        "",
        "| Source | URL | License | Est. terms | Extracted |",
        "|--------|-----|---------|------------|-----------|",
        f"| hurtlex RU 1.2 | https://github.com/valeriobasile/hurtlex | Academic | ~4679 | {source_counts.get('hurtlex_ru_12.tsv', 0)} RE+PS |",
        f"| vsecoder THREAT/IDENTITY | https://github.com/vsecoder/ru-toxic-messages-classification | MIT | ~40 patterns | {source_counts.get('vsecoder_make_multilabel.py', 0)} |",
        f"| Krugozor extremism | vendored PHP | No LICENSE | ~40 | {source_counts.get('krugozor_stopwords.php', 0)} |",
        f"| kugimiya banlist | vendored YAML | — | ~200 roots | {source_counts.get('kugimiya_banlist.yaml', 0)} |",
        "| ContentShield RU | https://github.com/ZachHandley/ContentShield | Check repo | ~215 | **FAILED 404** |",
        "| bars38 RU ban | https://github.com/bars38/Russian_ban_words | — | ~1316 | **FAILED 404** |",
        "| LDNOOBW V2 RU | https://github.com/LDNOOBWV2/ | Open | 4948 | skipped (profanity dup) |",
        "| TextDetox lexicon | HuggingFace | openrail++ | 140k | skipped (not violence) |",
        "| RuEthnoHate | HSE GitHub | Research | 5.5k texts | skipped (dataset not list) |",
        "| Citizen Lab VK | citizenlab.ca 2023/2025 | Research | LGBTIQ keywords | not violence-specific |",
        "",
        "## Honest gaps",
        "",
        "- Нет единого open-source **Russian violence wordlist** уровня profanity.",
        "- ContentShield/bars38 raw fetch failed (repo paths changed).",
        "- RKN/MinJust публикуют **материалы/теги**, не готовые stop-lists.",
        "- War glossary сильно UA/RU mixed — курация на RU-only tokens.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    bucket, regex_bucket, source_counts, phrases = collect_all()
    token_counts = write_tokens(OUT_TOKENS, bucket)
    regex_count = write_regex(OUT_REGEX, regex_bucket)
    phrase_count = write_phrases(OUT_PHRASES, phrases)
    context_count = write_context(OUT_CONTEXT)
    write_topics_report(OUT_TOPICS, bucket, source_counts, phrase_count, token_counts)

    stats = {
        "source_line_counts": source_counts,
        "token_counts_by_section": token_counts,
        "total_unique_tokens": sum(token_counts.values()),
        "regex_patterns": regex_count,
        "phrases": phrase_count,
        "context_required": context_count,
        "skip": len(SKIP_PHRASES),
        "exclude_terms": len(exclude_terms()),
        "web_source_files": list(WEB_SOURCE_ROUTES.keys()),
    }
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
