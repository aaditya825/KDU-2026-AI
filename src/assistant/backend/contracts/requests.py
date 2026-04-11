from pydantic import BaseModel, Field, model_validator


class AssistantChatRequest(BaseModel):
    """HTTP request contract for text and image assistant flows."""

    message: str = Field(default="", max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(default="default-user", min_length=1, max_length=128)
    communication_style: str | None = Field(default=None, max_length=64)
    expertise_level: str | None = Field(default=None, max_length=64)
    preferred_response_length: str | None = Field(default=None, max_length=64)
    image_base64: str | None = None
    image_mime_type: str | None = Field(default=None, max_length=128)
    image_name: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_content(self) -> "AssistantChatRequest":
        if not self.message.strip() and not (self.image_base64 or "").strip():
            raise ValueError("At least one of message or image_base64 is required.")
        if (self.image_base64 or "").strip() and not (self.image_mime_type or "").strip():
            raise ValueError("image_mime_type is required when image_base64 is provided.")
        return self
