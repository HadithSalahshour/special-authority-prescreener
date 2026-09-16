"""
Core criterion checker — now RAG-powered.

Flow per criterion:
  1. Retrieve top-k relevant chunks from the in-process hybrid index
  2. Pass retrieved context to LLM (temperature=0)
  3. Citation relevance check — blocks off-topic citations
  4. Numeric threshold check — programmatic math verification
  5. LLM numeric verify — second-pass confirmation for threshold criteria
"""

import json
import re
from sa_checker.local_llm import chat

_PROMPT = """You are a strict clinical documentation reviewer for BC PharmaCare Special Authority requests.

CRITERION:
{criterion}

RELEVANT CLINICAL DOCUMENTATION (retrieved from patient record):
{context}

YOUR TASK:
Search the documentation above for text that DIRECTLY and EXPLICITLY satisfies the criterion.

STRICT RULES:
- MET requires the criterion to be directly stated — do NOT infer, imply, or extrapolate.
  WRONG: "symptoms suggest NYHA class III" — this is inference.
  RIGHT: "Patient is NYHA functional class III" — this is explicit.
- The citation MUST be about the same topic as the criterion.
  If the criterion is about ferritin, the citation must mention ferritin or transferrin — not echocardiogram findings.
  If the criterion is about NYHA class, the citation must state NYHA class explicitly — not ejection fraction.
- If the criterion contains a numeric threshold (e.g. "≤ 300 mcg/L", "< 15%", "≥ 55%"):
  Extract the measured number and compare mathematically.
  ≤ means "at most" — criterion is MET when the value is LOW:
    38% DOES satisfy ≤ 40% (38 < 40 ✓); 95 mcg/L DOES satisfy ≤ 300 mcg/L (95 < 300 ✓); 45% does NOT satisfy ≤ 40% (45 > 40 ✗).
  ≥ means "at least" — criterion is MET when the value is HIGH:
    67% DOES satisfy ≥ 55% (67 > 55 ✓); 33% does NOT satisfy ≥ 55% (33 < 55 ✗).
  < means "strictly less than": 8% DOES satisfy < 15% (8 < 15 ✓).
  > means "greater than": 65 mmHg DOES satisfy > 50 mmHg (65 > 50 ✓).
- If the exact information is absent: assign NOT MET.
- If partial or ambiguous evidence exists: assign UNCLEAR.
- Never assign MET without a verbatim citation that directly satisfies the criterion.

VERDICTS:
  MET      — Explicit, on-topic, directly satisfying evidence found. Provide verbatim citation.
  NOT MET  — Required information is absent or does not satisfy the criterion. Citation = null.
  UNCLEAR  — Partial or ambiguous evidence only. Citation may be partial or null.

IMPORTANT: If a criterion contains "one of the following" or OR conditions, it is satisfied if ANY ONE option is met.
Evaluate the criterion as a WHOLE and output exactly ONE final verdict.

OUTPUT FORMAT: Respond with EXACTLY ONE JSON object and nothing else:
{{"status": "MET", "citation": "verbatim text from the documentation", "reasoning": "one concise sentence"}}
{{"status": "NOT MET", "citation": null, "reasoning": "one concise sentence"}}
{{"status": "UNCLEAR", "citation": "partial quote or null", "reasoning": "one concise sentence"}}"""

