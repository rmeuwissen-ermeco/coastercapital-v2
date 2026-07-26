from app.config import Settings


def test_neon_postgresql_url_uses_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:secret@example.test/coasters")

    assert settings.database_url == (
        "postgresql+psycopg://user:secret@example.test/coasters"
    )


def test_explicit_driver_and_sqlite_urls_are_preserved() -> None:
    psycopg_url = "postgresql+psycopg://user:secret@example.test/coasters"
    sqlite_url = "sqlite:///./coastercapital.db"

    assert Settings(database_url=psycopg_url).database_url == psycopg_url
    assert Settings(database_url=sqlite_url).database_url == sqlite_url
