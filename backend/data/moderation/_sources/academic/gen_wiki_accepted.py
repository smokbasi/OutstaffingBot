#!/usr/bin/env python3
"""Generate wiki_terms_accepted.txt from wiki_terms_new.txt NEW sections.

DISABLED 2026-07-09: Phase B rollback — do not regenerate without user approval.
"""
from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent
WIKI = BASE / "wiki_terms_new.txt"
OUT = BASE / "wiki_terms_accepted.txt"


def main() -> None:
    text = WIKI.read_text(encoding="utf-8")
    section: str | None = None
    buckets: dict[str, list[str]] = {"drugs": [], "phrases": [], "translit": []}

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("## NEW"):
            if "drugs" in s:
                section = "drugs"
            elif "phrase" in s:
                section = "phrases"
            elif "translit" in s:
                section = "translit"
            else:
                section = None
            continue
        if s.startswith("#"):
            if not s.startswith("## NEW"):
                section = None
            continue
        term = s.split("#", 1)[0].strip()
        if term and section:
            buckets[section].append(term)

    lines = [
        "# wiki import manifest — accepted terms from wiki_terms_new.txt curation",
        "# Rebuild: python build_wordlists.py",
        "",
        f"## drugs ({len(buckets['drugs'])})",
        *buckets["drugs"],
        "",
        f"## phrases ({len(buckets['phrases'])})",
        *buckets["phrases"],
        "",
        f"## translit ({len(buckets['translit'])})",
        *buckets["translit"],
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {OUT}")
    print(
        f"drugs={len(buckets['drugs'])} "
        f"phrases={len(buckets['phrases'])} "
        f"translit={len(buckets['translit'])}"
    )


if __name__ == "__main__":
    main()
