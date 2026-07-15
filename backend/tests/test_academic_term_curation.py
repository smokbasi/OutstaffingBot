"""Unit tests for academic candidate curation (Phase 9.3 curation)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ACADEMIC_DIR = BACKEND_ROOT / "data" / "moderation" / "_sources" / "academic"
CURATE_SCRIPT = ACADEMIC_DIR / "curate_candidates.py"
CURATED_DIR = ACADEMIC_DIR / "curated"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def curate_mod():
    return _load_module("curate_candidates", CURATE_SCRIPT)


def test_reject_ocr_mojibake(curate_mod) -> None:
    assert curate_mod.reject_drug_token("гђгѓг±гє", existing=frozenset()) == "ocr_mojibake"


def test_reject_homonym_in_context_list(curate_mod) -> None:
    assert curate_mod.reject_drug_token("кекс", existing=frozenset()) == "context_required"
    assert curate_mod.reject_drug_token("дом", existing=frozenset()) == "homonym"
    assert curate_mod.reject_drug_token("аптекарь", existing=frozenset()) in {"homonym", "excluded"}


def test_reject_inflected_verb(curate_mod) -> None:
    assert curate_mod.reject_drug_token("торчать", existing=frozenset()) == "inflected_verb"


def test_accept_known_good_slang(curate_mod) -> None:
    assert curate_mod.reject_drug_token("абстяк", existing=frozenset()) is None
    assert curate_mod.accept_drug_token("абстяк") is True
    assert curate_mod.reject_drug_token("афганка", existing=frozenset()) is None
    assert curate_mod.accept_drug_token("афганка") is True
    assert curate_mod.reject_drug_token("торчок", existing=frozenset()) is None
    assert curate_mod.accept_drug_token("торчок") is True


def test_reject_colesa_homonym(curate_mod) -> None:
    assert curate_mod.reject_drug_token("колеса", existing=frozenset()) == "homonym"
    assert curate_mod.reject_drug_token("банкир", existing=frozenset()) == "homonym"
    assert curate_mod.accept_drug_token("банкир") is False


def test_phrase_drop_garbage(curate_mod) -> None:
    assert curate_mod.reject_phrase("самодельных психостимуляторов") == "garbage_or_ambiguous"
    assert curate_mod.reject_phrase("интим услуг") == "garbage_or_ambiguous"
    assert curate_mod.reject_phrase("жрица любви") is None


def test_curate_script_runs_and_writes_manifests() -> None:
    result = subprocess.run(
        [sys.executable, str(CURATE_SCRIPT)],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    for name in (
        "curated_drugs.txt",
        "curated_sex.txt",
        "curated_phrases.txt",
        "curated_translit.txt",
        "curation_stats.json",
    ):
        assert (CURATED_DIR / name).exists(), f"missing {name}"


def test_curation_stats_has_expected_fields() -> None:
    stats = json.loads((CURATED_DIR / "curation_stats.json").read_text(encoding="utf-8"))
    assert "accepted" in stats
    assert "rejected" in stats
    assert stats["accepted"]["drugs"] >= 250
    assert stats["accepted"]["sex"] >= 4
    assert stats["accepted"]["phrases"] >= 15
    assert stats["accepted"]["translit"] >= 5
    assert stats["curated_counts"]["context_required.txt"] >= 32


def test_context_required_not_in_curated_drugs(curate_mod) -> None:
    drugs_path = CURATED_DIR / "curated_drugs.txt"
    if not drugs_path.exists():
        pytest.skip("run curate_candidates first")
    drugs = {
        line.strip().lower().replace("ё", "е")
        for line in drugs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    for homonym in ("кекс", "снег", "белый", "дурь"):
        assert homonym not in drugs


def test_stable_context_required_file_exists() -> None:
    path = BACKEND_ROOT / "data" / "moderation" / "context_required.txt"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "кекс" in text
    assert "герыч" not in text
