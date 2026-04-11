import base64
from dataclasses import dataclass

from assistant.backend.contracts.requests import AssistantChatRequest
from assistant.backend.shared.exceptions import InvalidImageInputError


@dataclass(slots=True)
class NormalizedAssistantRequest:
    """Internal normalized request shape used across the active MVP flow."""

    message: str
    session_id: str
    user_id: str
    communication_style: str | None = None
    expertise_level: str | None = None
    preferred_response_length: str | None = None
    image_bytes: bytes | None = None
    image_mime_type: str | None = None
    image_name: str | None = None

    @property
    def has_image(self) -> bool:
        return self.image_bytes is not None


class InputNormalizer:
    """Normalize incoming transport models into backend-friendly state."""

    _allowed_image_mime_types = {"image/png", "image/jpeg", "image/webp"}

    def __init__(self, max_image_bytes: int = 5 * 1024 * 1024) -> None:
        self._max_image_bytes = max_image_bytes

    def normalize(self, request: AssistantChatRequest) -> NormalizedAssistantRequest:
        image_bytes = None
        image_mime_type = None
        image_name = None
        if (request.image_base64 or "").strip():
            image_bytes = self._decode_image_bytes(request.image_base64)
            image_mime_type = (request.image_mime_type or "").strip()
            image_name = (request.image_name or "").strip() or None
            self._validate_image(image_bytes=image_bytes, image_mime_type=image_mime_type)

        return NormalizedAssistantRequest(
            message=request.message.strip(),
            session_id=request.session_id.strip(),
            user_id=request.user_id.strip(),
            communication_style=(request.communication_style or "").strip() or None,
            expertise_level=(request.expertise_level or "").strip() or None,
            preferred_response_length=(request.preferred_response_length or "").strip()
            or None,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
            image_name=image_name,
        )

    def _decode_image_bytes(self, image_base64: str) -> bytes:
        try:
            return base64.b64decode(image_base64, validate=True)
        except (TypeError, ValueError) as exc:
            raise InvalidImageInputError("Uploaded image data is not valid base64.") from exc

    def _validate_image(self, *, image_bytes: bytes, image_mime_type: str) -> None:
        if image_mime_type not in self._allowed_image_mime_types:
            raise InvalidImageInputError(
                "Uploaded image type is not supported. Use PNG, JPEG, or WEBP."
            )
        if len(image_bytes) > self._max_image_bytes:
            raise InvalidImageInputError(
                f"Uploaded image exceeds the {self._max_image_bytes} byte limit."
            )
