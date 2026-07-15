# Academic moderation sources (Phase 1)

Raw downloads in `raw/`, plain-text conversions in `txt/`.
**No curation or false-positive filtering yet.**

Regenerate: `python convert_sources.py` (from this directory)

## Status

| ID | Source | URL | Format | Status | txt path | lines | chars | Notes |
|----|--------|-----|--------|--------|----------|-------|-------|-------|
| researchgate_euphemisms | ResearchGate — Phraseological Euphemisms (Prostitution RU/AR) | https://www.researchgate.net/publication/335982398_Linguo-Cultural_Research_on_Phraseological_Euphemisms_Representing_Prostitution_a_Case_Study_of_the_Russian_and_Arabic_Languages | .pdf | **converted** | `txt/researchgate_euphemisms.txt` | 1131 | 50943 | Mirror: CyberLeninka PDF (ResearchGate 403). https://cyberleninka.ru/article/n/lingvokulturologicheskoe-issledovanie-evfemisticheskih-frazeologizmov-oboznachayuschih-prostitutsiyu-na-materiale-russkogo-i/pdf |
| umk_dembska | UMK Dembska — prostitution euphemisms (item/2627) | https://repozytorium.umk.pl/handle/item/2627 | .pdf | **converted** | `txt/umk_dembska.txt` | 334 | 18007 | — |
| bazhum_dembska | bazhum.muzhp.pl — Dembska fallback search | https://bazhum.muzhp.pl/cgi-bin/bazhum/search.cgi?Query=Dembska | .html | **pending** | `—` | — | — | Fallback if UMK fails; search.cgi returns 404 as of 2026-07 |
| shlyakhov_adler_dict | Shlyakhov & Adler — Dictionary of Russian Slang (archive.org) | https://archive.org/details/dictionaryofruss0000shli | .pdf | **converted** | `txt/shlyakhov_adler_dict.txt` | 33809 | 1118655 | Mirror: languageadvisor.net PDF (archive.org borrow-only). https://languageadvisor.net/wp-content/uploads/2022/06/Dictionary-of-Russian-Slang-and-Colloquial-Expressions-PDFDrive-.pdf |
| cyberleninka_bayramova | CyberLeninka — Bayramova drug slang dictionary | https://cyberleninka.ru/article/n/l-k-bayramova-n-f-haliullova-slovar-russkogo-i-angliyskogo-zhargona-narkomanov-slovar-antitsennostey-kazan-tsentr-innovatsionnyh | .pdf | **converted** | `txt/cyberleninka_bayramova.txt` | 150 | 7988 | HTML article + /pdf endpoint |
| cuni_bppr_2014 | Charles University — BPPR 2014 drug slang PDF | https://dspace.cuni.cz/bitstream/handle/20.500.11956/87278/BPPR_2014_2_11210_0_409141_0_165091.pdf?sequence=4&isAllowed=y | .pdf | **converted** | `txt/cuni_bppr_2014.txt` | 1346 | 13657 | — |
| abannet_narcotics | abannet.ru — Danilin Narcotics slang dictionary PDF | https://abannet.ru/sites/default/files/СЛОВАРЬ%20НАРКОТИЧЕСКОГО%20АРГО.pdf | .pdf | **converted** | `txt/abannet_narcotics.txt` | 741 | 31063 | — |
| russki_mat_narc | russki-mat.net — Narcotics dictionary | https://www.russki-mat.net/e/mat_slovar_narkomanov.htm | .html | **converted** | `txt/russki_mat_narc.txt` | 3351 | 84839 | — |
| newlit_shkarin | old.newlit.ru — Shkarin dictionary excerpt | https://old.newlit.ru/~shkarin/001419.htm | .html | **converted** | `txt/newlit_shkarin.txt` | 490 | 14165 | — |
| hf_russian_sensitive | Skoltech/s-nlp sensitive topics (HF NiGuLa mirror) | https://raw.githubusercontent.com/s-nlp/inappropriate-sensitive-topics/main/Version3/sensitive_topics.csv | .csv | **converted** | `txt/hf_sensitive_topics.txt` | 1332 | 149219 | Open mirror of NiGuLa/Russian_Sensitive_Topics via s-nlp/inappropriate-sensitive-topics Version3; txt = prostitution-labeled text rows only |

**Total txt files produced:** 9

## Extraction output (Phase 2)

Candidate terms for manual curation — **not merged** into live `stop_words_*.txt`.

Regenerate:

```bash
python backend/data/moderation/_sources/academic/extract_terms.py
```

Outputs in `extracted/`:

| File | Purpose |
|------|---------|
| `candidates_phrases.txt` | Multi-word sex/drugs/profanity phrases, deduped, not in existing wordlists |
| `candidates_tokens.txt` | Single-token candidates by category (`# drugs`, `# sex`, `# profanity`, `# translit`) |
| `candidates_context_required.txt` | Ambiguous homonyms (кекс, снег, белый, …) — need proximity/neural layer, not exact block alone |
| `extraction_stats.json` | Per-source counts, totals, skipped duplicates |

Logic reuses `build_wordlists.py`: `classify()`, `norm()`, `is_valid_term()`, `DRUG_STEMS`, `SEX_STEMS`, `EXCLUDE_FALSE_POSITIVES`. Skips terms already in any live wordlist or `GLOBAL_EXCLUDE`.

Tests: `backend/tests/test_academic_term_extraction.py`.

## Curation output (Phase 3)

Reproducible curation → merge into live wordlists via `build_wordlists.py`.

```bash
python backend/data/moderation/_sources/academic/curate_candidates.py
python backend/data/moderation/build_wordlists.py
```

| File | Purpose |
|------|---------|
| `curated/curated_drugs.txt` | FP-safe drug headwords → `stop_words_drugs.txt` |
| `curated/curated_sex.txt` | Sex slang tokens → `stop_words_sex.txt` |
| `curated/curated_phrases.txt` | Multi-word phrases → `stop_words_slang_manual.txt` (exact match) |
| `curated/curated_translit.txt` | Latin obfuscation → `stop_words_translit.txt` |
| `curated/curated_context_required.txt` | Copy of ambiguous homonyms (not block lists) |
| `../../context_required.txt` | Stable context-required reference for proximity layer |
| `curated/curation_stats.json` | Before/after counts, accepted/rejected breakdown |

**Not merged into blind block lists:** terms in `context_required.txt` (кекс, снег, герыч, домохозяйка, …). Proximity/context module pending — file preserved for Phase 9.4+.

Tests: `backend/tests/test_academic_term_curation.py`.

## Failures / skipped

- None

## Extra raw files

Some sources save auxiliary files (landing pages, metadata):
- `raw/umk_dembska_page.html` — UMK repository landing page
- `raw/cyberleninka_bayramova.html` — article HTML (PDF preferred)
- `raw/researchgate_euphemisms_blocked.html` — ResearchGate 403 block page (fallback)
- `raw/hf_sensitive_topics.csv` — Skoltech/s-nlp sensitive topics (open mirror)
- `raw/archive_org_metadata.json` — archive.org file list (if Shlyakhov mirror fails)

