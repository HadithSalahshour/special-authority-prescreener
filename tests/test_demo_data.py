import json
import unittest
from pathlib import Path


class DemoCriteriaTests(unittest.TestCase):
    def test_bundled_criteria_are_fictional(self):
        data_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "demo_criteria_cache.json"
        )
        demo_data = json.loads(data_path.read_text(encoding="utf-8"))

        self.assertTrue(demo_data, "The demo criteria file must not be empty")

        serialized_data = json.dumps(demo_data).lower()
        self.assertNotIn("http://", serialized_data)
        self.assertNotIn("https://", serialized_data)

        for drug_name, entry in demo_data.items():
            self.assertTrue(
                drug_name.startswith("demo "),
                f"Non-demo drug found: {drug_name}",
            )
            self.assertEqual(
                entry.get("source_file"),
                "synthetic-demo",
            )

            criteria = entry.get("criteria")
            self.assertIsInstance(criteria, list)
            self.assertTrue(criteria, f"No criteria found for {drug_name}")
            self.assertTrue(
                all(
                    isinstance(criterion, str) and criterion.strip()
                    for criterion in criteria
                )
            )


if __name__ == "__main__":
    unittest.main()
