import tempfile
import unittest
from pathlib import Path

from services import database
from services.auth_service import (
    authenticate,
    create_session,
    create_user,
    delete_session,
    hash_password,
    user_for_session,
    verify_password,
)


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.temp_dir.name) / "radar-test.db"
        database.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_passwords_are_salted_and_verified(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct horse battery staple", first))
        self.assertFalse(verify_password("incorrect", first))
        self.assertNotIn("correct horse", first)

    def test_user_authentication_and_session_lifecycle(self):
        user = create_user("Mazen Zawal", "mazen@example.com", "a-secure-password")
        self.assertEqual(
            authenticate("MAZEN@example.com", "a-secure-password")["id"], user["id"]
        )
        self.assertIsNone(authenticate("mazen@example.com", "wrong"))
        token = create_session(user["id"])
        self.assertEqual(user_for_session(token)["email"], "mazen@example.com")
        delete_session(token)
        self.assertIsNone(user_for_session(token))


if __name__ == "__main__":
    unittest.main()
