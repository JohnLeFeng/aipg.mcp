import base64
import json
import tempfile
import unittest
from pathlib import Path

from aipg_comfy_mcp.comfy_client import ComfyClientError, GeneratedImage
from aipg_comfy_mcp.discovery import ComfyConnection, DiscoveryError
from aipg_comfy_mcp.server import create_server, run_http_server


def write_template(path: Path) -> None:
    template = {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": 1, "steps": 4},
            "_meta": {"title": "KSampler"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512},
            "_meta": {"title": "Empty Latent Image"},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ""},
            "_meta": {"title": "prompt"},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "nsfw"},
            "_meta": {"title": "negativePrompt"},
        },
    }
    path.write_text(json.dumps(template), encoding="utf-8")


class FakeClient:
    generated_workflow = None
    image_path: Path

    def __init__(self, connection, output_dir):
        self.connection = connection
        self.output_dir = output_dir

    async def check_status(self):
        return True

    async def generate(self, workflow, *, timeout_seconds=600):
        type(self).generated_workflow = workflow
        return GeneratedImage(prompt_id="prompt-1", path=type(self).image_path)


class FailingClient(FakeClient):
    async def generate(self, workflow, *, timeout_seconds=600):
        raise ComfyClientError("ComfyUI workflow execution failed")


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.template_path = root / "workflow.json"
        self.output_dir = root / "media"
        self.output_dir.mkdir()
        write_template(self.template_path)
        FakeClient.image_path = self.output_dir / "generated.png"
        FakeClient.image_path.write_bytes(b"png-data")
        self.secret = "must-not-appear"
        self.server = create_server(
            resources_dir=root,
            output_dir=self.output_dir,
            template_path=self.template_path,
            discovery_fn=lambda _: ComfyConnection(
                "http://127.0.0.1:49000", self.secret
            ),
            client_factory=FakeClient,
        )

    async def asyncTearDown(self):
        self.temporary_directory.cleanup()

    async def test_registers_status_and_generation_tools(self):
        tools = await self.server.list_tools()

        self.assertEqual(
            {tool.name for tool in tools}, {"comfyui_status", "generate_image"}
        )

    async def test_status_does_not_reveal_token(self):
        result = await self.server.call_tool("comfyui_status", {})

        text = result.content[0].text
        self.assertIn("connected", text.lower())
        self.assertNotIn(self.secret, text)

    async def test_generate_returns_text_and_png_content(self):
        result = await self.server.call_tool(
            "generate_image",
            {
                "prompt": "a copper robot",
                "negative_prompt": "blurry",
                "width": 768,
                "height": 512,
                "steps": 6,
                "seed": 42,
            },
        )

        self.assertFalse(result.is_error)
        self.assertEqual(FakeClient.generated_workflow["6"]["inputs"]["text"], "a copper robot")
        self.assertEqual(FakeClient.generated_workflow["3"]["inputs"]["seed"], 42)
        self.assertEqual(result.content[1].mime_type, "image/png")
        self.assertEqual(base64.b64decode(result.content[1].data), b"png-data")
        serialized = result.model_dump_json(by_alias=True)
        self.assertNotIn(self.secret, serialized)

    async def test_status_returns_explicit_discovery_error(self):
        server = create_server(
            resources_dir=Path(self.temporary_directory.name),
            output_dir=self.output_dir,
            template_path=self.template_path,
            discovery_fn=lambda _: (_ for _ in ()).throw(
                DiscoveryError("AI Playground ComfyUI startup record was not found")
            ),
            client_factory=FakeClient,
        )

        result = await server.call_tool("comfyui_status", {})

        self.assertTrue(result.is_error)
        self.assertIn("startup record was not found", result.content[0].text)

    async def test_generate_returns_explicit_client_error(self):
        server = create_server(
            resources_dir=Path(self.temporary_directory.name),
            output_dir=self.output_dir,
            template_path=self.template_path,
            discovery_fn=lambda _: ComfyConnection(
                "http://127.0.0.1:49000", self.secret
            ),
            client_factory=FailingClient,
        )

        result = await server.call_tool("generate_image", {"prompt": "test"})

        self.assertTrue(result.is_error)
        self.assertEqual(result.content[0].text, "ComfyUI workflow execution failed")
        self.assertNotIn(self.secret, result.model_dump_json(by_alias=True))

    def test_http_server_runs_stateless_for_clean_restarts(self):
        class RecordingServer:
            call = None

            def run(self, transport, **kwargs):
                self.call = (transport, kwargs)

        server = RecordingServer()

        run_http_server(server, host="127.0.0.1", port=9876)

        self.assertEqual(server.call[0], "streamable-http")
        self.assertEqual(server.call[1]["host"], "127.0.0.1")
        self.assertEqual(server.call[1]["port"], 9876)
        self.assertEqual(server.call[1]["streamable_http_path"], "/mcp")
        self.assertTrue(server.call[1]["stateless_http"])
        security = server.call[1]["transport_security"]
        self.assertTrue(security.enable_dns_rebinding_protection)
        self.assertIn("host.docker.internal:*", security.allowed_hosts)
        self.assertIn("127.0.0.1:*", security.allowed_hosts)


if __name__ == "__main__":
    unittest.main()