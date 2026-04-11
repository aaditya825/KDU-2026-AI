import base64

from langchain_core.messages import HumanMessage

from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


class MultimodalMessageBuilder:
    """Build provider-ready multimodal messages from normalized request data."""

    def build_image_analysis_message(
        self,
        request: NormalizedAssistantRequest,
        *,
        user_name: str,
    ) -> HumanMessage:
        if request.image_bytes is None or request.image_mime_type is None:
            raise ValueError("Image analysis requires normalized image bytes and MIME type.")

        prompt_text = request.message or "Describe this image."
        image_base64 = base64.b64encode(request.image_bytes).decode("utf-8")

        return HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": f"User: {user_name}\nInstruction: {prompt_text}",
                },
                {
                    "type": "image",
                    "base64": image_base64,
                    "mime_type": request.image_mime_type,
                },
            ]
        )
