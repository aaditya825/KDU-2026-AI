import boto3

from interfaces import IModelInvoker
from models import ModelResponse


class BedrockModelInvoker(IModelInvoker):
    def __init__(self, aws_region: str):
        self._client = boto3.client("bedrock-runtime", region_name=aws_region)

    def invoke(self, model_id: str, user_query: str) -> ModelResponse:
        response = self._client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_query}]
                }
            ],
            inferenceConfig={
                "temperature": 0.2,
                "maxTokens": 1024
            }
        )

        return ModelResponse(
            model_id=model_id,
            text=self._extract_text(response),
            usage=response.get("usage", {})
        )

    @staticmethod
    def _extract_text(response: dict) -> str:
        try:
            content = response["output"]["message"]["content"]
            texts = [block["text"] for block in content if "text" in block]
            return "\n".join(texts).strip()
        except Exception:
            return ""
