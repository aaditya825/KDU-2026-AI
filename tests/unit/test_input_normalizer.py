import base64

from assistant.backend.application.services.input_normalizer import InputNormalizer
from assistant.backend.contracts.requests import AssistantChatRequest
from assistant.backend.shared.exceptions import InvalidImageInputError


def test_input_normalizer_strips_fields() -> None:
    normalizer = InputNormalizer()
    request = AssistantChatRequest(
        message=" hello ",
        session_id=" session-1 ",
        user_id=" user-1 ",
    )

    normalized = normalizer.normalize(request)

    assert normalized.message == "hello"
    assert normalized.session_id == "session-1"
    assert normalized.user_id == "user-1"


def test_input_normalizer_decodes_image_payload() -> None:
    normalizer = InputNormalizer(max_image_bytes=1024)
    image_bytes = b"fake-image-bytes"
    request = AssistantChatRequest(
        message="Describe this image",
        session_id="session-1",
        user_id="user-1",
        image_base64=base64.b64encode(image_bytes).decode("utf-8"),
        image_mime_type="image/png",
        image_name="sample.png",
    )

    normalized = normalizer.normalize(request)

    assert normalized.image_bytes == image_bytes
    assert normalized.image_mime_type == "image/png"
    assert normalized.image_name == "sample.png"


def test_input_normalizer_rejects_unsupported_image_type() -> None:
    normalizer = InputNormalizer(max_image_bytes=1024)
    request = AssistantChatRequest(
        message="Describe this image",
        session_id="session-1",
        user_id="user-1",
        image_base64=base64.b64encode(b"image").decode("utf-8"),
        image_mime_type="image/gif",
    )

    try:
        normalizer.normalize(request)
    except InvalidImageInputError as exc:
        assert "not supported" in str(exc)
    else:
        raise AssertionError("Expected InvalidImageInputError for unsupported image type.")
