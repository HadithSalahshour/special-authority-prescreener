#!/usr/bin/env python3
"""
BC PharmaCare Special Authority Policy Scraper

Fetches the full SA drug list from the BC government website,
then for each drug:
  1. Downloads the PDF criteria form if available
  2. Falls back to saving the HTML criteria as a .txt file

Saves everything to .local/policies/
Respects the server with a delay between requests.
Network access is opt-in and must be acknowledged explicitly.

Usage:
    python scrape_sa_policies.py --allow-network
    python scrape_sa_policies.py --allow-network --list-only
    python scrape_sa_policies.py --allow-network --limit 20
"""

import argparse
import os
import re
import time
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────

BASE_URL      = "https://www2.gov.bc.ca"
DRUG_LIST_URL = (
    "https://www2.gov.bc.ca/gov/content/health/practitioner-professional-resources"
    "/pharmacare/programs/special-authority/sa-drug-list"
)
POLICIES_DIR  = os.path.join(os.path.dirname(__file__), ".local", "policies")
DELAY_SEC     = 1.5   # pause between requests — be respectful to the server

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BC-SA-Scraper/1.0; "
        "healthcare research tool)"
    )
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── Helpers ───────────────────────────────────────────────────────────

def get(url: str, binary: bool = False, retries: int = 3):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=20, allow_redirects=True)
            r.raise_for_status()
            return r.content if binary else r.text
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"      FAILED after {retries} attempts: {e}")
                return None
            time.sleep(2)


def safe_filename(name: str) -> str:
    """Convert a drug name to a safe filename."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name[:120]


def extract_drug_links(html: str) -> list[dict]:
    """Parse the SA drug list page and return all drug name + URL pairs."""
    soup = BeautifulSoup(html, "html.parser")
    drugs = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "limited-coverage-drug" not in href:
            continue
        full_url = href if href.startswith("http") else urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        name = a.get_text(strip=True)
        if name:
            drugs.append({"name": name, "url": full_url})

    return drugs


def extract_criteria_text(soup: BeautifulSoup, drug_name: str) -> str:
    """
    Extract the Special Authority criteria text directly from the HTML page.

    The BC government drug pages contain the full criteria as readable HTML.
    The PDF links on each page point to SA *request forms* (fillable submission
    forms for doctors) — not criteria documents. We want the HTML criteria, not
    the forms.
    """
    lines = [f"BC PharmaCare Special Authority Criteria", f"Drug: {drug_name}", ""]

    # Remove nav, header, footer, scripts, and the sidebar form elements
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "noscript", "form"]):
        tag.decompose()

    # BC gov pages use these content container IDs/classes
    main = (
        soup.find("div", {"id": "wb-cont"}) or
        soup.find("main") or
        soup.find("div", class_=re.compile(r"content|main|body", re.I)) or
        soup.body
    )

    if main:
        # Remove breadcrumbs and "MORE TOPICS" sidebar if present
        for el in main.find_all(class_=re.compile(r"breadcrumb|sidebar|related|feedback", re.I)):
            el.decompose()

        text = main.get_text(separator="\n", strip=True)
        # Strip nav boilerplate that sometimes leaks through
        text = re.sub(r"(?m)^(Home|Menu|Search|Back to top|Share this page)$", "", text)
        # Clean excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines.append(text.strip())

    return "\n".join(lines)


# ── Main scraper ──────────────────────────────────────────────────────

def scrape_drug(drug: dict, index: int, total: int) -> dict:
    """
    Scrape one drug criteria page and save the HTML criteria text as a .txt file.

    NOTE: Each drug page links to a fillable SA *request form* PDF. We do NOT
    download those PDFs — they are blank submission forms, not criteria documents.
    The criteria text lives in the HTML of the drug page itself.
    """
    name = drug["name"]
    url  = drug["url"]
    slug = safe_filename(name)
    result = {"drug": name, "url": url, "status": None, "file": None}

    print(f"  [{index}/{total}] {name}")

    # Check if already scraped — skip to avoid hammering the server
    filename = f"sa_{slug}.txt"
    path = os.path.join(POLICIES_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) > 200:
        result["status"] = "skipped_exists"
        result["file"] = filename
        print(f"      → skipped (already exists): {filename}")
        return result

    html = get(url)
    if html is None:
        result["status"] = "fetch_failed"
        return result

    soup = BeautifulSoup(html, "html.parser")

    text = extract_criteria_text(soup, name)
    if len(text.strip()) < 150:
        result["status"] = "no_content"
        print(f"      → no usable content found")
        return result

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    result["status"] = "text_saved"
    result["file"] = filename
    print(f"      → saved: {filename} ({len(text)//1024}KB)")
    return result


def run(limit: int | None = None, list_only: bool = False):
    os.makedirs(POLICIES_DIR, exist_ok=True)

    print("Fetching SA drug list...")
    html = get(DRUG_LIST_URL)
    if not html:
        print("ERROR: Could not fetch the drug list page.")
        sys.exit(1)

    drugs = extract_drug_links(html)
    print(f"Found {len(drugs)} drugs on the SA list\n")

    if list_only:
        for i, d in enumerate(drugs, 1):
            print(f"  {i:3d}. {d['name']}")
            print(f"       {d['url']}")
        return

    if limit:
        drugs = drugs[:limit]
        print(f"Limited to first {limit} drugs\n")

    total    = len(drugs)
    results  = {"pdf_downloaded": [], "text_saved": [], "skipped_exists": [],
                "fetch_failed": [], "no_content": []}

    for i, drug in enumerate(drugs, 1):
        result = scrape_drug(drug, i, total)
        results[result["status"]].append(result["drug"])
        if i < total:
            time.sleep(DELAY_SEC)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  SCRAPE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  PDFs downloaded:   {len(results['pdf_downloaded'])}")
    print(f"  Text files saved:  {len(results['text_saved'])}")
    print(f"  Skipped (exist):   {len(results['skipped_exists'])}")
    print(f"  Fetch failed:      {len(results['fetch_failed'])}")
    print(f"  No content:        {len(results['no_content'])}")
    print(f"  Total processed:   {total}")
    print(f"{'=' * 60}")

    if results["fetch_failed"]:
        print(f"\nFailed drugs:")
        for d in results["fetch_failed"]:
            print(f"  • {d}")

    print(f"\nAll files saved to: {POLICIES_DIR}")
    print(f"\nNext step — re-ingest all policies:")
    print(f"  python check.py --ingest")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BC PharmaCare SA Policy Scraper")
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Acknowledge that this maintenance command contacts gov.bc.ca",
    )
    parser.add_argument("--list-only", action="store_true",
                        help="Print all drug names and URLs without downloading")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only scrape the first N drugs")
    args = parser.parse_args()

    if not args.allow_network:
        parser.error(
            "This maintenance command contacts gov.bc.ca. "
            "Re-run with --allow-network to continue."
        )

    run(limit=args.limit, list_only=args.list_only)
