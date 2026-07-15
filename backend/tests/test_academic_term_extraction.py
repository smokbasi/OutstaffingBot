"""Smoke and unit tests for academic moderation term extraction (Phase 9.3)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ACADEMIC_DIR = BACKEND_ROOT / "data" / "moderation" / "_sources" / "academic"
MOD_DIR = BACKEND_ROOT / "data" / "moderation"
EXTRACT_SCRIPT = ACADEMIC_DIR / "extract_terms.py"
EXTRACTED_DIR = ACADEMIC_DIR / "extracted"

OUTPUT_FILES = (
    "candidates_phrases.txt",
    "candidates_tokens.txt",
    "candidates_context_required.txt",
    "extraction_stats.json",
)

UMK_SEX_FOOTNOTES = (
    "грелка",
    "мочалка",
    "домохозяйка",
    "институтка",
    "прокурсетка",
    "липучка",
    "легкотрудница",
)

UMK_CONTEXT_HOMONYMS = frozenset({"грелка", "мочалка", "домохозяйка", "липучка"})

ABANNET_DRUG_SAMPLES = (
    "автопилот",
    "абстяга",
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _norm(term: str) -> str:
    return term.strip().lower().replace("ё", "е")


def _load_terms(path: Path) -> list[str]:
    terms: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        terms.append(_norm(line.split("#", 1)[0].strip()))
    return terms


@pytest.fixture(scope="module")
def extract_mod():
    return _load_module("academic_extract_terms", EXTRACT_SCRIPT)


@pytest.fixture(scope="module")
def build_mod():
    return _load_module("build_wordlists", MOD_DIR / "build_wordlists.py")


def test_parse_umk_footnote_slang(extract_mod) -> None:
    text = extract_mod.read_source_text(ACADEMIC_DIR / "txt" / "umk_dembska.txt")
    parsed = {_norm(t): h for t, h in extract_mod.extract_umk_footnote_terms(text)}
    for word in UMK_SEX_FOOTNOTES:
        assert word in parsed, f"missing UMK footnote term {word!r}"
        assert parsed[word] == "sex"


def test_umk_homonyms_classify_to_context(extract_mod) -> None:
    for word in UMK_CONTEXT_HOMONYMS:
        assert extract_mod.is_context_required(word)
        assert word in extract_mod.CONTEXT_REQUIRED_REASONS


def test_sex_stem_classification(build_mod, extract_mod) -> None:
    for word in ("прокурсетка", "институтка", "легкотрудница"):
        assert build_mod.classify(extract_mod.norm(word)) == "sex"
        assert extract_mod.classify_term(word, None) == "sex"


def test_abannet_drug_terms_classify(build_mod, extract_mod) -> None:
    text = extract_mod.read_source_text(ACADEMIC_DIR / "txt" / "abannet_narcotics.txt")
    parsed = dict(extract_mod.parse_abannet(text))
    for word in ABANNET_DRUG_SAMPLES:
        assert word in parsed or _norm(word) in {_norm(k) for k in parsed}, f"missing {word!r}"
        cat = extract_mod.classify_term(_norm(word), parsed.get(word) or parsed.get(_norm(word)))
        assert cat == "drugs", f"{word!r} -> {cat!r}"


def test_abannet_unclassified_materially_reduced(extract_mod) -> None:
    text = extract_mod.read_source_text(ACADEMIC_DIR / "txt" / "abannet_narcotics.txt")
    existing = extract_mod.load_existing_wordlists()
    unclassified = 0
    for term, hint in extract_mod.parse_abannet(text):
        t = _norm(term)
        if not extract_mod.is_valid_term(t) or t in existing:
            continue
        cat = extract_mod.classify_term(t, hint)
        if cat is None:
            unclassified += 1
            continue
        if " " in t and not extract_mod.is_valid_phrase(t, hint):
            unclassified += 1
    assert unclassified < 200, f"expected <200 abannet unclassified, got {unclassified}"


def test_extract_script_runs_and_writes_outputs() -> None:
    result = subprocess.run(
        [sys.executable, str(EXTRACT_SCRIPT)],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    for name in OUTPUT_FILES:
        assert (EXTRACTED_DIR / name).exists(), f"missing {name}"


def test_output_files_have_no_internal_duplicates() -> None:
    for name in OUTPUT_FILES:
        if not name.endswith(".txt"):
            continue
        terms = _load_terms(EXTRACTED_DIR / name)
        assert len(terms) == len(set(terms)), f"duplicate terms in {name}"


def test_context_file_does_not_overlap_phrases() -> None:
    phrases = set(_load_terms(EXTRACTED_DIR / "candidates_phrases.txt"))
    context = set(_load_terms(EXTRACTED_DIR / "candidates_context_required.txt"))
    overlap = phrases & context
    assert not overlap, f"context/phrases overlap: {sorted(overlap)[:10]}"


def test_extraction_stats_structure() -> None:
    stats = json.loads((EXTRACTED_DIR / "extraction_stats.json").read_text(encoding="utf-8"))
    assert "totals" in stats
    assert "skipped" in stats
    assert stats["totals"]["phrases"] >= 0
    assert stats["skipped"]["duplicates_in_existing_wordlists"] >= 0
    assert stats["skipped"]["unclassified"] < 557


def test_umk_terms_in_extracted_outputs() -> None:
    tokens = _load_terms(EXTRACTED_DIR / "candidates_tokens.txt")
    context = _load_terms(EXTRACTED_DIR / "candidates_context_required.txt")
    curated_sex_path = ACADEMIC_DIR / "curated" / "curated_sex.txt"
    merged_sex_path = MOD_DIR / "stop_words_sex.txt"
    merged_sex = _load_terms(merged_sex_path) if merged_sex_path.is_file() else set()
    curated_sex = _load_terms(curated_sex_path) if curated_sex_path.is_file() else set()
    umk_sex = {"прокурсетка", "институтка", "легкотрудница"}
    found = (set(tokens) | set(curated_sex) | set(merged_sex)) & umk_sex
    assert found, "expected UMK sex tokens in candidates, curated, or live sex wordlist"
    for homonym in UMK_CONTEXT_HOMONYMS:
        assert homonym in context, f"{homonym!r} should be context_required"


@pytest.mark.parametrize("name", OUTPUT_FILES)
def test_output_files_exist(name: str) -> None:
    assert (EXTRACTED_DIR / name).is_file()
