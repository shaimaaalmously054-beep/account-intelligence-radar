import io
import unittest

from pypdf import PdfReader

from services.pdf_service import render_report_pdf


class PdfServiceTests(unittest.TestCase):
    def test_pdf_contains_report_findings_and_all_source_urls(self):
        sources = [
            {
                "id": str(index),
                "title": f"Source {index}",
                "url": f"https://example.com/reports/{index}",
                "domain": "example.com",
                "publisher": "example.com",
                "source_type": "Financial Report",
                "extraction_status": "extracted",
                "snippet": "Evidence about a strategic initiative. " * 8,
                "evidence": [f"Supported finding {index}"],
            }
            for index in range(1, 22)
        ]
        payload = {
            "id": "report-123",
            "company_name": "Example Holdings",
            "mode": "company",
            "query": "Example Holdings",
            "status": "completed",
            "created_at": "2026-07-23T09:00:00+00:00",
            "source_count": len(sources),
            "summary": {
                "high_level": "Example Holdings has multiple evidence-backed initiatives.",
                "major_findings": ["Cloud platform expansion", "Supply-chain modernization"],
            },
            "search_information": {"objective": "Identify strategic initiatives."},
            "intelligence": {
                "company_name": "Example Holdings",
                "headquarters": "Madrid, Spain",
                "business_units": ["Digital"],
                "products_and_services": ["Analytics"],
                "target_industries": ["Manufacturing"],
                "leadership": [{"name": "Alex Smith", "title": "CEO"}],
                "strategic_initiatives": [
                    {"category": "Cloud", "description": "Expanded the cloud platform."}
                ],
            },
            "sources": sources,
            "search_results": sources,
            "comparison": None,
        }
        content = render_report_pdf(payload)
        self.assertTrue(content.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(content))
        self.assertGreater(len(reader.pages), 2)
        self.assertTrue(any(page.get("/Annots") for page in reader.pages))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Example Holdings", text)
        self.assertIn("Cloud platform expansion", text)
        self.assertIn("https://example.com/reports/1", text)
        self.assertIn("https://example.com/reports/21", text)


if __name__ == "__main__":
    unittest.main()
