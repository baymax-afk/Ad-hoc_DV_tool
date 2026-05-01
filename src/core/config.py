from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    redis_url: str = "redis://localhost:6379"
    session_ttl_seconds: int = 3600
    max_upload_mb: int = 50
    max_rows: int = 500_000
    log_level: str = "INFO"
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens_intent: int = 512
    llm_max_tokens_insights: int = 800


settings = Settings()
