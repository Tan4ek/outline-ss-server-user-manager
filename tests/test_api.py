import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class ApiCompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name) / "config.yml"
        self.config.write_text("keys: []\n")
        self.env = patch.dict(os.environ, {"SS_CONFIG_PATH": str(self.config)})
        self.env.start()
        spec = importlib.util.spec_from_file_location(
            "outline_test_main", Path(__file__).resolve().parents[1] / "main.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.restart = patch.object(self.module, "restart_outline_ss_server")
        self.restart_mock = self.restart.start()
        self.client = TestClient(self.module.app)

    def tearDown(self):
        self.client.close()
        self.restart.stop()
        self.env.stop()
        self.directory.cleanup()

    def test_create_get_list_delete(self):
        body = {"user_id": "test-user", "sssecret": "test-only-password"}
        created = self.client.post("/user", json=body)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json(), {"user_id": "test-user", "port": 9000, "cipher": "chacha20-ietf-poly1305", "secret": "test-only-password"})
        self.assertEqual(self.client.get("/user/test-user").json(), created.json())
        self.assertEqual(self.client.get("/users").json(), [{"user_id": "test-user"}])
        self.assertEqual(self.client.post("/user", json=body).status_code, 409)
        deleted = self.client.delete("/user/test-user")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/user/test-user").status_code, 404)
        self.assertEqual(self.client.get("/users").json(), [])
        self.assertEqual(self.restart_mock.call_count, 2)

    def test_invalid_body_does_not_change_state(self):
        before = self.config.read_text()
        response = self.client.post("/user", json={"user_id": "test-user"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.config.read_text(), before)
        self.restart_mock.assert_not_called()

    def test_restart_endpoint(self):
        self.assertEqual(self.client.post("/restart-ss-server").status_code, 200)
        self.restart_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
