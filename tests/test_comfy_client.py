import json
import tempfile
import unittest
from pathlib import Path

import httpx

from aipg_comfy_mcp.comfy_client import ComfyClient, ComfyClientError
from aipg_comfy_mcp.discovery import ComfyConnection


class ComfyClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_check_status_calls_queue(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/queue")
            self.assertEqual(request.headers["Authorization"], "Bearer secret")
            return httpx.Response(200, json={"queue_running": [], "queue_pending": []})

        client = ComfyClient(
            ComfyConnection("http://127.0.0.1:49000", "secret"),
            Path(tempfile.gettempdir()),
            transport=httpx.MockTransport(handler),
        )

        self.assertTrue(await client.check_status())

    async def test_submits_polls_and_returns_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            expected_path = output_dir / "generated.png"
            expected_path.write_bytes(b"png-data")
            history_calls = 0

            def handler(request: httpx.Request) -> httpx.Response:
                nonlocal history_calls
                self.assertEqual(request.headers["Authorization"], "Bearer secret")
                if request.url.path == "/prompt":
                    payload = json.loads(request.content)
                    self.assertEqual(payload["prompt"], {"1": {"class_type": "Test"}})
                    return httpx.Response(200, json={"prompt_id": "prompt-1"})
                history_calls += 1
                if history_calls == 1:
                    return httpx.Response(200, json={})
                return httpx.Response(
                    200,
                    json={
                        "prompt-1": {
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "generated.png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            },
                            "status": {"status_str": "success"},
                        }
                    },
                )

            client = ComfyClient(
                ComfyConnection("http://127.0.0.1:49000", "secret"),
                output_dir,
                transport=httpx.MockTransport(handler),
                poll_interval=0,
            )

            result = await client.generate({"1": {"class_type": "Test"}})

            self.assertEqual(result.prompt_id, "prompt-1")
            self.assertEqual(result.path, expected_path)
            self.assertEqual(history_calls, 2)

    async def test_reports_execution_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/prompt":
                return httpx.Response(200, json={"prompt_id": "failed"})
            return httpx.Response(
                200,
                json={"failed": {"outputs": {}, "status": {"status_str": "error"}}},
            )

        client = ComfyClient(
            ComfyConnection("http://127.0.0.1:49000", "secret"),
            Path(tempfile.gettempdir()),
            transport=httpx.MockTransport(handler),
            poll_interval=0,
        )

        with self.assertRaisesRegex(ComfyClientError, "execution failed"):
            await client.generate({"1": {}}, timeout_seconds=1)

    async def test_times_out(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/prompt":
                return httpx.Response(200, json={"prompt_id": "slow"})
            return httpx.Response(200, json={})

        client = ComfyClient(
            ComfyConnection("http://127.0.0.1:49000", "secret"),
            Path(tempfile.gettempdir()),
            transport=httpx.MockTransport(handler),
            poll_interval=0,
        )

        with self.assertRaisesRegex(ComfyClientError, "timed out"):
            await client.generate({"1": {}}, timeout_seconds=0)

    async def test_rejects_output_outside_media_directory(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/prompt":
                return httpx.Response(200, json={"prompt_id": "unsafe"})
            return httpx.Response(
                200,
                json={
                    "unsafe": {
                        "outputs": {
                            "9": {
                                "images": [
                                    {
                                        "filename": "secret.txt",
                                        "subfolder": "..",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                        "status": {"status_str": "success"},
                    }
                },
            )

        client = ComfyClient(
            ComfyConnection("http://127.0.0.1:49000", "secret"),
            Path(tempfile.gettempdir()) / "media",
            transport=httpx.MockTransport(handler),
            poll_interval=0,
        )

        with self.assertRaisesRegex(ComfyClientError, "outside"):
            await client.generate({"1": {}}, timeout_seconds=1)


if __name__ == "__main__":
    unittest.main()