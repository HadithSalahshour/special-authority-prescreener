"""Load a patient record and assemble their full clinical text from all visits."""

import json


def load_patient(patient_id: str, json_path: str) -> dict | None:
    with open(json_path) as f:
        data = json.load(f)

    for patient in data["patients"]:
        if patient["id"].upper() == patient_id.upper():
            return patient

    return None


def assemble_notes(patient: dict) -> str:
    age = patient.get("age")
    gender = patient.get("gender")
    city = patient.get("city")

    lines = [
        f"Patient: {patient.get('name') or 'Unknown'}",
        f"Age: {age} years old" if age else "Age: Unknown",
    ]

    # Explicit adult/minor line — required for SA criteria like
    # "Approval is limited to adults".
    # BM25 needs the word "adult" to appear verbatim;
    # dense retrieval needs the concept stated clearly.
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
        normalized_gender = str(gender).strip().upper()
        gender_label = {
            "M": "Male",
            "F": "Female",
        }.get(normalized_gender, "Unknown")
        lines.append(f"Gender: {gender_label}")

    if city:
        lines.append(f"City: {city}, British Columbia")

    for visit in patient.get("visits", []):
        lines.append(
            f"\n[Visit {visit['date']} — "
            f"Reason: {visit.get('reason', '')}]"
        )

        if visit.get("symptoms"):
            lines.append(f"Symptoms: {visit['symptoms']}")

        if visit.get("diagnosis"):
            lines.append(f"Diagnosis: {visit['diagnosis']}")

        if visit.get("prescribed"):
            lines.append(f"Prescribed: {visit['prescribed']}")

        if visit.get("doctor_notes"):
            lines.append(
                f"Doctor Notes: {visit['doctor_notes']}"
            )

    return "\n".join(lines)
