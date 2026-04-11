from pydantic import BaseModel, Field


class GeneralTextResult(BaseModel):
    """Structured internal result for the general text route."""

    answer: str


class WeatherTextResult(BaseModel):
    """Structured internal result for the weather route."""

    answer: str
    location: str
    temperature_c: int
    summary: str


class ImageTextResult(BaseModel):
    """Structured internal result for the image-analysis route."""

    answer: str
    description: str
    objects: list[str] = Field(default_factory=list)
    summary: str


class AssistantResponse(BaseModel):
    """Stable API response contract for active assistant routes."""

    route: str = Field(default="general_text")
    answer: str
    model: str
    location: str | None = None
    temperature_c: int | None = None
    summary: str | None = None
    description: str | None = None
    objects: list[str] | None = None


class UserProfileSummary(BaseModel):
    """Public summary of an available demo user profile."""

    user_id: str
    name: str
    location: str


class ErrorDetail(BaseModel):
    """Stable error detail payload returned by backend exception handlers."""

    type: str
    message: str
    provider: str | None = None
    retryable: bool = False


class ErrorResponse(BaseModel):
    """Stable error response payload for non-success requests."""

    error: ErrorDetail
