from dataclasses import dataclass


@dataclass(slots=True)
class UserProfile:
    """Minimal user profile used for hidden context in the weather flow."""

    user_id: str
    name: str
    location: str


class UserProfileStore:
    """Simple in-memory profile store for the MVP."""

    def __init__(self) -> None:
        self._profiles = {
            "default-user": UserProfile(
                user_id="default-user",
                name="User",
                location="Bengaluru",
            ),
            "user-1": UserProfile(
                user_id="user-1",
                name="Aarav",
                location="Mumbai",
            ),
            "weather-demo": UserProfile(
                user_id="weather-demo",
                name="Isha",
                location="San Francisco",
            ),
        }

    def get_profile(self, user_id: str) -> UserProfile:
        return self._profiles.get(
            user_id,
            UserProfile(
                user_id=user_id,
                name="User",
                location="Bengaluru",
            ),
        )

    def list_profiles(self) -> list[UserProfile]:
        return list(self._profiles.values())
