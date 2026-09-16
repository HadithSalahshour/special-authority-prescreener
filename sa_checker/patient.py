"""Load a patient record and assemble their full clinical text from all visits."""

import json


def load_patient(patient_id: str, json_path: str) -> dict | None:
    with open(json_path) as f:
        data = json.load(f)
    for p in data["patients"]:
        if p["id"].upper() == patient_id.upper():
            return p
    return None


def assemble_notes(patient: dict) -> str:
    age = patient.get("age")
    gender = patient.get("gender")
    city = patient.get("city")

    lines = [
        f"Patient: {patient.get('name') or 'Unknown'}",
        f"Age: {age} years old" if age else "Age: Unknown",
    ]

    # Explicit adult/minor line — required for SA criteria like "Approval is limited to adults".
    # BM25 needs the word "adult" to appear verbatim; dense needs the concept stated clearly.
    if age:
        if int(age) >= 19:
            lines.append(
                f"Adult patient: yes (patient is {age} years old; "
                "BC age of majority is 19 years)"
            )
        else:
            lines.append(
                f"Adult patient: no (patient is {age} years old; "
                "BC age of majority is 19 years — this patient is a minor)"
            )

    if gender:
        lines.append(f"Gender: {'Male' if gender == 'M' else 'Female'}")
    if city:
        lines.append(f"City: {city}, British Columbia")

    for v in patient.get("visits", []):
        lines.append(f"\n[Visit {v['date']} — Reason: {v.get('reason', '')}]")
        if v.get("symptoms"):
            lines.append(f"Symptoms: {v['symptoms']}")
        if v.get("diagnosis"):
            lines.append(f"Diagnosis: {v['diagnosis']}")
        if v.get("prescribed"):
            lines.append(f"Prescribed: {v['prescribed']}")
        if v.get("doctor_notes"):
            lines.append(f"Doctor Notes: {v['doctor_notes']}")
    return "\n".join(lines)
