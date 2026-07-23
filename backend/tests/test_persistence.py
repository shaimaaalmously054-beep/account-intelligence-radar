import tempfile
import unittest
from pathlib import Path

from models.schemas import InputMode, JobStatus
from services import database, job_store
from services.auth_service import create_user


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.temp_dir.name) / "radar-test.db"
        database.init_db()
        self.owner = create_user(
            "Owner User", "owner@example.com", "long-enough-password"
        )
        self.other = create_user(
            "Other User", "other@example.com", "another-good-password"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_jobs_are_durable_and_owner_scoped(self):
        job = job_store.create_job(
            InputMode.COMPANY,
            self.owner["id"],
            "Acme Corporation",
            {"mode": "company", "company": {"company_name": "Acme Corporation"}},
        )
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(
            job_store.get_job(job.job_id, self.owner["id"]).query, "Acme Corporation"
        )
        self.assertIsNone(job_store.get_job(job.job_id, self.other["id"]))
        self.assertEqual(len(job_store.list_jobs(self.owner["id"])), 1)
        self.assertEqual(job_store.list_jobs(self.other["id"]), [])

    def test_delete_is_owner_scoped(self):
        job = job_store.create_job(
            InputMode.GEOGRAPHY,
            self.owner["id"],
            "Riyadh, Saudi Arabia",
            {"mode": "geography"},
        )
        self.assertFalse(job_store.delete_job(job.job_id, self.other["id"]))
        self.assertTrue(job_store.delete_job(job.job_id, self.owner["id"]))


if __name__ == "__main__":
    unittest.main()
