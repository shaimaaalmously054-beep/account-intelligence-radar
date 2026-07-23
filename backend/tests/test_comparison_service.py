import unittest

from services.comparison_service import compare_reports, normalize_text


class ComparisonServiceTests(unittest.TestCase):
    def test_normalization_handles_business_aliases_and_formatting(self):
        self.assertEqual(
            normalize_text("Artificial Intelligence Transformation Programme"),
            "ai transformation program",
        )

    def test_comparison_ignores_order_and_minor_wording(self):
        previous = {
            "headquarters": "Riyadh, Saudi Arabia",
            "business_units": ["Energy", "Digital"],
            "strategic_initiatives": [
                {
                    "description": "Artificial Intelligence transformation program",
                    "category": "AI",
                }
            ],
        }
        current = {
            "headquarters": "Riyadh, Saudi Arabia",
            "business_units": ["Digital", "Energy"],
            "strategic_initiatives": [
                {
                    "description": "AI transformation programme",
                    "category": "Artificial Intelligence",
                }
            ],
        }
        result = compare_reports(previous, current)
        self.assertEqual(result["counts"]["new"], 0)
        self.assertEqual(result["counts"]["removed"], 0)
        self.assertEqual(result["counts"]["changed"], 0)

    def test_comparison_detects_new_changed_and_removed_intelligence(self):
        previous = {
            "headquarters": "London",
            "leadership": [{"name": "Alex Smith", "title": "Chief Executive Officer"}],
            "business_units": ["Legacy Systems"],
        }
        current = {
            "headquarters": "New York",
            "leadership": [{"name": "Alex Smith", "title": "Board Chair"}],
            "business_units": ["Cloud Platforms"],
        }
        result = compare_reports(previous, current)
        self.assertGreaterEqual(result["counts"]["changed"], 2)
        self.assertGreaterEqual(result["counts"]["new"], 1)
        self.assertGreaterEqual(result["counts"]["removed"], 1)


if __name__ == "__main__":
    unittest.main()
