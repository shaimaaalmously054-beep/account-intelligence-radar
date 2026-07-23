import unittest

from services.source_service import (
    build_source_records,
    normalize_url,
    report_sources,
)


class SourceServiceTests(unittest.TestCase):
    def test_url_normalization_rejects_unsafe_schemes(self):
        self.assertIsNone(normalize_url("javascript:alert(1)"))
        self.assertIsNone(normalize_url("file:///etc/passwd"))

    def test_url_normalization_removes_tracking_and_deduplicates_scheme_variants(self):
        normalized = normalize_url(
            "HTTPS://www.Example.com/report/?utm_source=newsletter&id=42#section"
        )
        self.assertEqual(normalized[0], "https://example.com/report?id=42")
        self.assertEqual(normalized[1], "//example.com/report?id=42")

    def test_search_results_retain_real_context_and_extraction_status(self):
        records = build_source_records(
            [
                {
                    "title": "Annual Report",
                    "link": "https://example.com/annual-report.pdf",
                    "snippet": "The company expanded its data platform.",
                    "rank": 1,
                    "search_query": "Example annual report",
                }
            ],
            ["https://example.com/annual-report.pdf"],
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].extraction_status, "extracted")
        self.assertEqual(records[0].source_type, "Financial Report")
        self.assertEqual(records[0].search_query, "Example annual report")

    def test_legacy_evidence_links_are_available_as_sources(self):
        sources = report_sources(
            {
                "evidence_links": [
                    {"url": "https://example.com/report", "description": "Annual report"}
                ]
            }
        )
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "Annual report")
        self.assertEqual(sources[0]["extraction_status"], "evidence")


if __name__ == "__main__":
    unittest.main()
