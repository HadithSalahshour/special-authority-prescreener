import json
import tempfile
import unittest
from pathlib import Path

from sa_checker.patient import assemble_notes, load_patient


class PatientTests(unittest.TestCase):
    def test_load_and_assemble_synthetic_patient(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patients.json"
            path.write_text(
                json.dumps(
                    {
                        "patients": [
                            {
                                "id": "DEMO-001",
                                "name": "Demo Patient 001",
                                "age": 45,
                                "gender": "F",
                                "city": "Victoria",
                                "visits": [
                                    {
                                        "date": "2026-01-01",
                                        "reason": "Follow-up",
                                        "diagnosis": "Example diagnosis",
                                        "doctor_notes": "Example local-only note.",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            patient = load_patient("demo-001", str(path))
            notes = assemble_notes(patient)

            self.assertIn("Demo Patient 001", notes)
            self.assertIn("Adult patient: yes", notes)
            self.assertIn("Example local-only note.", notes)


if __name__ == "__main__":
    unittest.main()
