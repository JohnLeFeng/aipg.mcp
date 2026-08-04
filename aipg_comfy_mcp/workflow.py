from __future__ import annotations

import copy
import secrets
from dataclasses import dataclass
from typing import Any


class WorkflowError(ValueError):
    pass


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    negative_prompt: str = "nsfw"
    width: int = 512
    height: int = 512
    steps: int = 4
    seed: int = -1


def _validate(request: GenerationRequest) -> None:
    if not request.prompt.strip():
        raise WorkflowError("prompt must not be empty")
    if len(request.prompt) > 10_000 or len(request.negative_prompt) > 10_000:
        raise WorkflowError("prompt text must not exceed 10000 characters")
    for name, value in (("width", request.width), ("height", request.height)):
        if not 64 <= value <= 2048:
            raise WorkflowError(f"{name} must be between 64 and 2048")
        if value % 8:
            raise WorkflowError(f"{name} must be a multiple of 8")
    if not 1 <= request.steps <= 100:
        raise WorkflowError("steps must be between 1 and 100")
    if not -1 <= request.seed < 2**63:
        raise WorkflowError("seed must be -1 or between 0 and 2^63-1")


def _node_by_title(workflow: dict[str, Any], title: str) -> dict[str, Any]:
    for node in workflow.values():
        if node.get("_meta", {}).get("title") == title:
            return node
    raise WorkflowError(f"workflow is missing required node: {title}")


def build_workflow(
    template: dict[str, Any], request: GenerationRequest
) -> dict[str, Any]:
    _validate(request)
    workflow = copy.deepcopy(template)

    _node_by_title(workflow, "prompt")["inputs"]["text"] = request.prompt
    _node_by_title(workflow, "negativePrompt")["inputs"]["text"] = (
        request.negative_prompt
    )

    latent_inputs = _node_by_title(workflow, "Empty Latent Image")["inputs"]
    latent_inputs["width"] = request.width
    latent_inputs["height"] = request.height

    sampler_inputs = _node_by_title(workflow, "KSampler")["inputs"]
    sampler_inputs["steps"] = request.steps
    sampler_inputs["seed"] = (
        secrets.randbelow(2**63) if request.seed == -1 else request.seed
    )
    return workflow