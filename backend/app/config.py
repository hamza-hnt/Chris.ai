from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    LLM_PROVIDER: Literal["openai", "anthropic"] = Field(description="LLM provider key.")
    OPENAI_API_KEY: SecretStr | None = Field(default=None, description="OpenAI API key.")
    OPENAI_MODEL: str = Field(default="gpt-4o", description="OpenAI model id.")
    TAVILY_API_KEY: SecretStr = Field(description="Tavily API key for web search.")

    POSTGRES_HOST: str = Field(description="PostgreSQL host.")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port.")
    POSTGRES_DB: str = Field(description="PostgreSQL database name.")
    POSTGRES_USER: str = Field(description="PostgreSQL username.")
    POSTGRES_PASSWORD: SecretStr = Field(description="PostgreSQL password.")

    APP_ENV: Literal["development", "staging", "production", "test"] = Field(
        default="development", description="Runtime environment."
    )
    APP_LOG_LEVEL: Literal["debug", "info", "warning", "error"] = Field(
        default="info", description="Application log level."
    )
    APP_AGENT_TOOL_BUDGET: int = Field(default=20, ge=1, le=100, description="Tool call cap.")

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        missing: list[str] = []
        if self.LLM_PROVIDER == "openai" and not _secret_value(self.OPENAI_API_KEY):
            missing.append("OPENAI_API_KEY")
        if not _secret_value(self.TAVILY_API_KEY):
            missing.append("TAVILY_API_KEY")
        if not _secret_value(self.POSTGRES_PASSWORD):
            missing.append("POSTGRES_PASSWORD")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing or empty required environment variable(s): {joined}")
        return self

    @property
    def database_url(self) -> str:
        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def safe_boot_summary(self) -> dict[str, str | int]:
        return {
            "app_env": self.APP_ENV,
            "log_level": self.APP_LOG_LEVEL,
            "llm_provider": self.LLM_PROVIDER,
            "openai_model": self.OPENAI_MODEL,
            "postgres_host": self.POSTGRES_HOST,
            "postgres_db": self.POSTGRES_DB,
            "agent_tool_budget": self.APP_AGENT_TOOL_BUDGET,
        }


def _secret_value(value: SecretStr | None) -> str:
    if value is None:
        return ""
    return value.get_secret_value().strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