_VERIFY_PROMPT = """Verify this numeric threshold check.

Criterion: {criterion}
Evidence: {citation}

Find the MEASURED value in the evidence for the same measurement named in the criterion.
Compare ONLY that measured value to the threshold. Ignore any numbers that are:
  - parenthetical references repeating the threshold (e.g. "(≥300 cells/µl confirmed)")
  - counts of a different measurement (e.g. exacerbation counts when criterion is about eosinophils)
  - years, weeks, months, or other non-measurement numbers

Remember: ≤ means "less than OR EQUAL TO" (so 40 satisfies ≤ 40); ≥ means "greater than OR EQUAL TO".

Examples:
  Criterion "LVEF ≤ 40%", Evidence "ejection fraction 45%" → measured LVEF=45, 45 > 40 → no
  Criterion "LVEF ≤ 40%", Evidence "LVEF 40% — reduced EF" → measured LVEF=40, 40 ≤ 40 → yes
  Criterion "ferritin ≤ 300 mcg/L", Evidence "ferritin 180 mcg/L" → measured ferritin=180, 180 ≤ 300 → yes
  Criterion "TSAT < 15%", Evidence "TSAT 8% (<15% threshold)" → measured TSAT=8, ignore 15 (threshold ref), 8 < 15 → yes
  Criterion "eosinophils ≥300 cells/µl", Evidence "eos 847 cells/µl, 2 exacerbations" → measured eos=847, ignore 2 (different measurement), 847 ≥ 300 → yes
  Criterion "LVEF ≥ 55%", Evidence "LVEF 67% (≥55% threshold met)" → measured LVEF=67, ignore 55 (threshold ref), 67 ≥ 55 → yes
  Criterion "resting heart rate ≥77 bpm", Evidence "resting heart rate confirmed to average ≥77 bpm on ECG" → evidence states the average IS ≥77 bpm, which directly satisfies ≥77 bpm → yes

Does the measured value satisfy the threshold?
Answer ONLY "yes" or "no"."""


# ── Relevance check ───────────────────────────────────────────────────

_STOPWORDS = {
    "with", "that", "this", "from", "have", "been", "must", "least",
    "most", "more", "less", "which", "where", "each", "such", "either",
    "both", "only", "also", "than", "then", "when", "once", "upon",
    "patient", "patients", "clinical", "notes", "history", "current",
    "prior", "based", "required", "requires", "including", "following",
    "documented", "determined", "diagnosis", "diagnosed", "evidence",
    "adequate", "failure", "other", "their", "there", "appropriate",
}


def _citation_is_relevant(criterion: str, citation: str) -> bool:
    terms = {
        w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", criterion)
        if w.lower() not in _STOPWORDS
    }
    if not terms:
        return True
    return any(t in citation.lower() for t in terms)


def _normalise_space(value: str) -> str:
    return " ".join((value or "").split()).casefold()


def _citation_is_verbatim(citation: str, context: str) -> bool:
    """Require cited evidence to exist in the retrieved patient documentation."""
    quoted = _normalise_space(citation)
    return bool(quoted) and quoted in _normalise_space(context)


# ── Numeric threshold checks ──────────────────────────────────────────

_THRESHOLD_RE = re.compile(
    r"(≤|≥|<=|>=|<|>)\s*([\d]+(?:\.\d+)?)\s*"
    r"(%|[a-zA-Zµμ]+(?:/[a-zA-Zµμ]+)?)?",
    re.IGNORECASE,
)
_OPS = {
    "≤": lambda a, b: a <= b, "<=": lambda a, b: a <= b,
    "≥": lambda a, b: a >= b, ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,  ">": lambda a, b: a > b,
}


def _normalise_unit(unit: str | None) -> str:
    return (unit or "").casefold().replace("μ", "µ")


def _numeric_ok(criterion: str, citation: str) -> bool | None:
    """Conservatively verify one simple threshold, or return None if ambiguous."""
    m = _THRESHOLD_RE.search(criterion)
    if not m:
        return None
    op, threshold = _OPS.get(m.group(1)), float(m.group(2))
    unit = _normalise_unit(m.group(3))
    if not op:
        return None

    candidate_re = re.compile(
        r"(?<![\d.])(\d+(?:\.\d+)?)\s*"
        r"(%|[a-zA-Zµμ]+(?:/[a-zA-Zµμ]+)?)?",
        re.IGNORECASE,
    )
    candidates: list[float] = []
    for match in candidate_re.finditer(citation or ""):
        if unit and _normalise_unit(match.group(2)) != unit:
            continue
        prefix = (citation or "")[max(0, match.start() - 3):match.start()]
        if re.search(r"[≤≥<>]\s*$", prefix):
            continue
        candidates.append(float(match.group(1)))

    if len(candidates) != 1:
        return None
    return op(candidates[0], threshold)


def _llm_verify_numeric(criterion: str, citation: str) -> bool:
    content = chat(
        _VERIFY_PROMPT.format(criterion=criterion, citation=citation)
    ).strip().lower()
    # LLM often shows reasoning before the final verdict (e.g. "67 ≥ 55 → yes").
    # Check the first line, the last word, and the full start to find the verdict.
    first_line = content.split("\n")[0].strip().rstrip(".,!?→ ")
    last_word = content.split()[-1].rstrip(".,!?→") if content.split() else ""
    return (
        first_line.startswith("yes")
        or first_line == "yes"
        or last_word == "yes"
        or content.startswith("yes")
    )


