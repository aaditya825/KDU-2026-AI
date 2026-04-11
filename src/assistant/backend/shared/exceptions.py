class AssistantError(Exception):
    """Base application exception for assistant backend."""


class UnsupportedRouteError(AssistantError):
    """Raised when a route exists in configuration but is not yet implemented."""


class InvalidModelConfigurationError(AssistantError):
    """Raised when backend model settings are invalid for the selected mode."""


class WeatherServiceError(AssistantError):
    """Raised when the weather backend cannot complete a request."""


class WeatherLocationNotFoundError(AssistantError):
    """Raised when a requested location cannot be resolved by the weather backend."""


class InvalidImageInputError(AssistantError):
    """Raised when uploaded image data is missing, malformed, or unsupported."""
