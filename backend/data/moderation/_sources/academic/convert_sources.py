#!/usr/bin/env python3
"""Download academic moderation sources and convert to plain text (Phase 1).

Usage (from repo root or this directory):
    python backend/data/moderation/_sources/academic/convert_sources.py
    python backend/data/moderation/_sources/academic/convert_sources.py --convert-only

Requires: httpx, beautifulsoup4, pymupdf (fitz) — install in backend venv if missing.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx", file=sys.stderr)
    raise

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore[misc, assignment]

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None  # type: ignore[assignment]

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
TXT_DIR = BASE_DIR / "txt"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 90.0

# Sources where raw may exist but must not become wordlist input
NO_TXT_CONVERT = frozenset({
    "bazhum_dembska",
})

RESEARCHGATE_MIRROR_URL = (
    "https://cyberleninka.ru/article/n/"
    "lingvokulturologicheskoe-issledovanie-evfemisticheskih-frazeologizmov-"
    "oboznachayuschih-prostitutsiyu-na-materiale-russkogo-i/pdf"
)
SHLYAKHOV_MIRROR_URL = (
    "https://languageadvisor.net/wp-content/uploads/2022/06/"
    "Dictionary-of-Russian-Slang-and-Colloquial-Expressions-PDFDrive-.pdf"
)
HF_SENSITIVE_TOPICS_URL = (
    "https://raw.githubusercontent.com/s-nlp/inappropriate-sensitive-topics/"
    "main/Version3/sensitive_topics.csv"
)

# abannet PDF — percent-encoded URL often 404; Cyrillic path works
ABANNET_PDF_URLS = [
    "https://abannet.ru/sites/default/files/СЛОВАРЬ%20НАРКОТИЧЕСКОГО%20АРГО.pdf",
    (
        "https://abannet.ru/sites/default/files/"
        "%D0%A1%D0%9B%D0%9E%D0%92%D0%90%D0%A0%D0%AC%20%D0%9D%D0%90%D0%A0%D0%9A%D0%9E%D0%A2%D0%98%D0%A7%D0%95%D0%A1%D0%9A%D0%9E%D0%93%D0%9E%20%D0%90%D0%A0%D0%93%D0%BE.pdf"
    ),
]


@dataclass
class Source:
    id: str
    name: str
    url: str
    category: str
    raw_filename: str | None = None
    notes: str = ""
    status: str = "pending"
    txt_path: str = ""
    lines: int = 0
    chars: int = 0
    error: str = ""


SOURCES: list[Source] = [
    Source(
        id="researchgate_euphemisms",
        name="ResearchGate — Phraseological Euphemisms (Prostitution RU/AR)",
        url=(
            "https://www.researchgate.net/publication/335982398_"
            "Linguo-Cultural_Research_on_Phraseological_Euphemisms_Representing_"
            "Prostitution_a_Case_Study_of_the_Russian_and_Arabic_Languages"
        ),
        category="sex",
        raw_filename="researchgate_euphemisms.pdf",
        notes=f"Mirror: CyberLeninka PDF (ResearchGate 403). {RESEARCHGATE_MIRROR_URL}",
    ),
    Source(
        id="umk_dembska",
        name="UMK Dembska — prostitution euphemisms (item/2627)",
        url="https://repozytorium.umk.pl/handle/item/2627",
        category="sex",
        raw_filename="umk_dembska.pdf",
    ),
    Source(
        id="bazhum_dembska",
        name="bazhum.muzhp.pl — Dembska fallback search",
        url="https://bazhum.muzhp.pl/cgi-bin/bazhum/search.cgi?Query=Dembska",
        category="sex",
        raw_filename="bazhum_search_dembska.html",
        notes="Fallback if UMK fails; search.cgi returns 404 as of 2026-07",
    ),
    Source(
        id="shlyakhov_adler_dict",
        name="Shlyakhov & Adler — Dictionary of Russian Slang (archive.org)",
        url="https://archive.org/details/dictionaryofruss0000shli",
        category="slang",
        raw_filename="shlyakhov_adler_dict.pdf",
        notes=f"Mirror: languageadvisor.net PDF (archive.org borrow-only). {SHLYAKHOV_MIRROR_URL}",
    ),
    Source(
        id="cyberleninka_bayramova",
        name="CyberLeninka — Bayramova drug slang dictionary",
        url=(
            "https://cyberleninka.ru/article/n/l-k-bayramova-n-f-haliullova-"
            "slovar-russkogo-i-angliyskogo-zhargona-narkomanov-slovar-antitsennostey-"
            "kazan-tsentr-innovatsionnyh"
        ),
        category="drugs",
        raw_filename="cyberleninka_bayramova.pdf",
        notes="HTML article + /pdf endpoint",
    ),
    Source(
        id="cuni_bppr_2014",
        name="Charles University — BPPR 2014 drug slang PDF",
        url=(
            "https://dspace.cuni.cz/bitstream/handle/20.500.11956/87278/"
            "BPPR_2014_2_11210_0_409141_0_165091.pdf?sequence=4&isAllowed=y"
        ),
        category="drugs",
        raw_filename="cuni_bppr_2014.pdf",
    ),
    Source(
        id="abannet_narcotics",
        name="abannet.ru — Danilin Narcotics slang dictionary PDF",
        url=ABANNET_PDF_URLS[0],
        category="drugs",
        raw_filename="abannet_narcotics.pdf",
    ),
    Source(
        id="russki_mat_narc",
        name="russki-mat.net — Narcotics dictionary",
        url="https://www.russki-mat.net/e/mat_slovar_narkomanov.htm",
        category="drugs",
        raw_filename="russki_mat_narc.html",
    ),
    Source(
        id="newlit_shkarin",
        name="old.newlit.ru — Shkarin dictionary excerpt",
        url="https://old.newlit.ru/~shkarin/001419.htm",
        category="slang",
        raw_filename="newlit_shkarin.html",
    ),
    Source(
        id="hf_russian_sensitive",
        name="Skoltech/s-nlp sensitive topics (HF NiGuLa mirror)",
        url=HF_SENSITIVE_TOPICS_URL,
        category="hf",
        raw_filename="hf_sensitive_topics.csv",
        notes=(
            "Open mirror of NiGuLa/Russian_Sensitive_Topics via "
            "s-nlp/inappropriate-sensitive-topics Version3; "
            "txt = prostitution-labeled text rows only"
        ),
    ),
]


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_url(
    client: httpx.Client, url: str, headers: dict[str, str] | None = None
) -> tuple[bytes, str, int]:
    req_headers = headers or {}
    resp = client.get(url, follow_redirects=True, headers=req_headers)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    return resp.content, ctype, resp.status_code


def find_pdf_link(html: bytes, base_url: str) -> str | None:
    if BeautifulSoup is None:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").lower()
        if href.lower().endswith(".pdf") or "pdf" in text:
            return urljoin(base_url, href)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower() or "bitstream" in href.lower():
            return urljoin(base_url, href)
    return None


def try_download_pdf(client: httpx.Client, urls: list[str], dest: Path) -> str:
    last_err = ""
    for url in urls:
        try:
            extra: dict[str, str] = {}
            if "cyberleninka.ru" in url:
                extra["Referer"] = "https://cyberleninka.ru/"
            data, ctype, _ = fetch_url(client, url, headers=extra or None)
            if b"%PDF" in data[:8] or "pdf" in ctype.lower():
                dest.write_bytes(data)
                return url
        except Exception as exc:
            last_err = str(exc)
    raise RuntimeError(last_err or "No PDF URL succeeded")


def download_archive_org(client: httpx.Client, src: Source) -> None:
    """archive.org item is borrow-only; PDF/DjVuTXT return 401 without login."""
    item_id = "dictionaryofruss0000shli"
    meta = client.get(f"https://archive.org/metadata/{item_id}", timeout=TIMEOUT)
    meta.raise_for_status()
    files = meta.json().get("files", [])
    private_pdf = any(
        f.get("name") == f"{item_id}.pdf" and f.get("private") == "true" for f in files
    )
    (RAW_DIR / "archive_org_metadata.json").write_text(
        meta.text, encoding="utf-8"
    )
    src.status = "failed"
    src.error = (
        "archive.org borrow-only (401 on PDF/DjVuTXT; files marked private=true). "
        "Manual borrow at archive.org/details/dictionaryofruss0000shli required."
    )
    src.notes = f"Saved metadata JSON; private_pdf={private_pdf}"


def download_source(client: httpx.Client, src: Source) -> None:
    if src.status == "skipped":
        return

    assert src.raw_filename
    raw_path = RAW_DIR / src.raw_filename

    try:
        if src.id == "shlyakhov_adler_dict":
            try:
                actual = try_download_pdf(client, [SHLYAKHOV_MIRROR_URL], raw_path)
                src.notes = (
                    f"Mirror PDF from {actual} "
                    "(original archive.org borrow-only: dictionaryofruss0000shli)"
                )
                src.status = "downloaded"
            except Exception:
                download_archive_org(client, src)
            return

        if src.id == "researchgate_euphemisms":
            mirror_urls = [
                RESEARCHGATE_MIRROR_URL,
                "https://doi.org/10.17072/2073-6681-2019-2-44-54",
            ]
            try:
                actual = try_download_pdf(client, mirror_urls, raw_path)
                src.notes = (
                    f"Mirror PDF from {actual} "
                    "(original ResearchGate 403; DOI 10.17072/2073-6681-2019-2-44-54)"
                )
                src.status = "downloaded"
            except Exception:
                try:
                    data, _, code = fetch_url(client, src.url)
                except httpx.HTTPStatusError as exc:
                    data = exc.response.content
                    code = exc.response.status_code
                blocked = RAW_DIR / "researchgate_euphemisms_blocked.html"
                blocked.write_bytes(data)
                src.status = "failed"
                src.error = (
                    f"HTTP {code} — ResearchGate block; CyberLeninka mirror also failed. "
                    "Saved blocked HTML shell."
                )
            return

        if src.id == "hf_russian_sensitive":
            data, _, _ = fetch_url(client, HF_SENSITIVE_TOPICS_URL)
            raw_path.write_bytes(data)
            src.notes = (
                f"CSV from {HF_SENSITIVE_TOPICS_URL} "
                "(open Skoltech/s-nlp mirror; gated NiGuLa HF dataset)"
            )
            src.status = "downloaded"
            return

        if src.id == "umk_dembska":
            html, _, _ = fetch_url(client, src.url)
            (RAW_DIR / "umk_dembska_page.html").write_bytes(html)
            pdf_url = find_pdf_link(html, src.url)
            if not pdf_url:
                pdf_url = (
                    "https://repozytorium.umk.pl/bitstreams/"
                    "382f7f15-c350-4321-afae-41d4fe92c8a6/download"
                )
            actual = try_download_pdf(client, [pdf_url], raw_path)
            src.notes = f"PDF from {actual}"
            src.status = "downloaded"
            return

        if src.id == "bazhum_dembska":
            try:
                data, _, _ = fetch_url(client, src.url)
                raw_path.write_bytes(data)
                src.status = "partial"
                src.error = "bazhum search.cgi returned page but likely 404/error shell"
            except httpx.HTTPStatusError as exc:
                src.status = "failed"
                src.error = f"HTTP {exc.response.status_code} — bazhum search unavailable"
            return

        if src.id == "cyberleninka_bayramova":
            article_url = src.url
            html, _, _ = fetch_url(client, article_url)
            (RAW_DIR / "cyberleninka_bayramova.html").write_bytes(html)
            pdf_url = article_url.rstrip("/") + "/pdf"
            actual = try_download_pdf(client, [pdf_url], raw_path)
            src.notes = f"PDF from {pdf_url}; HTML article also saved"
            src.status = "downloaded"
            return

        if src.id == "abannet_narcotics":
            headers = {"Referer": "https://abannet.ru/"}
            last_err = ""
            for url in ABANNET_PDF_URLS:
                try:
                    resp = client.get(url, follow_redirects=True, headers=headers)
                    resp.raise_for_status()
                    if b"%PDF" in resp.content[:8]:
                        raw_path.write_bytes(resp.content)
                        src.url = url
                        src.notes = f"Downloaded via Cyrillic filename URL"
                        src.status = "downloaded"
                        return
                except Exception as exc:
                    last_err = str(exc)
            src.status = "failed"
            src.error = f"All abannet URLs failed ({last_err})"
            return

        # default: direct fetch
        data, ctype, _ = fetch_url(client, src.url)
        raw_path.write_bytes(data)

        if src.raw_filename.endswith(".pdf") and b"%PDF" not in data[:8]:
            src.status = "failed"
            src.error = f"Response is not PDF (content-type: {ctype}, size={len(data)})"
            return

        src.status = "downloaded"

    except httpx.HTTPStatusError as exc:
        src.status = "failed"
        src.error = f"HTTP {exc.response.status_code}"
    except Exception as exc:
        src.status = "failed"
        src.error = str(exc)[:240]


def pdf_to_text_pymupdf(pdf_path: Path) -> str:
    if fitz is None:
        raise RuntimeError("pymupdf not installed — pip install pymupdf")
    doc = fitz.open(pdf_path)
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return "\n".join(parts)


def pdf_to_text_pdftotext(pdf_path: Path) -> str | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    out = pdf_path.with_suffix(".tmp.txt")
    result = subprocess.run(
        [exe, "-layout", str(pdf_path), str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and out.exists():
        text = out.read_text(encoding="utf-8", errors="replace")
        out.unlink(missing_ok=True)
        return text
    return None


def html_to_text(html_path: Path) -> str:
    raw = html_path.read_bytes()
    if BeautifulSoup is None:
        text = re.sub(r"<[^>]+>", " ", raw.decode("utf-8", errors="replace"))
        return unescape(re.sub(r"\s+", " ", text))
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def csv_sensitive_topics_to_text(csv_path: Path) -> str:
    """Extract prostitution-labeled message texts from Skoltech sensitive_topics CSV."""
    lines: list[str] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                if float(row.get("prostitution") or 0) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            text = (row.get("text") or "").strip()
            if text:
                lines.append(text)
    return "\n".join(lines)


def raw_to_text(raw_path: Path) -> str:
    suffix = raw_path.suffix.lower()
    if suffix == ".pdf":
        text = pdf_to_text_pdftotext(raw_path)
        if text is None:
            text = pdf_to_text_pymupdf(raw_path)
        return text
    if suffix == ".csv":
        if raw_path.name == "hf_sensitive_topics.csv":
            return csv_sensitive_topics_to_text(raw_path)
        return raw_path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        return html_to_text(raw_path)
    if suffix == ".gz":
        with gzip.open(raw_path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return raw_path.read_text(encoding="utf-8", errors="replace")


def convert_file(src: Source) -> None:
    if not src.raw_filename or src.id in NO_TXT_CONVERT:
        return
    if src.status in ("skipped", "failed", "partial"):
        # convert-only mode: still convert if we have a good raw file from prior run
        if src.status in ("failed", "partial", "skipped"):
            pass  # fall through if raw exists

    raw_path = RAW_DIR / src.raw_filename
    if not raw_path.exists():
        return

    txt_name = raw_path.stem + ".txt"
    txt_path = TXT_DIR / txt_name

    try:
        text = raw_to_text(raw_path)
        txt_path.write_text(text, encoding="utf-8")
        src.txt_path = str(txt_path.relative_to(BASE_DIR)).replace("\\", "/")
        src.lines = len(text.splitlines())
        src.chars = len(text)
        if src.status != "skipped" and src.lines > 0:
            src.status = "converted"
    except Exception as exc:
        src.error = (src.error + f" | convert: {exc}").strip(" |")
        if src.status not in ("partial",):
            src.status = "failed"


def write_readme(sources: list[Source]) -> None:
    lines = [
        "# Academic moderation sources (Phase 1)",
        "",
        "Raw downloads in `raw/`, plain-text conversions in `txt/`.",
        "**No curation or false-positive filtering yet.**",
        "",
        "Regenerate: `python convert_sources.py` (from this directory)",
        "",
        "## Status",
        "",
        "| ID | Source | URL | Format | Status | txt path | lines | chars | Notes |",
        "|----|--------|-----|--------|--------|----------|-------|-------|-------|",
    ]
    for s in sources:
        fmt = Path(s.raw_filename).suffix if s.raw_filename else "—"
        note = s.error or s.notes or "—"
        note = note.replace("|", "/").replace("\n", " ")
        lines.append(
            f"| {s.id} | {s.name} | {s.url} | {fmt} | **{s.status}** | "
            f"`{s.txt_path or '—'}` | {s.lines or '—'} | {s.chars or '—'} | {note} |"
        )

    converted = sum(
        1 for s in sources if s.txt_path and s.id not in NO_TXT_CONVERT
    )
    lines.extend(
        [
            "",
            f"**Total txt files produced:** {converted}",
            "",
            "## Failures / skipped",
            "",
        ]
    )
    problems = [s for s in sources if s.status in ("failed", "partial", "skipped")]
    if problems:
        for s in problems:
            detail = s.error or s.notes or s.status
            lines.append(f"- **{s.id}**: {detail}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Extra raw files",
            "",
            "Some sources save auxiliary files (landing pages, metadata):",
            "- `raw/umk_dembska_page.html` — UMK repository landing page",
            "- `raw/cyberleninka_bayramova.html` — article HTML (PDF preferred)",
            "- `raw/researchgate_euphemisms_blocked.html` — ResearchGate 403 block page (fallback)",
            "- `raw/hf_sensitive_topics.csv` — Skoltech/s-nlp sensitive topics (open mirror)",
            "- `raw/archive_org_metadata.json` — archive.org file list (if Shlyakhov mirror fails)",
            "",
        ]
    )

    (BASE_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and convert academic moderation sources")
    parser.add_argument("--convert-only", action="store_true", help="Skip download, convert existing raw files")
    parser.add_argument("--download-only", action="store_true", help="Skip conversion")
    args = parser.parse_args()

    ensure_dirs()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    if not args.convert_only:
        with httpx.Client(headers=headers, timeout=TIMEOUT, verify=True) as client:
            for src in SOURCES:
                print(f"Downloading: {src.id} ...")
                download_source(client, src)
                print(f"  -> {src.status}" + (f" ({src.error})" if src.error else ""))

    if not args.download_only:
        for src in SOURCES:
            if src.id in NO_TXT_CONVERT:
                continue
            raw = RAW_DIR / (src.raw_filename or "")
            if raw.exists():
                print(f"Converting: {src.id} ...")
                convert_file(src)
                if src.txt_path:
                    print(f"  -> {src.txt_path} ({src.lines} lines, {src.chars} chars)")

    write_readme(SOURCES)
    converted = sum(
        1 for s in SOURCES if s.txt_path and s.id not in NO_TXT_CONVERT
    )
    print(f"\nREADME: {BASE_DIR / 'README.md'}")
    print(f"Total txt files: {converted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
