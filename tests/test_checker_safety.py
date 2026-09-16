import unittest

from sa_checker.checker import (
    _citation_is_relevant,
    _citation_is_verbatim,
    _numeric_ok,
)


class CheckerSafetyTests(unittest.TestCase):
    def test_citation_must_be_present_in_context(self):
        context = "Diagnosis: heart failure\nLVEF measured at 38%."
        self.assertTrue(_citation_is_verbatim("LVEF measured at 38%.", context))
        self.assertFalse(_citation_is_verbatim("LVEF measured at 30%.", context))

    def test_relevance_uses_citation_not_model_reasoning(self):
        criterion = "Ferritin must be ≤ 300 mcg/L"
        self.assertTrue(_citation_is_relevant(criterion, "Ferritin measured at 180 mcg/L"))
        self.assertFalse(
            _citation_is_relevant(criterion, "Ejection fraction measured at 38%")
        )

    def test_numeric_less_than_or_equal_passes(self):
        self.assertIs(_numeric_ok("LVEF must be ≤ 40%", "LVEF measured at 38%"), True)

    def test_numeric_less_than_or_equal_fails(self):
        self.assertIs(_numeric_ok("LVEF must be ≤ 40%", "LVEF measured at 45%"), False)

    def test_numeric_matching_units_ignore_other_numbers(self):
        criterion = "Eosinophils must be ≥ 300 cells/µL"
        evidence = "Eosinophils measured at 847 cells/µL after 2 exacerbations"
        self.assertIs(_numeric_ok(criterion, evidence), True)

    def test_ambiguous_numeric_evidence_abstains(self):
        criterion = "LVEF must be ≤ 40%"
        evidence = "LVEF ranged from 35% to 45%"
        self.assertIsNone(_numeric_ok(criterion, evidence))


if __name__ == "__main__":
    unittest.main()
