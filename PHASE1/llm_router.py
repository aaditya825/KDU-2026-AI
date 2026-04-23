import json

import boto3

from interfaces import ILLMRouter
from models import LLMRouteResult, RouteLabel


class BedrockLLMRouter(ILLMRouter):
    def __init__(self, aws_region: str, router_model_id: str):
        self._client = boto3.client("bedrock-runtime", region_name=aws_region)
        self._router_model_id = router_model_id

    def route(self, query: str) -> LLMRouteResult:
        response = self._client.converse(
            modelId=self._router_model_id,
            system=[{"text": self._router_system_prompt()}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": query}]
                }
            ],
            inferenceConfig={
                "temperature": 0,
                "maxTokens": 200
            }
        )

        text = self._extract_text(response)

        try:
            data = json.loads(text)
            route = RouteLabel(data["route"])
            reason = data.get("reason", "")
            confidence = float(data.get("confidence", 0.0))
        except Exception:
            route = RouteLabel.CASUAL_CONVERSATION
            reason = "Fallback to cheaper route because router output was invalid."
            confidence = 0.0

        return LLMRouteResult(
            route=route,
            confidence=confidence,
            reason=reason,
            model_id=self._router_model_id,
            usage=response.get("usage", {}),
        )

    @staticmethod
    def _extract_text(response: dict) -> str:
        try:
            content = response["output"]["message"]["content"]
            texts = [block["text"] for block in content if "text" in block]
            return "\n".join(texts).strip()
        except Exception:
            return ""

    @staticmethod
    def _router_system_prompt() -> str:
        return """
You are a routing classifier.

Classify the user prompt into exactly one of:
- casual_conversation
- complex_code_generation

Rules:
- casual_conversation includes greetings, small talk, simple requests,
  lightweight Q&A, and very simple coding tasks like tiny functions or hello-world scripts.
- complex_code_generation includes advanced coding, multi-step implementation,
  architecture, framework-heavy tasks, system design, and production-level code generation.

Prefer casual_conversation unless the coding task is clearly difficult.

Return JSON only in this format:
{
  "route": "casual_conversation" | "complex_code_generation",
  "reason": "short reason",
  "confidence": 0.0
}
""".strip()
