import unittest
from pathlib import Path

from aipg_comfy_mcp.config import load_server_config


class ServerConfigTests(unittest.TestCase):
    def setUp(self):
        self.environ = {
            "LOCALAPPDATA": r"C:\Users\Example\AppData\Local",
            "USERPROFILE": r"C:\Users\Example",
        }
        self.project_root = Path(r"C:\repo")

    def test_uses_portable_windows_defaults(self):
        config = load_server_config(self.environ, project_root=self.project_root)

        self.assertEqual(
            config.resources_dir,
            Path(
                r"C:\Users\Example\AppData\Local\Programs\AI Playground\resources"
            ),
        )
        self.assertEqual(
            config.output_dir,
            Path(r"C:\Users\Example\Documents\AI-Playground\media"),
        )
        self.assertEqual(
            config.template_path,
            Path(r"C:\repo\workflows\draft_image_fast.json"),
        )
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 8765)

    def test_uses_environment_overrides(self):
        environ = {
            **self.environ,
            "AIPG_RESOURCES_DIR": r"D:\AI\resources",
            "AIPG_OUTPUT_DIR": r"D:\AI\media",
            "AIPG_WORKFLOW_PATH": r"D:\AI\workflow.json",
            "AIPG_MCP_HOST": "127.0.0.1",
            "AIPG_MCP_PORT": "9876",
        }

        config = load_server_config(environ, project_root=self.project_root)

        self.assertEqual(config.resources_dir, Path(r"D:\AI\resources"))
        self.assertEqual(config.output_dir, Path(r"D:\AI\media"))
        self.assertEqual(config.template_path, Path(r"D:\AI\workflow.json"))
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 9876)

    def test_ignores_whitespace_only_overrides(self):
        environ = {
            **self.environ,
            "AIPG_RESOURCES_DIR": "  ",
            "AIPG_OUTPUT_DIR": "  ",
            "AIPG_WORKFLOW_PATH": "  ",
            "AIPG_MCP_HOST": "  ",
            "AIPG_MCP_PORT": "  ",
        }

        config = load_server_config(environ, project_root=self.project_root)

        self.assertEqual(
            config.resources_dir,
            Path(
                r"C:\Users\Example\AppData\Local\Programs\AI Playground\resources"
            ),
        )
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 8765)

    def test_rejects_invalid_port(self):
        for value in ("abc", "0", "65536"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "AIPG_MCP_PORT"):
                    load_server_config(
                        {**self.environ, "AIPG_MCP_PORT": value},
                        project_root=self.project_root,
                    )


if __name__ == "__main__":
    unittest.main()