from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

_PROVIDER_MAP = {
    "openai": (OpenAIModel, OpenAIProvider),
    "anthropic": (AnthropicModel, AnthropicProvider),
    "google": (GoogleModel, GoogleProvider),
    "gemini": (GoogleModel, GoogleProvider),
}


def create_model(provider_name: str, model_id: str, api_key: str):
    """Create a PydanticAI model instance for the given provider."""
    entry = _PROVIDER_MAP.get(provider_name)
    if entry is None:
        supported = ", ".join(_PROVIDER_MAP.keys())
        raise ValueError(f"Unsupported provider: {provider_name}. Supported: {supported}")

    model_cls, provider_cls = entry
    provider = provider_cls(api_key=api_key)
    return model_cls(model_id, provider=provider)


def create_model_from_string(model_string: str, api_key: str):
    """Parse 'provider:model_id' and return a configured model instance.

    Examples:
        create_model_from_string("google:gemini-2.5-pro", "sk-...")
        create_model_from_string("openai:gpt-4o", "sk-...")
    """
    if ":" not in model_string:
        return create_model("openai", model_string, api_key)

    provider_name, model_id = model_string.split(":", 1)
    return create_model(provider_name, model_id, api_key)
