from app.config import Settings


def test_settings() -> Settings:
    return Settings.for_test()
