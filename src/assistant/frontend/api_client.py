import json
import base64

import httpx

from assistant.backend.shared.settings import get_settings


def get_available_users() -> dict:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.backend_base_url}/assistant/users",
            timeout=15.0,
        )
    except httpx.TimeoutException:
        return {
            "ok": False,
            "error": {
                "type": "backend_timeout",
                "message": "The backend did not respond before the timeout.",
                "provider": None,
                "retryable": True,
            },
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "error": {
                "type": "backend_connection_error",
                "message": f"Could not reach the backend: {exc}",
                "provider": None,
                "retryable": True,
            },
        }

    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None

    if response.is_success and isinstance(payload, list):
        return {"ok": True, "data": payload}

    return {
        "ok": False,
        "error": {
            "type": "invalid_backend_response",
            "message": "The backend returned an invalid user-profile response.",
            "provider": None,
            "retryable": False,
        },
    }


def send_chat_message(
    message: str,
    session_id: str,
    user_id: str = "default-user",
    communication_style: str | None = None,
    expertise_level: str | None = None,
    preferred_response_length: str | None = None,
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
    image_name: str | None = None,
) -> dict:
    settings = get_settings()
    request_payload = {
        "message": message,
        "session_id": session_id,
        "user_id": user_id,
    }
    if communication_style:
        request_payload["communication_style"] = communication_style
    if expertise_level:
        request_payload["expertise_level"] = expertise_level
    if preferred_response_length:
        request_payload["preferred_response_length"] = preferred_response_length
    if image_bytes is not None and image_mime_type:
        request_payload["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")
        request_payload["image_mime_type"] = image_mime_type
        request_payload["image_name"] = image_name
    try:
        response = httpx.post(
            f"{settings.backend_base_url}/assistant/chat",
            json=request_payload,
            timeout=30.0,
        )
    except httpx.TimeoutException:
        return {
            "ok": False,
            "status_code": 504,
            "error": {
                "type": "backend_timeout",
                "message": "The backend did not respond before the timeout.",
                "provider": None,
                "retryable": True,
            },
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "status_code": 503,
            "error": {
                "type": "backend_connection_error",
                "message": f"Could not reach the backend: {exc}",
                "provider": None,
                "retryable": True,
            },
        }

    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None

    if response.is_success:
        if payload is None:
            return {
                "ok": False,
                "status_code": response.status_code,
                "error": {
                    "type": "invalid_backend_response",
                    "message": "The backend returned a non-JSON success response.",
                    "provider": None,
                    "retryable": False,
                },
            }
        return {"ok": True, "data": payload}

    return {
        "ok": False,
        "status_code": response.status_code,
        "error": (payload or {}).get(
            "error",
            {
                "type": "unknown_error",
                "message": response.text.strip() or "The backend returned an unexpected error response.",
                "provider": None,
                "retryable": False,
            },
        ),
    }
