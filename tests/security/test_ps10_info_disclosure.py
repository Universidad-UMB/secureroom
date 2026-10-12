"""PS-10: No divulgación de información sensible (CA-10, RS-12, RS-13).

Objetivo: Comprobar que errores y respuestas no expongan trazas, rutas internas, SQL o secretos.
"""

import os
import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.auth.repository import in_memory_session_repo
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.main import app
from app.users.repository import in_memory_user_repo


class TestPS10InfoDisclosure(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()
        self.client = TestClient(app)

    def test_ps10_errors_do_not_leak_stack_traces_or_internals(self):
        """Triggering errors returns controlled messages, never internal tracebacks or SQL syntax."""
        # 1. Non-existent route
        resp_404 = self.client.get("/non-existent-endpoint-12345", headers={"Accept": "text/html"})
        self.assertEqual(resp_404.status_code, 404)
        self.assertNotIn("Traceback", resp_404.text)
        self.assertNotIn("/working_dir", resp_404.text)
        self.assertNotIn("File \"", resp_404.text)

        # 2. Malformed UUID parameter
        resp_bad_id = self.client.get("/rooms/invalid-not-uuid", headers={"Accept": "text/html"})
        self.assertNotIn("Traceback", resp_bad_id.text)
        self.assertNotIn("SELECT", resp_bad_id.text)
        self.assertNotIn("postgres", resp_bad_id.text)

    def test_ps10_repository_and_env_example_contain_no_real_secrets(self):
        """RS-13: Verifies .env.example contains placeholder values and no hardcoded production secrets."""
        env_example_path = ".env.example"
        self.assertTrue(os.path.exists(env_example_path))

        with open(env_example_path, "r") as f:
            content = f.read()

        # Placeholders should be present, not real production credentials
        self.assertIn("change_me", content.lower())
        self.assertNotIn("production_master_key", content)


if __name__ == "__main__":
    unittest.main()
