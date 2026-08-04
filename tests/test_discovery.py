import json
import tempfile
import unittest
from pathlib import Path

from aipg_comfy_mcp.discovery import DiscoveryError, discover_comfy_connection


def startup_line(port: int, token: str) -> str:
    payload = {
        "parameters": ["main.py", "--port", str(port)],
        "additionalEnvVariables": {"AIPG_LOOPBACK_TOKEN": token},
    }
    return f"08:21:27|comfyui-backend|starting comfyui with {json.dumps(payload)}\n"


class DiscoveryTests(unittest.TestCase):
    def test_uses_latest_startup_record_from_newest_log(self):
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            (resources / "aip-2026-08-02.log").write_text(startup_line(49000, "old-token"))
            (resources / "aip-2026-08-03.log").write_text(
                startup_line(49001, "stale-token") + startup_line(49002, "current-token")
            )

            connection = discover_comfy_connection(resources)

            self.assertEqual(connection.base_url, "http://127.0.0.1:49002")
            self.assertEqual(connection.token, "current-token")

    def test_rejects_log_without_startup_record(self):
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            (resources / "aip-empty.log").write_text("ComfyUI is running\n")

            with self.assertRaisesRegex(DiscoveryError, "startup record"):
                discover_comfy_connection(resources)

    def test_error_does_not_reveal_token(self):
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            secret = "do-not-leak-this-token"
            malformed = {
                "parameters": ["main.py", "--port"],
                "additionalEnvVariables": {"AIPG_LOOPBACK_TOKEN": secret},
            }
            (resources / "aip.log").write_text(
                f"comfyui-backend|starting comfyui with {json.dumps(malformed)}\n"
            )

            with self.assertRaises(DiscoveryError) as raised:
                discover_comfy_connection(resources)

            self.assertNotIn(secret, str(raised.exception))


if __name__ == "__main__":
    unittest.main()