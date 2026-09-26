from news_analysis.config import Settings


def test_settings_loads_factcheck_key_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FACTCHECK_API_KEY", raising=False)
    (tmp_path / ".env").write_text("FACTCHECK_API_KEY=from-dotenv\n", encoding="utf-8")

    settings = Settings.from_env()

    assert settings.factcheck_api_key == "from-dotenv"


def test_environment_variable_overrides_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FACTCHECK_API_KEY", "from-env")
    (tmp_path / ".env").write_text("FACTCHECK_API_KEY=from-dotenv\n", encoding="utf-8")

    settings = Settings.from_env()

    assert settings.factcheck_api_key == "from-env"
