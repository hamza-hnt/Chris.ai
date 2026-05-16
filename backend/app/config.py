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
    SLNG_API_KEY: SecretStr | None = Field(default=None, description="SLNG API key for STT/TTS.")
    SLNG_STT_MODEL: str = Field(
        default="slng/deepgram/nova:3-multi",
        description="SLNG STT model path segment, for example slng/deepgram/nova:3-multi.",
    )

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
    APP_AGENT_RUNTIME: Literal["deterministic", "llm"] = Field(
        default="deterministic", description="Agent runtime policy."
    )

    WHATSAPP_MODE: Literal["stub", "cloud", "twilio"] = Field(
        default="stub", description="WhatsApp integration mode."
    )
    WHATSAPP_GRAPH_API_VERSION: str = Field(
        default="v25.0", description="Meta Graph API version for WhatsApp Cloud API."
    )
    WHATSAPP_ACCESS_TOKEN: SecretStr | None = Field(
        default=None, description="WhatsApp Cloud API access token."
    )
    WHATSAPP_BUSINESS_ACCOUNT_ID: str | None = Field(
        default=None, description="WhatsApp Business Account ID."
    )
    WHATSAPP_PHONE_NUMBER_ID: str | None = Field(
        default=None, description="WhatsApp sender phone number ID."
    )
    WHATSAPP_VERIFY_TOKEN: SecretStr | None = Field(
        default=None, description="Webhook verification token configured in Meta."
    )
    WHATSAPP_APP_SECRET: SecretStr | None = Field(
        default=None, description="Meta app secret for X-Hub-Signature-256 validation."
    )
    TWILIO_ACCOUNT_SID: str | None = Field(
        default=None, description="Twilio account SID for WhatsApp Sandbox."
    )
    TWILIO_AUTH_TOKEN: SecretStr | None = Field(
        default=None, description="Twilio auth token for REST API and webhook signatures."
    )
    TWILIO_WHATSAPP_FROM: str = Field(
        default="whatsapp:+14155238886", description="Twilio WhatsApp Sandbox sender."
    )
    TWILIO_VALIDATE_SIGNATURE: bool = Field(
        default=False, description="Validate X-Twilio-Signature on inbound webhooks."
    )

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        missing: list[str] = []
        if self.LLM_PROVIDER == "openai" and not _secret_value(self.OPENAI_API_KEY):
            missing.append("OPENAI_API_KEY")
        if not _secret_value(self.TAVILY_API_KEY):
            missing.append("TAVILY_API_KEY")
        if not _secret_value(self.SLNG_API_KEY):
            missing.append("SLNG_API_KEY")
        if not _secret_value(self.POSTGRES_PASSWORD):
            missing.append("POSTGRES_PASSWORD")
        if self.WHATSAPP_MODE == "cloud":
            if not _secret_value(self.WHATSAPP_ACCESS_TOKEN):
                missing.append("WHATSAPP_ACCESS_TOKEN")
            if not _plain_value(self.WHATSAPP_PHONE_NUMBER_ID):
                missing.append("WHATSAPP_PHONE_NUMBER_ID")
            if not _secret_value(self.WHATSAPP_VERIFY_TOKEN):
                missing.append("WHATSAPP_VERIFY_TOKEN")
            if self.APP_ENV == "production" and not _secret_value(self.WHATSAPP_APP_SECRET):
                missing.append("WHATSAPP_APP_SECRET")
        if self.WHATSAPP_MODE == "twilio":
            if not _plain_value(self.TWILIO_ACCOUNT_SID):
                missing.append("TWILIO_ACCOUNT_SID")
            if not _secret_value(self.TWILIO_AUTH_TOKEN):
                missing.append("TWILIO_AUTH_TOKEN")
            if not _plain_value(self.TWILIO_WHATSAPP_FROM):
                missing.append("TWILIO_WHATSAPP_FROM")
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
            "agent_runtime": self.APP_AGENT_RUNTIME,
            "whatsapp_mode": self.WHATSAPP_MODE,
            "whatsapp_graph_api_version": self.WHATSAPP_GRAPH_API_VERSION,
        }


def _secret_value(value: SecretStr | None) -> str:
    if value is None:
        return ""
    return value.get_secret_value().strip()


def _plain_value(value: str | None) -> str:
    return value.strip() if value else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
