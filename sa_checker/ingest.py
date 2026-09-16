"""
Load policy files, extract discrete criteria with local Ollama, and write a
local cache. Runtime retrieval indexes patient notes separately.
"""

import os
import json
import re

from PyPDF2 import PdfReader
from sa_checker.local_llm import chat

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_FILE = os.path.join(ROOT, ".local", "criteria_cache.json")
DEMO_CACHE_FILE = os.path.join(ROOT, "data", "demo_criteria_cache.json")


def active_cache_file() -> str:
    return CACHE_FILE if os.path.exists(CACHE_FILE) else DEMO_CACHE_FILE


def cache_mode() -> str:
    return "local-generated" if os.path.exists(CACHE_FILE) else "fictional-demo"


def _clean(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"Page \d+ of \d+", "", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2},?\s+\d+:\d+\s*[apm]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"MORE TOPICS.*?Search", "", text, flags=re.DOTALL)
    text = re.sub(r"Menu\s*Search", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _pdf_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def _txt_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_drug_name(text: str, filename: str) -> str:
    snippet = _clean(text)[:800]
    prompt = (
        f"From this BC PharmaCare Special Authority policy document extract the drug name "
        f"and the medical condition it treats.\n"
        f"Filename hint: {filename}\n"
        f"Document snippet:\n{snippet}\n\n"
        f"Return ONLY a short lowercase identifier such as "
        f"'ferric carboxymaltose for iron deficiency anemia' or "
        f"'abatacept for rheumatoid arthritis'. Nothing else."
    )
    return chat(prompt).strip().strip('"').lower()


def _extract_criteria(drug_name: str, text: str) -> list[str]:
    cleaned = _clean(text)[:5500]
    prompt = (
        f"You are reading a BC PharmaCare Special Authority policy for: {drug_name}\n\n"
        f"Extract ONLY the patient eligibility criteria that a prescriber must satisfy to receive SA approval.\n\n"
        f"INCLUDE:\n"
        f"- Diagnosis requirements (patient must have condition X)\n"
        f"- Lab value thresholds (e.g. LVEF ≤ 40%, ferritin ≤ 300)\n"
        f"- Prior treatment history (e.g. failed methotrexate for 3+ months)\n"
        f"- Required specialist type or assessments\n"
        f"- Functional class requirements (e.g. NYHA Class II-III)\n\n"
        f"DO NOT INCLUDE — these are NOT eligibility criteria:\n"
        f"- Contraindications or safety warnings (e.g. 'drug is contraindicated in X')\n"
        f"- Definitions of terms (e.g. 'moderate COPD is defined as...')\n"
        f"- Monitoring or administration requirements (e.g. 'liver function tests should be monitored')\n"
        f"- Clinical guidance or notes (e.g. 'clinical judgement is warranted')\n"
        f"- Treatment strategy statements (e.g. 'should be used in combination with...')\n"
        f"- Approval period durations (e.g. 'First approval: 12 weeks', 'Renewal: 1 year', 'Indefinite')\n"
        f"- Form references or submission requirements (e.g. 'submit using HLTH form')\n\n"
        f"Rules:\n"
        f"- Each string is ONE complete, self-contained criterion\n"
        f"- Keep exact language from the document\n"
        f"- Do NOT invent criteria not in the document\n"
        f"- Return ONLY the JSON array, no prose before or after\n\n"
        f"Policy text:\n{cleaned}\n\n"
        f"JSON array of criteria:"
    )
    raw = chat(prompt).strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    try:
        return [c for c in json.loads(raw[start:end]) if isinstance(c, str) and c.strip()]
    except json.JSONDecodeError:
        return []


def ingest_all(policies_dir: str) -> list[dict]:
    cache = {}
    results = []

    # Files to skip: the main SA drug list page (not a criteria document)
    SKIP_FILES = {"sa_limited_coverage_drugs.txt", "sa_limited_coverage_drugs.pdf"}

    for fname in sorted(os.listdir(policies_dir)):
        if fname in SKIP_FILES:
            continue
        if fname.endswith(".pdf"):
            path = os.path.join(policies_dir, fname)
            text = _pdf_text(path)
        elif fname.endswith(".txt"):
            path = os.path.join(policies_dir, fname)
            text = _txt_text(path)
        else:
            continue

        print(f"\n  [{fname}]")

        drug_name = _extract_drug_name(text, fname)
        print(f"  Drug identified: {drug_name}")

        criteria = _extract_criteria(drug_name, text)
        if not criteria:
            print(f"  WARNING: no criteria extracted — skipping")
            continue
        print(f"  Criteria extracted: {len(criteria)}")
        for i, c in enumerate(criteria, 1):
            print(f"    {i}. {c[:90]}{'...' if len(c) > 90 else ''}")

        cache[drug_name] = {"criteria": criteria, "source_file": fname}
        results.append({"drug": drug_name, "criteria_count": len(criteria), "file": fname})

    cache_path = os.path.abspath(CACHE_FILE)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"\n  Cache saved to: {cache_path}")

    return results


def get_criteria_for_drug(drug_query: str) -> tuple[str, list[str]]:
    cache_path = os.path.abspath(active_cache_file())
    if not os.path.exists(cache_path):
        raise RuntimeError("No criteria cache found. Run: python check.py --ingest")

    with open(cache_path) as f:
        cache = json.load(f)

    q = drug_query.lower().strip()

    # 1. Exact match
    if q in cache:
        return q, cache[q]["criteria"]

    # 2. Drug-name prefix match: extract the drug name (before " for ") from the query
    #    and find cache entries whose drug name starts with the same token.
    #    This prevents "cyclosporine for RA" from matching "sarilumab for RA" via shared condition words.
    q_drug_name = q.split(" for ")[0].strip()
    prefix_matches = [d for d in cache if d.split(" for ")[0].strip() == q_drug_name]
    if len(prefix_matches) == 1:
        return prefix_matches[0], cache[prefix_matches[0]]["criteria"]
    if len(prefix_matches) > 1:
        # Multiple same-drug entries (e.g. infliximab for RA vs infliximab for CD):
        # pick the one with highest word overlap on the full query
        query_words = set(q.split())
        best = max(prefix_matches, key=lambda d: len(query_words & set(d.split())))
        return best, cache[best]["criteria"]

    # 3. Fallback: full word-overlap (condition-name weighted)
    query_words = set(q.split())
    best_drug, best_score = None, -1
    for drug in cache:
        score = len(query_words & set(drug.split()))
        if score > best_score:
            best_score, best_drug = score, drug

    if not best_drug or best_score == 0:
        return None, []

    return best_drug, cache[best_drug]["criteria"]


def list_drugs() -> list[str]:
    cache_path = os.path.abspath(active_cache_file())
    if not os.path.exists(cache_path):
        return []
    with open(cache_path) as f:
        return sorted(json.load(f).keys())
