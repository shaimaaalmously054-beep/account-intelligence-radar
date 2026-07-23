import tempfile
import unittest
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services import database


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.temp_dir.name) / "radar-api-test.db"
        database.init_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def test_private_routes_require_authentication(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 401)

    def test_registration_sets_session_and_unlocks_private_history(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "name": "Radar User",
                "email": "radar@example.com",
                "password": "secure-password-123",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("air_session", response.cookies)
        history = self.client.get("/api/jobs")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json(), {"items": []})
        self.assertEqual(self.client.get("/api/auth/me").json()["email"], "radar@example.com")
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/jobs").status_code, 401)

    def test_legacy_report_dashboard_and_pdf_export_work_without_comparison(self):
        user = self.client.post(
            "/api/auth/register",
            json={
                "name": "Report User",
                "email": "report@example.com",
                "password": "secure-password-123",
            },
        ).json()
        now = datetime.now(timezone.utc).isoformat()
        job_id, report_id = str(uuid.uuid4()), str(uuid.uuid4())
        intelligence = {
            "company_name": "Legacy Company",
            "headquarters": "Madrid, Spain",
            "business_units": ["Consulting"],
            "products_and_services": [],
            "target_industries": [],
            "leadership": [],
            "strategic_initiatives": [],
            "evidence_links": [
                {"url": "https://example.com/annual-report", "description": "Annual report"}
            ],
        }
        with database.connect() as db:
            db.execute(
                """
                INSERT INTO jobs(
                    id, user_id, mode, query, request_json, status, stage, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    user["id"],
                    "company",
                    "Legacy Company",
                    json.dumps(
                        {
                            "mode": "company",
                            "company": {
                                "company_name": "Legacy Company",
                                "objective_prompt": "Identify business units.",
                            },
                        }
                    ),
                    "completed",
                    "Dashboard ready",
                    now,
                    now,
                ),
            )
            db.execute(
                """
                INSERT INTO reports(
                    id, job_id, user_id, company_slug, company_name, intelligence_json,
                    markdown, source_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    job_id,
                    user["id"],
                    "legacy-company",
                    "Legacy Company",
                    json.dumps(intelligence),
                    "# Legacy Company",
                    1,
                    now,
                ),
            )
        dashboard = self.client.get(f"/api/reports/{report_id}")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIsNone(dashboard.json()["comparison"])
        self.assertEqual(dashboard.json()["sources"][0]["url"], "https://example.com/annual-report")
        pdf = self.client.get(f"/api/reports/{report_id}/export/pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertIn("account-intelligence-legacy-company", pdf.headers["content-disposition"])
        self.assertTrue(pdf.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
