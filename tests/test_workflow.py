import unittest

from aipg_comfy_mcp.workflow import GenerationRequest, WorkflowError, build_workflow


def template_workflow():
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": 1, "steps": 4},
            "_meta": {"title": "KSampler"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
            "_meta": {"title": "Empty Latent Image"},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "old prompt", "clip": ["10", 1]},
            "_meta": {"title": "prompt"},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "old negative", "clip": ["10", 1]},
            "_meta": {"title": "negativePrompt"},
        },
    }


class WorkflowTests(unittest.TestCase):
    def test_builds_modified_copy(self):
        template = template_workflow()
        request = GenerationRequest(
            prompt="a copper robot",
            negative_prompt="blurry",
            width=768,
            height=512,
            steps=6,
            seed=42,
        )

        result = build_workflow(template, request)

        self.assertEqual(result["6"]["inputs"]["text"], "a copper robot")
        self.assertEqual(result["7"]["inputs"]["text"], "blurry")
        self.assertEqual(result["5"]["inputs"]["width"], 768)
        self.assertEqual(result["5"]["inputs"]["height"], 512)
        self.assertEqual(result["3"]["inputs"]["steps"], 6)
        self.assertEqual(result["3"]["inputs"]["seed"], 42)
        self.assertEqual(template["6"]["inputs"]["text"], "old prompt")

    def test_random_seed_is_resolved(self):
        result = build_workflow(
            template_workflow(), GenerationRequest(prompt="test", seed=-1)
        )

        self.assertGreaterEqual(result["3"]["inputs"]["seed"], 0)
        self.assertLess(result["3"]["inputs"]["seed"], 2**63)

    def test_rejects_dimension_not_divisible_by_eight(self):
        with self.assertRaisesRegex(WorkflowError, "multiple of 8"):
            build_workflow(
                template_workflow(), GenerationRequest(prompt="test", width=513)
            )

    def test_rejects_missing_semantic_node(self):
        template = template_workflow()
        del template["7"]

        with self.assertRaisesRegex(WorkflowError, "negativePrompt"):
            build_workflow(template, GenerationRequest(prompt="test"))


if __name__ == "__main__":
    unittest.main()