from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .discovery import ComfyConnection


class ComfyClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedImage:
    prompt_id: str
    path: Path


class ComfyClient:
    def __init__(
        self,
        connection: ComfyConnection,
        output_dir: Path,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        poll_interval: float = 0.25,
    ) -> None:
        self._connection = connection
        self._output_dir = output_dir.resolve()
        self._transport = transport
        self._poll_interval = poll_interval

    async def check_status(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._connection.base_url,
                headers={"Authorization": f"Bearer {self._connection.token}"},
                transport=self._transport,
                trust_env=False,
                timeout=10,
            ) as client:
                response = await client.get("/queue")
                response.raise_for_status()
                return True
        except httpx.HTTPError as error:
            raise ComfyClientError("AI Playground ComfyUI is not reachable") from error

    async def generate(
        self, workflow: dict[str, Any], *, timeout_seconds: float = 600
    ) -> GeneratedImage:
        headers = {"Authorization": f"Bearer {self._connection.token}"}
        try:
            async with httpx.AsyncClient(
                base_url=self._connection.base_url,
                headers=headers,
                transport=self._transport,
                trust_env=False,
                timeout=30,
            ) as client:
                response = await client.post(
                    "/prompt",
                    json={"prompt": workflow, "client_id": str(uuid.uuid4())},
                )
                response.raise_for_status()
                prompt_id = response.json()["prompt_id"]
                if not isinstance(prompt_id, str) or not prompt_id:
                    raise ValueError("invalid prompt id")

                deadline = time.monotonic() + timeout_seconds
                while time.monotonic() < deadline:
                    history_response = await client.get(f"/history/{prompt_id}")
                    history_response.raise_for_status()
                    record = history_response.json().get(prompt_id)
                    if record is not None:
                        if record.get("status", {}).get("status_str") == "error":
                            raise ComfyClientError("ComfyUI workflow execution failed")
                        image = self._find_output_image(record.get("outputs", {}))
                        if image is not None:
                            return GeneratedImage(
                                prompt_id=prompt_id,
                                path=self._resolve_output_path(image),
                            )
                        if record.get("status", {}).get("status_str") == "success":
                            raise ComfyClientError(
                                "ComfyUI completed without an image output"
                            )
                    await asyncio.sleep(self._poll_interval)
        except ComfyClientError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise ComfyClientError("ComfyUI request failed") from error

        raise ComfyClientError("ComfyUI image generation timed out")

    @staticmethod
    def _find_output_image(outputs: dict[str, Any]) -> dict[str, Any] | None:
        for output in outputs.values():
            for image in output.get("images", []):
                if image.get("type") == "output":
                    return image
        return None

    def _resolve_output_path(self, image: dict[str, Any]) -> Path:
        filename = image.get("filename")
        subfolder = image.get("subfolder", "")
        if not isinstance(filename, str) or not isinstance(subfolder, str):
            raise ComfyClientError("ComfyUI returned an invalid output path")
        candidate = (self._output_dir / subfolder / filename).resolve()
        if not candidate.is_relative_to(self._output_dir):
            raise ComfyClientError("ComfyUI output path is outside the media directory")
        if not candidate.is_file():
            raise ComfyClientError("ComfyUI output image was not found on disk")
        return candidate