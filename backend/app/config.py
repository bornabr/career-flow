import os
from pydantic_settings import BaseSettings
from functools import lru_cache


# Available models per provider (updated March 2026)
AVAILABLE_MODELS: dict[str, list[str]] = {
    "google": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
    ],
    "openai": [
        "gpt-5.4",
        "gpt-5.4-pro",
        "gpt-5.3-codex",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "o3",
        "o3-pro",
        "o3-mini",
        "o4-mini",
    ],
    "anthropic": [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "claude-sonnet-4-5",
        "claude-opus-4-5",
    ],
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    app_name: str = "Career Flow API"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM Provider
    model_name: str = "google:gemini-2.5-pro"
    api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    @property
    def resolved_api_key(self) -> str:
        """Resolve API key: explicit api_key > provider-specific key."""
        if self.api_key:
            return self.api_key
        provider = self.provider
        return self._resolve_api_key_for_provider(provider)

    def resolve_api_key_for_provider(self, provider: str) -> str:
        """Resolve API key for a specific provider.

        Used when the user selects a model from a different provider
        than the default. Checks explicit api_key first, then
        provider-specific env vars.
        """
        if self.api_key:
            return self.api_key
        return self._resolve_api_key_for_provider(provider)

    def _resolve_api_key_for_provider(self, provider: str) -> str:
        """Internal: resolve provider-specific API key from env vars."""
        if provider in ("google", "gemini") and self.gemini_api_key:
            return self.gemini_api_key
        if provider == "openai" and self.openai_api_key:
            return self.openai_api_key
        if provider == "anthropic" and self.anthropic_api_key:
            return self.anthropic_api_key
        return ""

    # File upload
    max_upload_size_mb: int = 10

    model_config = {
        # Look for .env in backend/ first, then fall back to repo root
        "env_file": (
            os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        ),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def provider(self) -> str:
        """Extract provider name from model_name (e.g., 'google' from 'google:gemini-2.5-pro')."""
        if ":" in self.model_name:
            return self.model_name.split(":")[0]
        return "openai"

    @property
    def model_id(self) -> str:
        """Extract model ID from model_name (e.g., 'gemini-2.5-pro' from 'google:gemini-2.5-pro')."""
        if ":" in self.model_name:
            return self.model_name.split(":")[-1]
        return self.model_name


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
