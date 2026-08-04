from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ServerConfig:
    resources_dir: Path
    output_dir: Path
    template_path: Path
    host: str
    port: int


def _value(environ: Mapping[str, str], name: str) -> str | None:
    value = environ.get(name, "").strip()
    return value or None


def _port(value: str | None) -> int:
    try:
        port = int(value) if value is not None else 8765
    except ValueError as error:
        raise ValueError(
            "AIPG_MCP_PORT must be an integer from 1 through 65535"
        ) from error
    if not 1 <= port <= 65535:
        raise ValueError("AIPG_MCP_PORT must be an integer from 1 through 65535")
    return port


def load_server_config(
    environ: Mapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> ServerConfig:
    values = os.environ if environ is None else environ
    local_app_data = Path(
        _value(values, "LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    )
    user_profile = Path(_value(values, "USERPROFILE") or Path.home())

    return ServerConfig(
        resources_dir=Path(
            _value(values, "AIPG_RESOURCES_DIR")
            or local_app_data / "Programs" / "AI Playground" / "resources"
        ),
        output_dir=Path(
            _value(values, "AIPG_OUTPUT_DIR")
            or user_profile / "Documents" / "AI-Playground" / "media"
        ),
        template_path=Path(
            _value(values, "AIPG_WORKFLOW_PATH")
            or project_root / "workflows" / "draft_image_fast.json"
        ),
        host=_value(values, "AIPG_MCP_HOST") or "0.0.0.0",
        port=_port(_value(values, "AIPG_MCP_PORT")),
    )