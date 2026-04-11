import httpx
from google.genai import errors as google_genai_errors
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from assistant.backend.contracts.responses import AssistantResponse
from assistant.backend.api.dependencies import get_orchestrator
from fastapi.testclient import TestClient

from assistant.backend.main import create_app


def test_chat_endpoint_returns_response() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            return AssistantResponse(
                route="general_text",
                answer="Explain the current phase -> stubbed response",
                model="gemini-2.5-flash",
            )

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "Explain the current phase",
            "session_id": "integration-session",
            "user_id": "integration-user",
        },
    )

    assert http_response.status_code == 200
    payload = http_response.json()
    assert payload["route"] == "general_text"
    assert payload["model"] == "gemini-2.5-flash"
    assert "stubbed response" in payload["answer"]


def test_users_endpoint_returns_available_profiles() -> None:
    app = create_app()
    client = TestClient(app)

    http_response = client.get("/assistant/users")

    assert http_response.status_code == 200
    payload = http_response.json()
    assert isinstance(payload, list)
    user_ids = {item["user_id"] for item in payload}
    assert {"default-user", "user-1", "weather-demo"} <= user_ids


def test_chat_endpoint_returns_weather_response() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            return AssistantResponse(
                route="weather_text",
                answer="It is warm in Mumbai.",
                model="gemini-2.5-flash",
                location="Mumbai",
                temperature_c=31,
                summary="Warm and humid.",
            )

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "What's the weather?",
            "session_id": "weather-session",
            "user_id": "weather-demo",
        },
    )

    assert http_response.status_code == 200
    payload = http_response.json()
    assert payload["route"] == "weather_text"
    assert payload["location"] == "Mumbai"
    assert payload["temperature_c"] == 31
    assert payload["summary"] == "Warm and humid."


def test_chat_endpoint_returns_image_response() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            return AssistantResponse(
                route="image_text",
                answer="A desk setup is visible.",
                model="gemini-2.5-flash",
                description="A laptop beside a mug on a desk.",
                objects=["laptop", "mug", "desk"],
                summary="Indoor workspace scene.",
            )

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "Describe this image",
            "session_id": "image-session",
            "user_id": "image-user",
            "image_base64": "aW1hZ2U=",
            "image_mime_type": "image/png",
        },
    )

    assert http_response.status_code == 200
    payload = http_response.json()
    assert payload["route"] == "image_text"
    assert payload["description"] == "A laptop beside a mug on a desk."
    assert payload["objects"] == ["laptop", "mug", "desk"]


def test_chat_endpoint_translates_google_ai_studio_auth_error() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            raise google_genai_errors.ClientError(
                401,
                {"error": {"message": "invalid api key"}},
                None,
            )

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "hello",
            "session_id": "google-auth-failure",
            "user_id": "user-1",
        },
    )

    assert http_response.status_code == 502
    payload = http_response.json()
    assert payload["error"]["type"] == "google_ai_studio_authentication_error"
    assert payload["error"]["provider"] == "google_ai_studio"
    assert payload["error"]["retryable"] is False


def test_chat_endpoint_translates_google_ai_studio_rate_limit_error() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            raise google_genai_errors.ClientError(
                429,
                {"error": {"message": "quota exceeded"}},
                None,
            )

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "hello",
            "session_id": "google-rate-limit-failure",
            "user_id": "user-1",
        },
    )

    assert http_response.status_code == 503
    payload = http_response.json()
    assert payload["error"]["type"] == "google_ai_studio_rate_limit_error"
    assert payload["error"]["provider"] == "google_ai_studio"
    assert payload["error"]["retryable"] is True


def test_chat_endpoint_translates_google_ai_studio_connection_error() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            raise httpx.ConnectError("dns failure")

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "Describe this image",
            "session_id": "google-connect-failure",
            "user_id": "user-1",
            "image_base64": "aW1hZ2U=",
            "image_mime_type": "image/png",
        },
    )

    assert http_response.status_code == 503
    payload = http_response.json()
    assert payload["error"]["type"] == "google_ai_studio_connection_error"
    assert payload["error"]["provider"] == "google_ai_studio"
    assert payload["error"]["retryable"] is True


def test_chat_endpoint_translates_langchain_google_rate_limit_error() -> None:
    class FakeOrchestrator:
        def execute(self, _request):
            raise ChatGoogleGenerativeAIError(
                "Error calling model 'gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED."
            )

    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    http_response = client.post(
        "/assistant/chat",
        json={
            "message": "hello",
            "session_id": "google-langchain-rate-limit",
            "user_id": "user-1",
        },
    )

    assert http_response.status_code == 503
    payload = http_response.json()
    assert payload["error"]["type"] == "google_ai_studio_rate_limit_error"
    assert payload["error"]["provider"] == "google_ai_studio"
    assert payload["error"]["retryable"] is True
