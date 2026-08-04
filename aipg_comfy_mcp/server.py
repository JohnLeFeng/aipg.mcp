from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from mcp.server import MCPServer
from mcp.server.mcpserver.utilities.types import Image
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolResult, TextContent

from .comfy_client import ComfyClient, ComfyClientError
from .config import load_server_config
from .discovery import ComfyConnection, DiscoveryError, discover_comfy_connection
from .workflow import GenerationRequest, WorkflowError, build_workflow


def _load_template(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Draft Image workflow template could not be loaded") from error
    if not isinstance(data, dict):
        raise RuntimeError("Draft Image workflow template is invalid")
    return data


def _error_result(error: Exception) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=str(error))],
        is_error=True,
    )


def create_server(
    *,
    resources_dir: Path,
    output_dir: Path,
    template_path: Path,
    discovery_fn: Callable[[Path], ComfyConnection] = discover_comfy_connection,
    client_factory: Callable[[ComfyConnection, Path], ComfyClient] = ComfyClient,
) -> MCPServer:
    server = MCPServer(
        "aipg-comfyui",
        title="AI Playground ComfyUI",
        description="Generate images with AI Playground's local ComfyUI backend.",
        instructions=(
            "Use generate_image only when the user asks to create an image. "
            "Keep dimensions separate from the descriptive prompt."
        ),
        version="1.0.0",
    )

    @server.tool()
    async def comfyui_status() -> CallToolResult:
        """Check whether AI Playground's ComfyUI backend is reachable."""
        try:
            connection = discovery_fn(resources_dir)
            client = client_factory(connection, output_dir)
            await client.check_status()
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Connected to AI Playground ComfyUI at {connection.base_url}",
                    )
                ],
                is_error=False,
            )
        except (DiscoveryError, ComfyClientError) as error:
            return _error_result(error)

    @server.tool()
    async def generate_image(
        prompt: str,
        negative_prompt: str = "nsfw",
        width: int = 512,
        height: int = 512,
        steps: int = 4,
        seed: int = -1,
    ) -> CallToolResult:
        """Generate an image from a detailed prompt using Draft Image - Fast.

        Width and height must be multiples of 8 from 64 through 2048. Use seed
        -1 for a random result. The default four steps match the LCM workflow.
        """
        try:
            template = _load_template(template_path)
            workflow = build_workflow(
                template,
                GenerationRequest(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    seed=seed,
                ),
            )
            connection = discovery_fn(resources_dir)
            client = client_factory(connection, output_dir)
            generated = await client.generate(workflow)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Generated image: {generated.path}",
                    ),
                    Image(path=generated.path).to_image_content(),
                ],
                is_error=False,
            )
        except (DiscoveryError, WorkflowError, ComfyClientError, RuntimeError) as error:
            return _error_result(error)

    return server


def run_http_server(server: MCPServer, *, host: str, port: int) -> None:
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "host.docker.internal:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://host.docker.internal:*",
        ],
    )
    server.run(
        "streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        transport_security=transport_security,
    )


def main() -> None:
    config = load_server_config()
    server = create_server(
        resources_dir=config.resources_dir,
        output_dir=config.output_dir,
        template_path=config.template_path,
    )
    run_http_server(server, host=config.host, port=config.port)


if __name__ == "__main__":
    main()