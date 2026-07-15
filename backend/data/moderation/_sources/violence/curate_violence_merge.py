#!/usr/bin/env python3
"""Merge approved violence candidates into live moderation wordlists.

Usage (from repo root):
    python backend/data/moderation/_sources/violence/curate_violence_merge.py
    python backend/data/moderation/build_wordlists.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2]
VIOLENCE_DIR = Path(__file__).resolve().parent
CURATED_DIR = VIOLENCE_DIR / "curated"

CANDIDATES_TOKENS = VIOLENCE_DIR / "candidates_violence.txt"
CANDIDATES_PHRASES = VIOLENCE_DIR / "candidates_violence_phrases.txt"
CANDIDATES_CONTEXT = VIOLENCE_DIR / "candidates_context_required.txt"
CANDIDATES_REGEX = VIOLENCE_DIR / "candidates_violence_regex.txt"

OUT_VIOLENCE = CURATED_DIR / "curated_violence.txt"
OUT_PHRASES = CURATED_DIR / "curated_violence_phrases.txt"
OUT_REGEX = MOD_DIR / "violence_regex_patterns.txt"
OUT_CONTEXT = MOD_DIR / "context_required.txt"
OUT_STATS = CURATED_DIR / "merge_stats.json"


def _load_build_helpers():
    spec = importlib.util.spec_from_file_location("build_wordlists", MOD_DIR / "build_wordlists.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load build_wordlists.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_extract_excludes() -> set[str]:
    spec = importlib.util.spec_from_file_location(
        "extract_violence_political", VIOLENCE_DIR / "extract_violence_political.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load extract_violence_political.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {mod.norm(x) for x in mod.EXCLUDE_TERMS_RAW}


def _parse_term_line(line: str, norm, is_valid_term) -> str | None:
    if not line.strip() or line.startswith("#"):
        return None
    term = norm(line.split("#", 1)[0].strip())
    if term and is_valid_term(term):
        return term
    return None


def parse_violence_token_sections(path: Path, norm, is_valid_term) -> tuple[set[str], set[str]]:
    """Return (token_terms, skip_terms) from candidates_violence.txt."""
    tokens: set[str] = set()
    skip: set[str] = set()
    mode: str | None = None

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("## tokens"):
            mode = "tokens"
            continue
        if stripped.startswith("## skip"):
            mode = "skip"
            continue
        if stripped.startswith("## "):
            continue

        term = _parse_term_line(line, norm, is_valid_term)
        if not term:
            continue
        if mode == "tokens":
            tokens.add(term)
        elif mode == "skip":
            skip.add(term)

    return tokens, skip


def load_phrase_candidates(path: Path, norm, is_valid_term) -> list[str]:
    phrases: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        term = _parse_term_line(line, norm, is_valid_term)
        if term:
            phrases.append(term)
    return phrases


def load_context_dict(path: Path, norm, is_valid_term) -> dict[str, str]:
    context: dict[str, str] = {}
    if not path.exists():
        return context
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        term_part, _, comment = line.partition("#")
        term = norm(term_part.strip())
        if term and is_valid_term(term):
            reason = comment.strip() or "ambiguous homonym"
            context[term] = reason
    return context


def load_existing_slang(norm, is_valid_term) -> set[str]:
    path = MOD_DIR / "stop_words_slang_manual.txt"
    if not path.exists():
        return set()
    return {
        term
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if (term := _parse_term_line(line, norm, is_valid_term)) is not None
    }


def load_regex_patterns(path: Path) -> list[str]:
    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if line.strip().startswith("## "):
            continue
        pattern = line.split("#", 1)[0].strip()
        if pattern:
            patterns.append(pattern)
    return patterns


def write_lines(path: Path, terms: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(terms) + ("\n" if terms else ""), encoding="utf-8")
    return len(terms)


def write_context_file(path: Path, context: dict[str, str]) -> int:
    lines = [f"{term}  # {reason}" for term, reason in sorted(context.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def main() -> int:
    bw = _load_build_helpers()
    norm = bw.norm
    is_valid_term = bw.is_valid_term
    is_excluded = bw.is_excluded

    exclude_terms = _load_extract_excludes()
    context_required = load_context_dict(OUT_CONTEXT, norm, is_valid_term)
    violence_context = load_context_dict(CANDIDATES_CONTEXT, norm, is_valid_term)
    context_required.update(violence_context)

    raw_tokens, skip_terms = parse_violence_token_sections(CANDIDATES_TOKENS, norm, is_valid_term)
    excluded_from_tokens = context_required.keys() | exclude_terms | skip_terms

    violence_tokens: list[str] = []
    rejected: dict[str, int] = {}
    for term in sorted(raw_tokens):
        if term in excluded_from_tokens:
            rejected["context_or_skip_or_exclude"] = rejected.get("context_or_skip_or_exclude", 0) + 1
            continue
        if is_excluded(term):
            rejected["global_exclude"] = rejected.get("global_exclude", 0) + 1
            continue
        violence_tokens.append(term)

    existing_slang = load_existing_slang(norm, is_valid_term)
    phrase_candidates = load_phrase_candidates(CANDIDATES_PHRASES, norm, is_valid_term)
    violence_phrases: list[str] = []
    phrases_skipped_dup = 0
    for phrase in phrase_candidates:
        if phrase in existing_slang:
            phrases_skipped_dup += 1
            continue
        if is_excluded(phrase):
            rejected["phrase_global_exclude"] = rejected.get("phrase_global_exclude", 0) + 1
            continue
        violence_phrases.append(phrase)

    regex_patterns = load_regex_patterns(CANDIDATES_REGEX)

    counts = {
        "curated_violence.txt": write_lines(OUT_VIOLENCE, violence_tokens),
        "curated_violence_phrases.txt": write_lines(OUT_PHRASES, violence_phrases),
        "violence_regex_patterns.txt": write_lines(OUT_REGEX, regex_patterns),
        "context_required.txt": write_context_file(OUT_CONTEXT, context_required),
    }

    stats = {
        "candidate_tokens_raw": len(raw_tokens),
        "candidate_phrases_raw": len(phrase_candidates),
        "candidate_context_required": len(violence_context),
        "skip_terms": len(skip_terms),
        "exclude_terms": len(exclude_terms),
        "rejected": rejected,
        "phrases_skipped_duplicate": phrases_skipped_dup,
        "merged_counts": counts,
        "context_required_total": counts["context_required.txt"],
        "regex_patterns": len(regex_patterns),
    }
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
