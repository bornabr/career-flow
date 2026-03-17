from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GraphRuntimeConfig:
    """Runtime configuration for LangGraph execution.

    Contains secrets and per-request configuration that should NOT be
    persisted in graph checkpoints. API keys are passed at runtime via
    RunnableConfig["configurable"]["runtime"].

    Attributes:
        model_name: LLM model for main generation (format: "provider:model-id")
        api_key: API key for main model provider
        review_model_name: Optional model for reviewer agents (can differ from main)
        review_api_key: Optional API key for review model provider
    """
    model_name: str
    api_key: str
    review_model_name: str | None = None
    review_api_key: str | None = None
