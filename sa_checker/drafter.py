"""
For each NOT MET / UNCLEAR criterion, generate a concrete note
describing what documentation would be needed to satisfy it.
"""

from sa_checker.local_llm import chat

_PROMPT = """A patient's clinical notes do not satisfy this BC PharmaCare Special Authority criterion for {drug}.

Criterion: {criterion}
Current status: {status}

Write 1-2 specific, actionable sentences stating exactly what clinical documentation or evidence would need to be present in the notes to satisfy this criterion for {drug}. Only reference lab tests, thresholds, or specialist types that are directly relevant to {drug} and this criterion. Do not invent requirements from unrelated conditions or drugs. Do not repeat the criterion verbatim. Be direct."""


def draft_gap(criterion: str, status: str, drug: str = "this drug") -> str:
    return chat(
        _PROMPT.format(criterion=criterion, status=status, drug=drug)
    ).strip()
