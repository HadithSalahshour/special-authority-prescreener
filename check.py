#!/usr/bin/env python3
"""
BC PharmaCare Special Authority Checker
Usage:
  python check.py --ingest                              # parse all PDFs, build index
  python check.py --list                                # show ingested drugs
  python check.py DEMO-001 "demo migraine preventive"
  python check.py --demo                                # run synthetic demo cases
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sa_checker.ingest import ingest_all, get_criteria_for_drug, list_drugs
from sa_checker.patient import load_patient, assemble_notes
from sa_checker.checker import check_all
from sa_checker.drafter import draft_gap

BASE = os.path.dirname(os.path.abspath(__file__))
POLICIES_DIR = os.path.join(BASE, ".local", "policies")
PATIENTS_JSON = os.path.join(BASE, "data", "demo_patients.json")

LINE = "=" * 70


def run_check(patient_id: str, drug_query: str):
    patient = load_patient(patient_id, PATIENTS_JSON)
    if not patient:
        print(f"ERROR: Synthetic patient '{patient_id}' not found in the demo dataset")
        return

    matched_drug, criteria = get_criteria_for_drug(drug_query)
    if not criteria:
        print(f"ERROR: No criteria found for '{drug_query}'.")
        print("Run --list to see available drugs, or --ingest to rebuild the index.")
        return

    notes = assemble_notes(patient)
    name = patient.get("name") or patient_id
    age = patient.get("age") or "?"

    print(f"\n{LINE}")
    print(f"  BC PHARMACARE — SPECIAL AUTHORITY CHECK")
    print(LINE)
    print(f"  Drug:    {matched_drug.upper()}")
    print(f"  Patient: {name}  |  ID: {patient_id}  |  Age: {age}")
    print(LINE)
    print()

    print(f"Evaluating {len(criteria)} criteria...\n")
    results = check_all(criteria, notes, patient_id=patient_id, verbose=True)

    # Draft gap notes for unmet criteria
    print("\nDrafting documentation guidance for unmet criteria...")
    for r in results:
        if r["status"] in ("NOT MET", "UNCLEAR"):
            r["needed"] = draft_gap(r["criterion"], r["status"], matched_drug)

    # Summary
    all_met = all(r["status"] == "MET" for r in results)
    met_count = sum(1 for r in results if r["status"] == "MET")

    # Per-criterion report
    print(f"\n{LINE}")
    print(f"  PER-CRITERION BREAKDOWN")
    print(LINE)

    for i, r in enumerate(results, 1):
        badge = {"MET": "✅ MET", "NOT MET": "❌ NOT MET", "UNCLEAR": "⚠️  UNCLEAR"}.get(
            r["status"], r["status"]
        )
        print(f"\nCriterion {i}:")
        print(f"  {r['criterion']}")
        print(f"  ─ Status:   {badge}")
        if r.get("citation"):
            print(f"  ─ Evidence: \"{r['citation']}\"")
        if r.get("reasoning"):
            print(f"  ─ Reason:   {r['reasoning']}")
        if r.get("needed"):
            print(f"  ─ Needed:   {r['needed']}")

    # Verdict
    print(f"\n{LINE}")
    if all_met:
        print("  SCREEN: ✅  POTENTIALLY ELIGIBLE — CLINICIAN REVIEW REQUIRED")
    elif any(r["status"] == "UNCLEAR" for r in results):
        print("  SCREEN: ⚠️  MANUAL REVIEW REQUIRED")
    else:
        print("  SCREEN: ❌  REQUIRED DOCUMENTATION NOT FOUND")
    print(f"  Criteria met: {met_count} / {len(results)}")
    print(LINE)
    print()


def run_demo():
    demos = [
        (
            "DEMO-001",
            "demo migraine preventive",
            "Synthetic qualifying documentation",
        ),
        (
            "DEMO-001",
            "demo migraine preventive",
            "Synthetic documentation-gap case",
        ),
        (
            "DEMO-004",
            "demo inhaled therapy for copd",
            "Synthetic non-qualifying case",
        ),
    ]
    for patient_id, drug, description in demos:
        print(f"\n{'#' * 70}")
        print(f"# DEMO: {description}")
        print(f"{'#' * 70}")
        run_check(patient_id, drug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BC PharmaCare Special Authority Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python check.py --ingest\n"
            "  python check.py --list\n"
            "  python check.py DEMO-001 \"demo migraine preventive\"\n"
            "  python check.py --demo\n"
        ),
    )
    parser.add_argument("--ingest", action="store_true",
                        help="Parse all PDFs and build criteria index")
    parser.add_argument("--list", action="store_true",
                        help="List all indexed drugs")
    parser.add_argument("--demo", action="store_true",
                        help="Run 3 contrast demo checks")
    parser.add_argument("patient", nargs="?", metavar="PATIENT_ID",
                        help="Synthetic demo patient ID, e.g. DEMO-001")
    parser.add_argument("drug", nargs="?", metavar="DRUG_QUERY",
                        help="Drug name query, e.g. 'ferric carboxymaltose heart failure'")
    args = parser.parse_args()

    if args.ingest:
        print("Ingesting policy PDFs from:", POLICIES_DIR)
        results = ingest_all(POLICIES_DIR)
        print(f"\nDone — {len(results)} drugs indexed:")
        for r in results:
            print(f"  {r['drug']} — {r['criteria_count']} criteria  [{r['file']}]")

    elif args.list:
        drugs = list_drugs()
        if drugs:
            print("Available drugs:")
            for d in drugs:
                print(f"  • {d}")
        else:
            print("No drugs indexed yet. Run: python check.py --ingest")

    elif args.demo:
        run_demo()

    elif args.patient and args.drug:
        run_check(args.patient, args.drug)

    else:
        parser.print_help()
