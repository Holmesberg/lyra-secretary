from app.core.config import Settings


def test_cors_allowed_origins_include_operator_dev_and_public_frontend():
    settings = Settings(FRONTEND_URL="https://lyraos.org")

    assert "https://lyraos.org" in settings.cors_allowed_origins
    assert "http://localhost:3000" in settings.cors_allowed_origins
    assert "http://127.0.0.1:3000" in settings.cors_allowed_origins


def test_cors_allowed_origins_accept_extra_configured_origins_without_duplicates():
    settings = Settings(
        FRONTEND_URL="https://lyraos.org",
        CORS_ALLOWED_ORIGINS="http://localhost:3000, https://preview.lyraos.org/",
    )

    assert settings.cors_allowed_origins.count("http://localhost:3000") == 1
    assert "https://preview.lyraos.org" in settings.cors_allowed_origins
