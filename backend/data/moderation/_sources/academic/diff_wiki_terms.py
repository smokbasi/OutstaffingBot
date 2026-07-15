#!/usr/bin/env python3
"""Diff Wikipedia-style narcotics slang paste against moderation wordlists.

Usage:
    python backend/data/moderation/_sources/academic/diff_wiki_terms.py
    python backend/data/moderation/_sources/academic/diff_wiki_terms.py --raw path/to/wiki_slang_raw.txt
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MOD_DIR = BASE_DIR.parent.parent
DEFAULT_RAW = BASE_DIR / "wiki_slang_raw.txt"
DEFAULT_OUT = BASE_DIR / "wiki_terms_new.txt"

_BW_PATH = MOD_DIR / "build_wordlists.py"
_spec = importlib.util.spec_from_file_location("build_wordlists", _BW_PATH)
assert _spec and _spec.loader
_bw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bw)

norm = _bw.norm
is_valid_term = _bw.is_valid_term
EXCLUDE_FALSE_POSITIVES = _bw.EXCLUDE_FALSE_POSITIVES
classify = _bw.classify
DRUG_STEMS = _bw.DRUG_STEMS
SEX_STEMS = _bw.SEX_STEMS

WORDLIST_FILES = (
    "stop_words_drugs.txt",
    "stop_words_slang_manual.txt",
    "stop_words_sex.txt",
    "stop_words_profanity.txt",
    "stop_words_translit.txt",
    "context_required.txt",
)

# Section headers / prose — not slang headwords
SECTION_HEADER_RE = re.compile(
    r"^(?:"
    r"Формы\s+наркотических|Приготовление\s+наркотиков|Приспособления(?:\s+для\s+употребления)?|"
    r"Действия(?:\s+по\s+употреблению)?|Компоненты|Ингредиенты\s+марихуаны|"
    r"Общие|Курение|Инъекции|Другие\s+виды|Курительные\s+устройства|Самокрутки|"
    r"Внутривенное\s+введение|Распространение\s+наркотиков|Продавцы|Посредники|"
    r"Пункты\s+торговли|Виды\s+деятельности|Обозначение\s+самих|"
    r"Состояния\s+наркотического|Анатомические\s+термины|Прочее"
    r")",
    re.IGNORECASE,
)

DESCRIPTION_DRUG_RE = re.compile(
    r"^(?:"
    r"амфетамин|марихуан|гашиш|героин|кокаин|кетамин|морфин|опи|"
    r"экстаз|лсд|lsd|dxm|метамфетамин|первитин|эфедрин|кодеин|"
    r"мефедрон|дезоморфин|дифенгидрамин|барбитурат|каннаб|"
    r"опиат|стимулятор|диссоциатив|галлюциноген|психоделик|"
    r"наркотик|психоактив|психотроп|запрещ"
    r")",
    re.IGNORECASE,
)

SKIP_TERM_RE = re.compile(
    r"^(?:"
    r"также\s+названия|употребляемые|преимущественно|на\s+лебедюхе|"
    r"проверь\s+все\s+термины|описание\s+убери"
    r")",
    re.IGNORECASE,
)

FOOTNOTE_RE = re.compile(r"\[\d+\]")
PARENS_RE = re.compile(r"\([^)]*\)")
QUOTED_RE = re.compile(r"[«\"']([^»\"']+)[»\"']")
CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
PHRASE_FRAGMENT_START = re.compile(
    r"^(?:обознач|бывает|после|перед|что|кто|если|когда|немного|"
    r"параллельно|исто|мысл|действ|вызыва|пренеб|«|'|"
    r"возникающ|обычно|необязательно|минимальное|посредник|"
    r"постоянное|желание|сильное|размером|разновидност)",
    re.IGNORECASE,
)
LATIN_CODE_RE = re.compile(r"\b(jwh-\d{2,4}|dxm|lsd-?\d{0,3}|mdma|pcp)\b", re.IGNORECASE)
LATIN_TOKEN_RE = re.compile(r"^[a-z][a-z0-9\-]{0,14}$", re.IGNORECASE)


def strip_accents(text: str) -> str:
    """Remove stress marks (U+0301 etc.) without NFD — NFD splits Cyrillic «й» into «и»+breve."""
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def normalize_wiki_term(raw: str) -> str:
    s = strip_accents(raw.strip())
    s = FOOTNOTE_RE.sub("", s)
    s = PARENS_RE.sub("", s)
    s = s.strip(" \t«»\"'.,;:")
    s = re.sub(r"\s+", " ", s)
    return norm(s)


def term_variants(term: str) -> set[str]:
    t = normalize_wiki_term(term)
    variants = {t}
    if not t:
        return variants
    variants.add(t.replace("-", " "))
    variants.add(t.replace(" ", "-"))
    if "-" in t:
        for part in t.split("-"):
            if len(part) >= 2:
                variants.add(part)
    return {v for v in variants if v}


def load_wordlists() -> tuple[set[str], set[str], dict[str, str]]:
    """Return (block_terms, context_required, source_map)."""
    block: set[str] = set()
    context: set[str] = set()
    source: dict[str, str] = {}

    for name in WORDLIST_FILES:
        path = MOD_DIR / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.split("#", 1)[0].strip()
            if not raw:
                continue
            t = norm(raw)
            if name == "context_required.txt":
                context.add(t)
            else:
                block.add(t)
            source.setdefault(t, name)

    for t in EXCLUDE_FALSE_POSITIVES:
        block.add(t)
        source.setdefault(t, "EXCLUDE_FALSE_POSITIVES")

    return block, context, source


def build_lemma_index(block_terms: set[str]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    try:
        from pymorphy3 import MorphAnalyzer

        morph = MorphAnalyzer()
    except Exception:
        return index

    for term in block_terms:
        if " " in term or not CYRILLIC_RE.search(term):
            continue
        try:
            parsed = morph.parse(term)
            if parsed:
                lemma = norm(parsed[0].normal_form)
                index.setdefault(lemma, set()).add(term)
        except Exception:
            pass
    return index


def is_covered(
    term: str,
    *,
    block: set[str],
    context: set[str],
    lemma_index: dict[str, set[str]],
) -> tuple[bool, str]:
    """Return (covered, reason)."""
    for variant in term_variants(term):
        if variant in block:
            return True, f"exact:{variant}"
        if variant in context:
            return True, f"context_required:{variant}"
        if variant in EXCLUDE_FALSE_POSITIVES:
            return True, f"EXCLUDE:{variant}"

    t = normalize_wiki_term(term)
    if t in block or t in context or t in EXCLUDE_FALSE_POSITIVES:
        return True, "exact"

    try:
        from pymorphy3 import MorphAnalyzer

        morph = MorphAnalyzer()
        if CYRILLIC_RE.search(t) and " " not in t and len(t) >= 3:
            parsed = morph.parse(t)
            if parsed:
                lemma = norm(parsed[0].normal_form)
                if lemma in block:
                    return True, f"lemma:{lemma}"
                if lemma in context:
                    return True, f"context_required_lemma:{lemma}"
                if lemma in lemma_index:
                    return True, f"lemma_index:{next(iter(lemma_index[lemma]))}"
    except Exception:
        pass

    return False, ""


def is_section_header(line: str) -> bool:
    stripped = line.strip()
    if not stripped or " — " in stripped or " – " in stripped:
        return False
    if SECTION_HEADER_RE.match(stripped):
        return True
    if (
        len(stripped) < 90
        and stripped[0].isupper()
        and "," not in stripped
        and not re.search(r"\[\d+\]", stripped)
        and any(
            kw in stripped.lower()
            for kw in (
                "наркотик",
                "запрещ",
                "употреблен",
                "распростран",
                "состояни",
                "термин",
                "деятельност",
            )
        )
    ):
        return True
    return False


def is_valid_wiki_term(term: str) -> bool:
    t = normalize_wiki_term(term)
    if not t or len(t) < 2 or len(t) > 80 or t.startswith("//"):
        return False
    if re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,24}", t):
        return True
    return is_valid_term(t)


def is_garbage_phrase(phrase: str) -> bool:
    t = normalize_wiki_term(phrase)
    if len(t.split()) > 5:
        return True
    if re.search(r"\s-\s", t) and len(t) > 18:
        return True
    if t.startswith(("№", "второй и", "обычно ", "необязательно ")):
        return True
    return bool(PHRASE_FRAGMENT_START.match(t))


def is_definition_tail(segment: str) -> bool:
    s = segment.strip().rstrip(".")
    if DESCRIPTION_DRUG_RE.match(s):
        return True
    words = s.split()
    return len(words) <= 4 and len(s) < 36 and "," not in s and bool(words) and words[0][0].isupper()


def is_description_segment(segment: str) -> bool:
    s = segment.strip()
    if len(s) > 120:
        return True
    if DESCRIPTION_DRUG_RE.match(s):
        return True
    low = s.lower()
    if low.startswith(("смесь ", "общее ", "состояние ", "процесс ", "метод ", "человек, ", "находящ")):
        return True
    if s.count(" ") > 12:
        return True
    return False


def clean_term_piece(piece: str) -> str:
    piece = piece.strip()
    piece = FOOTNOTE_RE.sub("", piece)
    piece = re.sub(r"^\d+\.\s*", "", piece)
    piece = piece.strip(" .;")
    return piece


def split_term_list(payload: str) -> list[str]:
    """Split comma-separated headwords; preserve multi-word phrases."""
    payload = clean_term_piece(payload)
    if not payload or SKIP_TERM_RE.match(payload):
        return []

    terms: list[str] = []
    for chunk in re.split(r",\s*", payload):
        chunk = clean_term_piece(chunk)
        if not chunk:
            continue
        # Inline parenthetical strip already done in normalize; strip here too
        chunk = PARENS_RE.sub("", chunk).strip()
        chunk = re.sub(r"\s+", " ", chunk)
        if not chunk or SKIP_TERM_RE.match(chunk):
            continue
        if len(chunk) > 80:
            continue
        terms.append(chunk)

    for match in QUOTED_RE.finditer(payload):
        inner = clean_term_piece(match.group(1))
        if inner:
            terms.append(inner)

    return terms


def extract_terms_from_line(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("http"):
        return []
    if is_section_header(stripped):
        return []
    if re.match(r"^(?:Проверь|описание\s+убери)", stripped, re.I):
        return []

    if " — " in stripped or " – " in stripped:
        parts = re.split(r"\s*(?:—|–)\s*", stripped)
        if len(parts) == 2:
            term_segments = [parts[0]] if not is_description_segment(parts[0]) else []
        elif len(parts) > 2 and is_definition_tail(parts[-1]):
            term_segments = [p for p in parts[:-1] if not is_description_segment(p)]
        else:
            term_segments = [parts[0]] if not is_description_segment(parts[0]) else []
    else:
        # No dash — skip prose / headers
        if "," in stripped and len(stripped) < 180:
            term_segments = [stripped]
        else:
            return []

    out: list[str] = []
    for segment in term_segments:
        # Truncate at sentence boundary inside long segments
        segment = re.split(r"\.\s+(?=[А-ЯA-Z])", segment, maxsplit=1)[0]
        out.extend(split_term_list(segment))
    for code in LATIN_CODE_RE.findall(stripped):
        out.append(code)
    return out


def suggest_category(term: str) -> str:
    t = normalize_wiki_term(term)
    if not t:
        return "skip"
    if t in EXCLUDE_FALSE_POSITIVES:
        return "skip-homonym"
    if " " in t:
        if is_garbage_phrase(t):
            return "skip"
        if classify(t) == "sex" or any(st in t for st in SEX_STEMS):
            return "sex"
        return "phrase"
    if LATIN_TOKEN_RE.match(t) and not CYRILLIC_RE.search(t):
        return "translit"
    cat = classify(t)
    if cat == "sex":
        return "sex"
    if cat == "drugs":
        return "drugs"
    if cat == "translit":
        return "translit"
    if cat == "profanity":
        return "drugs"  # still block-worthy; group with drugs for review
    # Wiki drug dictionary default
    if CYRILLIC_RE.search(t):
        return "drugs"
    return "translit"


def parse_wiki_text(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for line in text.splitlines():
        for raw in extract_terms_from_line(line):
            n = normalize_wiki_term(raw)
            if not n or not is_valid_wiki_term(n):
                continue
            if " " in n and is_garbage_phrase(n):
                continue
            if n in seen:
                continue
            seen.add(n)
            ordered.append(raw.strip())
    return ordered


def format_output(
    *,
    extracted: list[str],
    new_terms: list[tuple[str, str]],
    covered_count: int,
    flags: dict[str, list[str]],
) -> str:
    lines: list[str] = []
    lines.append("# Wikipedia narcotics slang diff")
    lines.append(f"# extracted_total={len(extracted)}")
    lines.append(f"# already_covered={covered_count}")
    lines.append(f"# new_only={len(new_terms)}")
    lines.append("")

    if flags.get("exclude_fp"):
        lines.append("## FLAGS — не добавлять / EXCLUDE_FALSE_POSITIVES")
        for t in sorted(flags["exclude_fp"]):
            lines.append(f"{t}  # EXCLUDE")
        lines.append("")

    if flags.get("context_block"):
        lines.append("## FLAGS — уже в block-листах (были context_required)")
        for t, reason in sorted(flags["context_block"]):
            lines.append(f"{t}  # {reason}")
        lines.append("")

    if flags.get("context_only"):
        lines.append("## FLAGS — только context_required (не block)")
        for t in sorted(flags["context_only"]):
            lines.append(f"{t}  # context_required")
        lines.append("")

    by_cat: dict[str, list[str]] = {}
    for raw, cat in new_terms:
        by_cat.setdefault(cat, []).append(normalize_wiki_term(raw))

    cat_order = ("drugs", "phrase", "translit", "sex", "skip-homonym")
    for cat in cat_order:
        items = sorted(set(by_cat.get(cat, [])))
        if not items:
            continue
        lines.append(f"## NEW — {cat} ({len(items)})")
        for t in items:
            lines.append(t)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff wiki slang paste vs wordlists")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.raw.exists():
        print(f"Missing raw file: {args.raw}", file=sys.stderr)
        return 1

    text = args.raw.read_text(encoding="utf-8", errors="replace")
    extracted = parse_wiki_text(text)
    block, context, _sources = load_wordlists()
    lemma_index = build_lemma_index(block)

    new_terms: list[tuple[str, str]] = []
    covered_count = 0
    flags: dict[str, list] = {
        "exclude_fp": [],
        "context_block": [],
        "context_only": [],
    }

    context_moved_to_block = {"герыч", "шишки", "шишка"}

    for raw in extracted:
        n = normalize_wiki_term(raw)
        covered, reason = is_covered(raw, block=block, context=context, lemma_index=lemma_index)

        if n in EXCLUDE_FALSE_POSITIVES:
            flags["exclude_fp"].append(n)

        if n in context_moved_to_block or any(
            normalize_wiki_term(v) in block for v in term_variants(raw) if normalize_wiki_term(v) in context_moved_to_block
        ):
            if covered and ("герыч" in reason or "шиш" in reason or n in block):
                flags["context_block"].append((n, reason))

        if not covered and n in context:
            flags["context_only"].append(n)

        if covered:
            covered_count += 1
            continue

        cat = suggest_category(raw)
        if cat == "skip-homonym":
            flags["exclude_fp"].append(n)
            continue

        new_terms.append((raw, cat))

    flags["exclude_fp"] = sorted(set(flags["exclude_fp"]))
    flags["context_only"] = sorted(set(flags["context_only"]))

    output = format_output(
        extracted=extracted,
        new_terms=new_terms,
        covered_count=covered_count,
        flags=flags,
    )
    args.out.write_text(output, encoding="utf-8")

    print(f"extracted={len(extracted)} covered={covered_count} new={len(new_terms)}")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