# ── Parser ────────────────────────────────────────────────────────────

def _parse(raw: str, criterion: str) -> dict:
    raw = raw.strip()
    s, e = raw.find("{"), raw.rfind("}") + 1
    if s != -1 and e > 0:
        try:
            data = json.loads(raw[s:e])
            status = str(data.get("status", "UNCLEAR")).upper().strip()
            if "NOT" in status and "MET" in status:
                status = "NOT MET"
            elif status not in ("MET", "UNCLEAR"):
                status = "UNCLEAR"
            return {
                "criterion": criterion,
                "status": status,
                "citation": data.get("citation"),
                "reasoning": data.get("reasoning", ""),
            }
        except json.JSONDecodeError:
            pass
    upper = raw.upper()
    if "NOT MET" in upper or "NOT_MET" in upper:
        status = "NOT MET"
    elif '"MET"' in raw or "'MET'" in raw:
        status = "MET"
    else:
        status = "UNCLEAR"
    return {"criterion": criterion, "status": status, "citation": None, "reasoning": raw[:200]}


# ── Core check (uses retrieved chunks as context) ────────────────────

def check_criterion(criterion: str, context_chunks: list[str]) -> dict:
    if not context_chunks:
        return {
            "criterion": criterion,
            "status": "NOT MET",
            "citation": None,
            "reasoning": "No relevant clinical documentation found for this criterion.",
        }

    context = "\n---\n".join(context_chunks)
    result = _parse(
        chat(_PROMPT.format(criterion=criterion, context=context)),
        criterion,
    )

    if result["status"] == "MET":
        if not result.get("citation"):
            result["status"] = "UNCLEAR"
            result["reasoning"] = "A MET result was returned without supporting evidence."
            return result

        if not _citation_is_verbatim(result["citation"], context):
            result["status"] = "UNCLEAR"
            result["reasoning"] = "The cited text was not found verbatim in the retrieved record."
            result["citation"] = None
            return result

        # Layer: citation relevance
        if not _citation_is_relevant(criterion, result["citation"]):
            result["status"] = "UNCLEAR"
            result["reasoning"] = (
                "Citation does not relate to this criterion's topic. "
                f"Original: {result['reasoning']}"
            )
            result["citation"] = None
            return result

        # Use deterministic math when one measurement is unambiguous. Ambiguous
        # cases receive a second focused local-model check.
        if _THRESHOLD_RE.search(criterion):
            numeric_result = _numeric_ok(criterion, result["citation"])
            if numeric_result is False or (
                numeric_result is None
                and not _llm_verify_numeric(criterion, result["citation"])
            ):
                result["status"] = "UNCLEAR"
                result["reasoning"] = (
                    "Numeric verification failed: value does not meet the threshold. "
                    f"Original: {result['reasoning']}"
                )

    return result


# ── Public API ────────────────────────────────────────────────────────

def check_all(
    criteria: list[str],
    patient_notes: str,
    patient_id: str,
    verbose: bool = True,
) -> list[dict]:
    """
    RAG-powered evaluation:
    1. Index patient notes in process memory
    2. For each criterion, retrieve relevant chunks
    3. Run check_criterion on retrieved context
    """
    from sa_checker.rag import index_patient, retrieve

    if verbose:
        print(f"  Indexing notes for {patient_id}...", end=" ", flush=True)
    n = index_patient(patient_id, patient_notes)
    if verbose:
        print(f"{n} chunks indexed")

    results = []
    for i, criterion in enumerate(criteria, 1):
        if verbose:
            print(f"  [{i}/{len(criteria)}] retrieving + checking...", end=" ", flush=True)
        chunks = retrieve(patient_id, criterion)
        result = check_criterion(criterion, chunks)
        if verbose:
            icon = {"MET": "✅", "NOT MET": "❌", "UNCLEAR": "⚠️"}.get(result["status"], "?")
            print(icon)
        results.append(result)

    return results
