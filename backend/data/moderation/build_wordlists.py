#!/usr/bin/env python3
"""Build categorized moderation wordlists from vendored sources."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "_sources"
CURATED_DIR = SRC / "academic" / "curated"
VIOLENCE_CURATED_DIR = SRC / "violence" / "curated"
OUT = ROOT

CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
LATIN_RE = re.compile(r"[a-z]", re.IGNORECASE)
WORD_IN_PHP = re.compile(r"'([^']+)'")
KUGIMIYA_LINE = re.compile(r"^\s*-\s*(.+)$")

PROFANITY_STEMS = {
    "бля", "бляд", "блять", "хуй", "хуе", "хуи", "хуя", "пизд", "пидор", "пидар", "еба", "ёба",
    "ебл", "ебан", "ебат", "ебу", "ебё", "ебо", "сука", "сук ", "муда", "мудо", "залуп",
    "манда", "жоп", "жопа", "анус", "вагин", "член", "соси", "дроч", "онан", "гандон",
    "шлюх", "простит", "fuck", "shit", "bitch", "asshole", "cunt", "dick", "cock",
    "govno", "pizd", "blyat", "suka", "mudak", "debil",
}


def norm(term: str) -> str:
    return term.strip().lower().replace("ё", "е")


def is_valid_term(term: str) -> bool:
    t = norm(term)
    if not t or len(t) < 2:
        return False
    if any(ch in t for ch in "()[]{}|^$.*+?\\"):
        return False
    if t.startswith("//"):
        return False
    # skip noisy fragments
    if len(t) > 80:
        return False
    return True


def write_list(path: Path, terms: set[str]) -> int:
    ordered = sorted(terms)
    path.write_text("\n".join(ordered) + ("\n" if ordered else ""), encoding="utf-8")
    return len(ordered)


def parse_php_words(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {norm(w) for w in WORD_IN_PHP.findall(text) if is_valid_term(w)}


def parse_krugozor_section(path: Path, start_marker: str, end_markers: tuple[str, ...]) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find(start_marker)
    if start == -1:
        return set()
    chunk = text[start:]
    end = len(chunk)
    for em in end_markers:
        pos = chunk.find(em, len(start_marker))
        if pos != -1:
            end = min(end, pos)
    chunk = chunk[:end]
    terms: set[str] = set()
    for line in chunk.splitlines():
        if line.strip().startswith("//"):
            # comma-separated slang on one line (skip section headers without quoted tokens)
            if "'" not in line:
                continue
            payload = line.split("//", 1)[1].strip()
            if payload and not payload.startswith(" "):
                for part in re.split(r"',\s*'|',\s*", payload.strip("'")):
                    part = part.strip("'\", ")
                    if is_valid_term(part):
                        terms.add(norm(part))
        for w in WORD_IN_PHP.findall(line):
            if is_valid_term(w):
                terms.add(norm(w))
    return terms


def parse_txt_lines(path: Path) -> set[str]:
    return {norm(line) for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if is_valid_term(line)}


def load_curated_manifest(name: str, *, base_dir: Path = CURATED_DIR) -> set[str]:
    """Load curated manifests (academic or violence curation output)."""
    path = base_dir / name
    if not path.exists():
        return set()
    return {
        norm(line.split("#", 1)[0].strip())
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.startswith("#") and is_valid_term(line.split("#", 1)[0].strip())
    }


def load_context_required(path: Path) -> set[str]:
    """Terms needing proximity context — never blind block."""
    if not path.exists():
        return set()
    return {
        norm(line.split("#", 1)[0].strip())
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.startswith("#") and is_valid_term(line.split("#", 1)[0].strip())
    }


def load_wiki_terms_accepted() -> dict[str, set[str]]:
    """Load wiki curation manifest (wiki_terms_accepted.txt).

    DISABLED 2026-07-09: Phase B wiki bulk rollback — terms moved to
    ``_sources/violence/candidates_*`` for user review; no auto-merge to live lists.
    """
    return {"drugs": set(), "phrases": set(), "translit": set()}


def parse_kugimiya_filtered(path: Path, stems: set[str]) -> set[str]:
    terms: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = KUGIMIYA_LINE.match(line)
        if not m:
            continue
        raw = m.group(1).strip()
        raw = re.sub(r"\(\s*\|\s*\^\)", "", raw)
        raw = re.sub(r"\(\s*\|\s*\$\)", "", raw)
        raw = re.sub(r"\[\^[^\]]+\]", "", raw)
        raw = raw.strip()
        candidates: set[str] = set()
        for chunk in re.findall(r"[a-zа-яё0-9][a-zа-яё0-9\-]{2,}", raw, flags=re.IGNORECASE):
            if is_valid_term(chunk):
                candidates.add(norm(chunk))
        for c in candidates:
            if matches_stem(c, stems):
                terms.add(c)
        # keep full pattern roots like "проститу" from regex
        if raw and not raw.startswith("(?:") and matches_stem(raw, stems):
            cleaned = re.sub(r"[^a-zа-яё0-9\- ]", "", raw, flags=re.IGNORECASE).strip()
            if is_valid_term(cleaned):
                terms.add(norm(cleaned))
    return terms


def parse_censureblock_roots(path: Path) -> set[str]:
    return {
        norm(w)
        for w in [
            "секс", "совокупление", "стriptiz", "стriptease", "трах", "отрах", "потрах",
            "эротика", "эропод", "эровидео", "извращение", "извращен", "интим", "инцест",
            "клитор", "кунилингус", "минет", "девствен", "дефлорация", "проституция",
            "проститут", "пизда", "пидор", "порево", "порно", "лесби", "хентай", "хуй",
            "шлюха", "блядь", "бляд", "жопа", "ебать", "голый", "голые", "грудь", "груди",
            "обнажен", "анус", "разврат", "насилие", "насил", "целочка", "xxx", "эскорт",
        ]
        if is_valid_term(w)
    }


def parse_hacking_buds_csv(path: Path) -> set[str]:
    terms: set[str] = set()
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reason = (row.get("Reason") or "").lower()
            phrase = norm(row.get("Phrase") or "")
            if not phrase:
                continue
            if "prostitution" not in reason and "trafficking" not in reason:
                continue
            if "ethnicity" in reason or "nationality" in reason or "transitive" in reason:
                continue
            if is_valid_term(phrase):
                terms.add(phrase)
            for word in re.findall(r"[a-zа-яё]{3,}", phrase, flags=re.IGNORECASE):
                if is_valid_term(word) and matches_stem(word, SEX_STEMS):
                    terms.add(norm(word))
    return terms


def load_badwords_py() -> set[str]:
    try:
        from badwords import ProfanityFilter

        p = ProfanityFilter()
        p.init(languages=["ru"])
        return {norm(w) for w in p.bad_words if is_valid_term(w)}
    except Exception:
        return set()


DRUG_STEMS = {
    "наркот", "амфетамин", "анаша", "гашиш", "героин", "кокаин", "кокс", "коноп",
    "марихуан", "мефедрон", "меф", "спайс", "лсд", "lsd", "mdma", "экстази",
    "опиум", "опиух", "метамфетамин", "кетамин", "метадон", "фентанил", "морфин",
    "кодеин", "трамадол", "каннабино", "психодел", "заклад", "zaklad", "кладмен",
    "клад", "барыг", "дозняк", "торч", "нарком", "наркош", "наркота",
    "абстин", "психостимул", "первитин", "эфедрон",
    "mephedrone", "mephedron", "desomorphin", "kraken", "гидра", "hydra", "blacksprut",
    "silkroad", "darknet", "даркнет", "пusher", "пушer", "легалка",
    "шмаль", "шир", "косяк", "бошк", "гандж", "травк", "марijuana",
    "cannabis", "weed", "heroin", "cocaine", "spice", "spais", "nembutal",
    "pentobarbital", "мухомор", "дезоморфин", "кrokodil", "крокодил",
    "alpha-pvp", "a-pvp", "apvp", "фен", "амф", "мдма", "экстаз",
}

VIOLENCE_STEMS = {
    "убью", "убий", "убив", "убит", "застрел", "зарез", "заруб",
    "расстрел", "придуш", "пореш", "грохн", "избью", "избив", "избит",
    "добью", "добив", "пришью", "пришиб", "проломл", "истребл",
    "сдохн", "суицид", "суизид", "самоубий", "харакири", "выпилиться",
    "эвтаназ", "задуш", "заруб", "закол", "заруб",
    "огнестрел", "травмат", "электрошокер", "шокер", "кастет", "дубинк",
    "игил", "джихад", "моджахед", "шахид", "халифат", "ваххаб",
    "свастик", "зигхайл", "зиг-хайл",
}

SEX_STEMS = {
    "проститут", "эскорт", "escort", "интим", "порно", "porn", "sex", "sexy",
    "эрот", "erot", "разврат", "шлюх", "бордел", "brothel", "call girl", "callgirl",
    "курсет", "легкотруд", "легкотрудн", "проститу", "куртизан", "институтк",
    "incall", "outcall", "webcam", "вебкам", "striptiz", "striptease", "стriptiz",
    "минет", "кунилинг", "лесби", "хентай", "hentai", "мжм", "жмж", "ммж",
    "sugar daddy", "sugardaddy", "pimp", "madam", "lot lizard", "cat house",
    "massage 18", "массаж 18", "vip девуш", "vip devush", "intim uslug", "интим услуг",
    "досуг", "индивидуал", "happy end", "проститу", "pornuha", "cybersex", "sexshop",
    "transsex", "shemale", "childporn", "pedofil", "backpage", "onlyfans", "only fans",
    "pornhub", "pornstar", "whore", "slut", "hooker", "prostitut", "bordel",
    "red light", "redlight", "incalls", "outcalls", "эromassage", "эромассаж",
}

TRANSLIT_EXPLICIT = {
    "govno", "pidor", "pizda", "pizd", "huy", "hui", "blyat", "bljat", "blat", "blyad", "bliad",
    "suka", "cyka", "syka", "ebat", "ebal", "yebat", "yeban", "zhopa", "jopa", "huilo",
    "mudak", "pizdec", "pizdets", "nahui", "nahuy", "mephedron", "mephedrone", "mefedron",
    "zakladka", "zaklad", "kladmen", "heroin", "cocaine", "cannabis", "marijuana", "fuck",
    "shit", "bitch", "whore", "slut", "porn", "porno", "sex", "sexy", "escort", "prostitute",
    "prostitut", "bordel", "brothel", "xuy", "xyi", "govno", "suck", "spice", "spais",
    "jwh",
}

LATIN_BLOCKLIST = {
    "download", "downloads", "torrent", "torrents", "video", "youtube", "yotube", "yutube",
    "rutube", "mp3", "spam", "vpn", "proxy", "casino", "mega", "empire", "versus", "omg",
    "whitehouse", "berlusconi", "incognito", "evolution", "feshop", "hansa", "monopoly",
    "nemesis", "torrez", "worldmarket", "elude", "tor2door", "desnake", "drugsrus",
    "solid", "iqos", "icos", "vape", "vaping", "torent", "rutor", "rutorka", "wayaway",
    "clearnet", "onion", "kraken", "kraken2web", "krakendarknet", "krakenonion", "kr2web",
    "2krnk", "2kraken", "shkafssylka", "torbazaw", "megadarknet", "silk-road", "alpha-bay",
    "alphabay", "dream-market", "dreammarket", "asap-market", "hydra-reborn", "hydra2",
    "hydra3", "blackmarket", "darkode", "dark0de", "darkbay", "cryptonia", "archetyp",
    "cyberden", "cannazon", "bohemia", "abacus", "ramp", "blacksprut", "silkroad",
}

SLANG_MANUAL_SEED = {
    norm(x)
    for x in [
        "косяк", "косяки", "шмаль", "заклад", "закладки", "торч", "дозняк", "барыга", "барыги",
        "vip девушки", "массаж 18", "интим услуги",
        "mephedrone", "spice", "darknet",
        "ширка", "ширки", "бошка", "бошки", "дурь", "дурман", "дурьма",
        "закладочник", "закладочница", "кладмен", "кладмены",
        "наркоша", "наркоши", "пушер", "пушеры", "легалка", "легалочка",
        "meow meow", "meowmeow", "alpha-pvp", "a-pvp", "apvp",
    ]
}

ALCOHOL_ALLOW = {
    "алкоголь", "алкогольный", "алкогольная", "алкогольное", "алкогольные",
    "бар", "бармен", "бармена", "бармену", "барменом", "бармены",
    "барная", "барный", "барное", "барные", "барменская",
    "коктейль", "коктейли", "коктейля", "коктейлем", "коктейлей",
    "вино", "вина", "вину", "вином", "винный", "винная", "винное", "винные",
    "сомелье", "винный бар", "винная карта", "алкогольное меню",
    "пиво", "пива", "пиву", "пивом", "пивной", "пивная",
    "виски", "whiskey", "whisky", "rum", "gin", "vodka", "tequila", "brandy",
    "champagne", "шампанское", "шампанск", "ликер", "ликёр", "aperitif", "digestif",
    "mixology", "mixologist", "bartender", "barista",
    "craft beer", "крафтовое пиво", "taproom", "pub", "lounge bar",
}

GLOBAL_EXCLUDE = ALCOHOL_ALLOW | {
    "special", "companion", "daddy", "entertainer", "patron", "seasoned", "stable",
    "buyer", "bottom", "black", "asian", "latino", "chinese", "vietnamese", "korean",
    "thai", "ebony", "petite", "athletic", "automatic", "new in town", "just visiting",
    "visiting", "passing through", "limited time", "рецепт", "донор", "смерть",
    "убить", "убивать", "john", "romeo", "papi", "casanova", "business manager",
    "adult", "amateur", "anal",  # anal in readme is profanity context - keep in profanity not exclude
}

# Krugozor drug slang homonyms + darknet tokens that collide with normal job ads.
# Rebuild-safe: excluded in classify() and bucket assignment.
EXCLUDE_FALSE_POSITIVES = {
    norm(x)
    for x in [
        # RU everyday / work context (Krugozor «наркоманский жаргон» homonyms)
        "план", "взбодриться", "агрегат", "болтанка", "болтушка", "варево",
        "канюля", "карбид", "кикер", "крис", "крисы",
        "кроссвордный", "кумар", "натур", "оттянуться", "пинки", "пласт",
        "подзаправиться", "расколбаситься", "стимульнуться", "треснуться", "ужалиться",
        "ускоритель", "мача", "мулька", "шала", "жмых", "брахман", "гарик",
        "марго", "вторяк", "духарь", "калики", "килики",
        # EN marketplace tokens vs normal business speech
        "asap", "onion", "ramp", "mega", "versus", "empire", "evolution", "monopoly",
        "incognito", "omg",
        # hacking-buds / escort list vs job ads
        "teen", "teens", "young", "youngs", "branding", "finesse", "quota", "purchaser",
        "seasoning",
        # Krugozor section header misparsed as term
        "наркоманский жаргон в одну строку, с разных источников",
        # badwords-py false positive: everyday RU verb «есть» (e.g. «Есть витамины»)
        "есть",
        # Krugozor «наркоманские площадки» — gambling/darknet marketplace, not drug slang
        "казино",
        # abannet dictionary homonyms — vitamins vs drug jargon
        "витамин", "витамины",
        # abannet/russki_mat everyday-word FPs (2026-07 curation cleanup)
        "парфюм", "парфюмерия", "пассажир", "пекарня", "вольт", "вольты",
        "движок", "десяток", "десятка", "крест", "кресты",
        "мультик", "мультики", "мультяшка", "мультяшки", "мультяха", "мультяхи",
        "напряжный", "напрячь", "напряг", "напряжно",
        "непонятка", "непонятки", "обезьяна", "огород", "огородник", "одеколонщик",
        "палочка", "пальма", "плановик", "плановщик", "плановый", "плановой",
        "планокеш", "планокеша", "планокишеть", "планокиша",
        "плантатор", "плантация", "пластик", "платформа", "подвиг", "поддувать",
        "подогрев", "подогреть", "подогретый", "подошва", "полина", "помидор",
        "пончик", "потолок", "праздник", "президент", "прибор", "присоска",
        "компания", "компании", "центр",
        "причиндалы", "пробка", "прогон", "продвинуть", "продвинутый", "продукт",
        "промокашка", "прорез", "прорезы", "простокваша", "пустота",
        "путешественник", "пчелка", "пыльца", "рабочка", "пятачок",
        "разведка", "разведчик", "разлом", "реактор", "резина", "резидент",
        "рекорд", "рубиновка", "ручник", "рыжик", "рыжики", "садовник", "сажать",
        "самовар", "самоварка", "самоделка", "самодуринский", "саморуб",
        "самосад", "самосадка", "самосвал", "сапог", "сапоги", "сверло",
        "свинина", "свинопас", "свиняк", "сезонник", "сенокос", "сидней",
        "сине-зеленый", "система", "скороварка", "скрипка", "случайный", "сменка",
        "сметана", "смолка", "собачка", "солома", "соломка", "сонник", "сонники",
        "сопливчик", "стакан", "стандарт", "старый", "стекло", "стекляшка",
        "стимул", "стимульный", "стимульной", "стрелка", "струна", "струнка",
        "ступенька", "ступеньки", "тарелка", "тарелки", "тарталетка", "тарталетки",
        "телега", "темнота", "температурка", "теплый",
        # wiki/academic homonyms — user curation 2026-07-09
        "абрикос", "аленка", "антенна", "аппаратура", "аптекарь", "атом", "банка",
        "барсик", "баян", "баянист", "боец", "болт", "булик", "бублики", "бумага",
        "бутылка", "валек", "варить", "вата", "весло", "виталя", "витек", "вода",
        "вулкан", "выкупить", "галя", "гараж", "гвоздь", "гильза", "гонец", "гонки",
        "грязь", "гусь", "дед", "дизель", "дима", "дома", "дрова", "зима", "знахарь",
        "камень", "инструмент", "качели", "каша", "кнопка", "ковбой", "коделак",
        "колодец", "колючий", "колючка", "компот", "контроль", "конфета", "космонавт",
        "котелок", "красный", "кратер", "крыса", "купец", "ликвид", "машина",
        "медицина", "метла", "метро", "москва", "мокрый", "мягкий", "напарить",
        "настя", "оксана", "парашют", "подзаборка", "покрышка", "свин", "свинак",
        "федя", "фрукт", "часики", "часы", "чек", "шланг",
        "забить гвоздь", "черный русский",
    ]
}


def matches_stem(term: str, stems: set[str]) -> bool:
    t = norm(term)
    return any(stem in t for stem in stems)


def is_translit(term: str) -> bool:
    t = norm(term)
    return bool(LATIN_RE.search(t)) and not bool(CYRILLIC_RE.search(t))


def is_excluded(term: str) -> bool:
    t = norm(term)
    return t in GLOBAL_EXCLUDE or t in EXCLUDE_FALSE_POSITIVES


# Inflected runtime lemmas that must not be collapsed at build time.
SKIP_BUILD_LEMMA = frozenset({"марка"})


def lemmatize_build_term(term: str, morph: object | None = None) -> str:
    """Canonicalize inflected Cyrillic tokens at build time (Phase 9.3.5)."""
    t = norm(term)
    if t in SKIP_BUILD_LEMMA:
        return t
    if " " in t or is_translit(t) or not CYRILLIC_RE.search(t) or len(t) < 4:
        return t
    try:
        if morph is None:
            from pymorphy3 import MorphAnalyzer

            morph = MorphAnalyzer()
        parsed = morph.parse(t)  # type: ignore[union-attr]
        if parsed:
            lemma = norm(parsed[0].normal_form)
            if lemma and lemma != t:
                return lemma
    except Exception:
        pass
    return t


def canonicalize_bucket(terms: set[str]) -> set[str]:
    morph = None
    try:
        from pymorphy3 import MorphAnalyzer

        morph = MorphAnalyzer()
    except Exception:
        morph = None
    canonical: set[str] = set()
    for term in terms:
        if not is_valid_term(term):
            continue
        t = norm(term)
        if " " in t or is_translit(t):
            canonical.add(t)
            continue
        canonical.add(lemmatize_build_term(t, morph))
    return canonical


def build_slang_bucket(krugozor_jargon: set[str], sex_manual: set[str]) -> set[str]:
    slang = {norm(x) for x in SLANG_MANUAL_SEED if is_valid_term(x) and not is_excluded(x)}
    for t in krugozor_jargon:
        if is_valid_term(t) and not is_excluded(t):
            slang.add(norm(t))
    for t in sex_manual:
        if is_valid_term(t) and " " in t and not is_excluded(t):
            slang.add(norm(t))
    return slang


def classify(term: str) -> str | None:
    t = norm(term)
    if not is_valid_term(t) or is_excluded(t) or t in LATIN_BLOCKLIST:
        return None
    if t in TRANSLIT_EXPLICIT or (is_translit(t) and (
        matches_stem(t, DRUG_STEMS) or matches_stem(t, SEX_STEMS) or matches_stem(t, PROFANITY_STEMS)
    )):
        return "translit"
    if matches_stem(t, SEX_STEMS):
        return "sex"
    if matches_stem(t, VIOLENCE_STEMS):
        return "violence"
    if matches_stem(t, DRUG_STEMS):
        return "drugs"
    if matches_stem(t, PROFANITY_STEMS):
        return "profanity"
    return None


def main() -> None:
    krugozor_jargon = parse_krugozor_section(
        SRC / "krugozor_stopwords.php",
        "// Наркоманский жаргон",
        ("// На это очень сильно реагирует РКН",),
    )
    krugozor_drugs = set(krugozor_jargon)
    krugozor_drugs |= parse_krugozor_section(
        SRC / "krugozor_stopwords.php",
        "// Наркоманские препараты",
        ("// Наркоманские площадки",),
    )
    krugozor_drugs |= parse_krugozor_section(
        SRC / "krugozor_stopwords.php",
        "// Наркоманские площадки",
        ("// На это очень сильно реагирует РКН",),
    )

    krugozor_sex = parse_krugozor_section(
        SRC / "krugozor_stopwords.php",
        "'мжм', 'ммж'",
        ("'амулет'",),
    )

    sources: dict[str, set[str]] = {
        "badwords_py": load_badwords_py(),
        "readme_svg": parse_txt_lines(SRC / "ru_banned_readme_svg.txt"),
        "krugozor_profanity": parse_php_words(SRC / "krugozor_profanity.php"),
        "krugozor_drugs": krugozor_drugs,
        "krugozor_sex": krugozor_sex,
        "censureblock": parse_censureblock_roots(SRC / "censureblock_ex_ussr.txt"),
        "kugimiya_sex": parse_kugimiya_filtered(SRC / "kugimiya_banlist.yaml", SEX_STEMS),
        "kugimiya_drugs": parse_kugimiya_filtered(SRC / "kugimiya_banlist.yaml", DRUG_STEMS),
        "hacking_buds": parse_hacking_buds_csv(SRC / "bad_terms_old.csv")
        | parse_hacking_buds_csv(SRC / "bad_terms.csv"),
        "drugs_manual": {
            norm(x)
            for x in [
                "закладка", "закладки", "закладку", "закладкой", "закладок", "закладочный",
                "zakladka", "zakladki", "klad", "kladm", "kladmen", "кладмен", "клад", "клады",
                "mephedrone", "mephedron", "meow meow", "meowmeow", "mefedron", "мефедрон", "меф",
                "alpha-pvp", "альфа pvp", "альфа-пвп", "a-pvp", "apvp", "амф", "амфетамин",
                "метамфетамин", "героин", "кокаин", "марихуана", "гашиш", "спайс", "спайсы",
                "лсд", "lsd", "mdma", "экстази", "кetamine", "кетамин", "фentanyl", "фентанил",
                "дезоморфин", "кrokodil", "крокодил", "бошки", "травка", "marijuana",
                "cannabis", "weed", "наркота", "наркотик", "наркотики", "закладчик", "закладчики",
                "курьер заклад", "закладочник", "закладочница",
                "ешка",  # MDMA/ecstasy slang (abannet)
                "марка", "фен", "колоться", "колиться", "укол",
            ]
        },
        "sex_manual": {
            norm(x)
            for x in [
                "досуг", "досуга", "досугом", "массаж 18+", "массаж 18", "массаж для мужчин 18",
                "vip девушки", "vip devushki", "vip girls", "vip girl", "intim uslugi", "intim usluga",
                "интим услуги", "интим услуга", "eskort", "escort service", "escort services",
                "эскорт услуги", "эскорт услуга", "индивидуалка", "индивидуалки", "индивидуалок",
                "проститутка", "проститутки", "проституток", "проституция", "call girl", "callgirl",
                "call-girl", "happy ending", "happy endings", "хэппи энд", "хэппи эндинг",
                "relax salon", "relax massazh", "erotic massage", "эротический массаж", "эромассаж",
                "tantric massage", "тантрический массаж", "striptease", "striptiz", "стриптиз",
                "стриптизерша", "стриптизёрша", "bordel", "brothel", "brothels", "бордель", "бордели",
                "pornstar", "porn star", "pornhub", "onlyfans", "only fans", "webcam model",
                "вебкам модель", "вебкам-модель", "sex worker", "sex workers", "sex work",
                "sugar daddy", "sugar baby", "sugar daddies", "incall", "outcall", "incalls", "outcalls",
                "lot lizard", "lot lizards", "red light", "redlight", "red-light district",
            ]
        },
        "translit_manual": set(TRANSLIT_EXPLICIT),
        "academic_curated_drugs": load_curated_manifest("curated_drugs.txt"),
        "academic_curated_sex": load_curated_manifest("curated_sex.txt"),
        "academic_curated_translit": load_curated_manifest("curated_translit.txt"),
        "academic_curated_phrases": load_curated_manifest("curated_phrases.txt"),
        "violence_curated_phrases": load_curated_manifest(
            "curated_violence_phrases.txt", base_dir=VIOLENCE_CURATED_DIR
        ),
    }
    wiki_accepted = load_wiki_terms_accepted()
    sources["wiki_accepted_drugs"] = wiki_accepted["drugs"]
    sources["wiki_accepted_phrases"] = wiki_accepted["phrases"]
    sources["wiki_accepted_translit"] = wiki_accepted["translit"]

    violence_live = parse_txt_lines(OUT / "stop_words_violence.txt")
    violence_curated = load_curated_manifest("curated_violence.txt", base_dir=VIOLENCE_CURATED_DIR)

    buckets: dict[str, set[str]] = {
        "profanity": set(),
        "sex": set(),
        "violence": set(violence_live) | violence_curated,
        "drugs": set(),
        "translit": set(),
    }

    # Force-assign dedicated source buckets first
    for t in (
        sources["krugozor_drugs"]
        | sources["drugs_manual"]
        | sources["kugimiya_drugs"]
        | sources["academic_curated_drugs"]
        | sources["wiki_accepted_drugs"]
    ):
        if is_valid_term(t) and not is_excluded(t):
            buckets["drugs"].add(norm(t))

    context_required = load_context_required(OUT / "context_required.txt")

    for t in (
        sources["krugozor_sex"]
        | sources["sex_manual"]
        | sources["censureblock"]
        | sources["hacking_buds"]
        | sources["kugimiya_sex"]
        | sources["academic_curated_sex"]
    ):
        if is_valid_term(t) and not is_excluded(t):
            buckets["sex"].add(norm(t))

    for t in sources["translit_manual"] | sources["academic_curated_translit"] | sources["wiki_accepted_translit"]:
        if is_valid_term(t):
            buckets["translit"].add(norm(t))

    # Classify profanity sources
    for t in sources["badwords_py"] | sources["readme_svg"] | sources["krugozor_profanity"]:
        cat = classify(t)
        if cat == "translit":
            buckets["translit"].add(norm(t))
        elif cat == "sex":
            buckets["sex"].add(norm(t))
        elif cat == "drugs":
            buckets["drugs"].add(norm(t))
        elif cat == "profanity":
            buckets["profanity"].add(norm(t))
        elif cat is None and is_valid_term(t) and not is_excluded(t):
            # readme/badwords default to profanity if from profanity lists
            buckets["profanity"].add(norm(t))

    buckets["drugs"] -= context_required
    buckets["violence"] -= context_required

    # Dedupe priority: sex > violence > drugs > translit > profanity
    assigned: set[str] = set()
    final: dict[str, set[str]] = {k: set() for k in buckets}

    for t in sorted(buckets["sex"]):
        final["sex"].add(t)
        assigned.add(t)
    for t in sorted(buckets["violence"]):
        if t not in assigned:
            final["violence"].add(t)
            assigned.add(t)
    for t in sorted(buckets["drugs"]):
        if t not in assigned:
            final["drugs"].add(t)
            assigned.add(t)
    for t in sorted(buckets["translit"]):
        if t not in assigned:
            final["translit"].add(t)
            assigned.add(t)
    for t in sorted(buckets["profanity"]):
        if t not in assigned:
            final["profanity"].add(t)

    slang_manual = build_slang_bucket(krugozor_jargon, sources["sex_manual"])
    for t in (
        sources["academic_curated_phrases"]
        | sources["wiki_accepted_phrases"]
        | sources["violence_curated_phrases"]
    ):
        if is_valid_term(t) and not is_excluded(t):
            slang_manual.add(norm(t))
    final["profanity"] = {t for t in canonicalize_bucket(final["profanity"]) if not is_excluded(t)}
    final["sex"] = {t for t in canonicalize_bucket(final["sex"]) if not is_excluded(t)}
    final["violence"] = {
        t
        for t in canonicalize_bucket(final["violence"])
        if not is_excluded(t) and t not in context_required
    }
    final["drugs"] = {
        t for t in canonicalize_bucket(final["drugs"]) if not is_excluded(t) and t not in context_required
    }

    counts = {
        "stop_words_profanity.txt": write_list(OUT / "stop_words_profanity.txt", final["profanity"]),
        "stop_words_sex.txt": write_list(OUT / "stop_words_sex.txt", final["sex"]),
        "stop_words_violence.txt": write_list(OUT / "stop_words_violence.txt", final["violence"]),
        "stop_words_drugs.txt": write_list(OUT / "stop_words_drugs.txt", final["drugs"]),
        "stop_words_translit.txt": write_list(OUT / "stop_words_translit.txt", final["translit"]),
        "allow_words_alcohol.txt": write_list(
            OUT / "allow_words_alcohol.txt",
            {norm(x) for x in ALCOHOL_ALLOW if is_valid_term(x)},
        ),
        "stop_words_slang_manual.txt": write_list(OUT / "stop_words_slang_manual.txt", slang_manual),
    }

    stats_path = OUT / "_build_stats.txt"
    lines = [f"{k}={v}" for k, v in counts.items()]
    for name, data in sources.items():
        lines.append(f"src_{name}={len(data)}")
    stats_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
