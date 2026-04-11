from fastapi import APIRouter, Depends

from assistant.backend.api.dependencies import get_orchestrator, get_profile_store
from assistant.backend.contracts.requests import AssistantChatRequest
from assistant.backend.contracts.responses import AssistantResponse, UserProfileSummary

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantResponse)
def chat(
    request: AssistantChatRequest,
    orchestrator=Depends(get_orchestrator),
) -> AssistantResponse:
    return orchestrator.execute(request)


@router.get("/users", response_model=list[UserProfileSummary])
def list_users(profile_store=Depends(get_profile_store)) -> list[UserProfileSummary]:
    return [
        UserProfileSummary(
            user_id=profile.user_id,
            name=profile.name,
            location=profile.location,
        )
        for profile in profile_store.list_profiles()
    ]
