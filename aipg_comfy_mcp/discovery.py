from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


STARTUP_MARKER = "starting comfyui with "


class DiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ComfyConnection:
    base_url: str
    token: str


def discover_comfy_connection(resources_dir: Path) -> ComfyConnection:
    log_paths = sorted(
        resources_dir.glob("aip-*.log"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    startup_json: str | None = None
    for log_path in log_paths:
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            marker_index = line.lower().find(STARTUP_MARKER)
            if marker_index >= 0:
                startup_json = line[marker_index + len(STARTUP_MARKER) :]

    if startup_json is None:
        raise DiscoveryError("AI Playground ComfyUI startup record was not found")

    try:
        payload = json.loads(startup_json)
        parameters = payload["parameters"]
        port_index = parameters.index("--port") + 1
        port = int(parameters[port_index])
        token = payload["additionalEnvVariables"]["AIPG_LOOPBACK_TOKEN"]
        if not isinstance(token, str) or not token:
            raise ValueError("empty token")
    except (KeyError, ValueError, TypeError, IndexError, json.JSONDecodeError) as error:
        raise DiscoveryError("AI Playground ComfyUI startup record is invalid") from error

    return ComfyConnection(base_url=f"http://127.0.0.1:{port}", token=token)