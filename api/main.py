"""Local-only FastAPI interface for the Special Authority pre-screen."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from sa_checker.checker import check_all
from sa_checker.drafter import draft_gap
from sa_checker.ingest import cache_mode, get_criteria_for_drug, list_drugs
from sa_checker.patient import assemble_notes, load_patient


ROOT = Path(__file__).resolve().parents[1]
PATIENTS_JSON = ROOT / "data" / "demo_patients.json"
INDEX_HTML = ROOT / "api" / "index.html"

app = FastAPI(
    title="BC Special Authority Pre-Screen",
    version="0.1.0",
    description="Local research prototype using synthetic demonstration records.",
)


class SACheckRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9-]+$")
    drug: str = Field(min_length=1, max_length=200)


@app.middleware("http")
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "local-synthetic-demo",
        "patient_data": "synthetic-only",
    }


@app.get("/sa-drugs")
def sa_drugs():
    return {
        "drugs": list_drugs(),
        "mode": cache_mode(),
        "notice": (
            "Fictional criteria for software demonstration only."
            if cache_mode() == "fictional-demo"
            else "Local policy snapshot; verify against current BC PharmaCare criteria."
        ),
    }


@app.get("/sa-patients")
def sa_patients():
    data = json.loads(PATIENTS_JSON.read_text(encoding="utf-8"))
    patients = []
    for patient in data.get("patients", []):
        if patient.get("is_synthetic_profile") is not True:
            continue
        visits = patient.get("visits") or []
        last = visits[-1] if visits else None
        patients.append(
            {
                "id": patient["id"],
                "name": patient.get("name") or patient["id"],
                "age": patient.get("age"),
                "city": patient.get("city"),
                "gender": patient.get("gender"),
                "n_visits": len(visits),
                "last_date": last.get("date") if last else None,
                "last_dx": (
                    last.get("diagnosis", "").split(";")[0].strip()
                    if last
                    else None
                ),
            }
        )
    return {"patients": patients, "notice": data.get("notice")}


@app.post("/sa-check")
def sa_check(request: SACheckRequest, response: Response):
    patient = load_patient(request.patient_id, str(PATIENTS_JSON))
    if not patient or patient.get("is_synthetic_profile") is not True:
        raise HTTPException(status_code=404, detail="Synthetic demo patient not found")

    matched_drug, criteria = get_criteria_for_drug(request.drug)
    if not criteria:
        raise HTTPException(status_code=404, detail="No matching policy criteria found")

    try:
        results = check_all(
            criteria,
            assemble_notes(patient),
            patient_id=patient["id"],
            verbose=False,
        )
        for result in results:
            result["needed"] = (
                draft_gap(result["criterion"], result["status"], matched_drug)
                if result["status"] in {"NOT MET", "UNCLEAR"}
                else None
            )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Local model unavailable or evaluation failed. Check Ollama and retry.",
        ) from exc

    met_count = sum(result["status"] == "MET" for result in results)
    has_unclear = any(result["status"] == "UNCLEAR" for result in results)
    if met_count == len(results):
        verdict = "POTENTIALLY_ELIGIBLE"
    elif has_unclear:
        verdict = "MANUAL_REVIEW_REQUIRED"
    else:
        verdict = "DOCUMENTATION_GAPS_FOUND"

    response.headers["X-Clinical-Use"] = "research-prototype"
    return {
        "drug": matched_drug,
        "patient_id": patient["id"],
        "patient_name": patient.get("name") or patient["id"],
        "verdict": verdict,
        "met_count": met_count,
        "total": len(results),
        "results": results,
        "disclaimer": (
            "Research pre-screen only. A clinician must verify current policy "
            "criteria and the complete patient record."
        ),
    }
