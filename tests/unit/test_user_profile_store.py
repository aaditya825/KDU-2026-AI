from assistant.backend.application.services.user_profile_store import UserProfileStore


def test_user_profile_store_returns_seeded_profile_identity_fields() -> None:
    store = UserProfileStore()

    profile = store.get_profile("weather-demo")

    assert profile.name == "Isha"
    assert profile.location == "San Francisco"


def test_user_profile_store_returns_defaults_for_unknown_user() -> None:
    store = UserProfileStore()

    profile = store.get_profile("unknown-user")

    assert profile.user_id == "unknown-user"
    assert profile.location == "Bengaluru"


def test_user_profile_store_lists_seeded_profiles() -> None:
    store = UserProfileStore()

    profiles = store.list_profiles()
    user_ids = {profile.user_id for profile in profiles}

    assert {"default-user", "user-1", "weather-demo"} <= user_ids
