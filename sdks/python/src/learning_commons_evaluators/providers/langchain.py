"""LangChain chat model factory.

create_provider(prompt_settings, evaluator_config) builds a LangChain chat model
(OpenAI, Google, Anthropic) using PromptSettings and EvaluatorConfig.
Set model and temperature when building the chain, e.g. llm.bind(model="gpt-4o", temperature=0.7).

token_usage_from_aimessage() extracts TokenUsage from a LangChain AIMessage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.schemas.config import (
    EvaluatorConfig,
    LlmProvider,
    PromptSettings,
)
from learning_commons_evaluators.schemas.metadata import TokenUsage

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


def token_usage_from_aimessage(message: Any, prompt_settings: PromptSettings) -> TokenUsage:
    """Extract TokenUsage from a LangChain AIMessage and prompt settings."""
    usage = getattr(message, "usage_metadata", None) or getattr(
        message, "response_metadata", {}
    ).get("usage_metadata")
    if not usage:
        return TokenUsage(
            provider_type=prompt_settings.provider_type,
            model=prompt_settings.model,
            input_tokens=0,
            output_tokens=0,
        )
    return TokenUsage(
        provider_type=prompt_settings.provider_type,
        model=prompt_settings.model,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
    )


def _create_openai_llm(
    prompt_settings: PromptSettings, evaluator_config: EvaluatorConfig
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    openai_config = evaluator_config.openai_prompt_provider_config
    if openai_config is None:
        raise ConfigurationError("OpenAI provider config is not set on EvaluatorConfig")
    kwargs: dict[str, Any] = {
        "api_key": openai_config.api_key,
        "model": prompt_settings.model,
        "temperature": prompt_settings.temperature,
    }
    if openai_config.base_url is not None:
        kwargs["base_url"] = openai_config.base_url
    return ChatOpenAI(**kwargs)


def _create_google_llm(
    prompt_settings: PromptSettings, evaluator_config: EvaluatorConfig
) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    google_config = evaluator_config.google_prompt_provider_config
    if google_config is None:
        raise ConfigurationError("Google provider config is not set on EvaluatorConfig")
    return ChatGoogleGenerativeAI(
        google_api_key=google_config.api_key,
        model=prompt_settings.model,
        temperature=prompt_settings.temperature,
    )


def _create_anthropic_llm(
    prompt_settings: PromptSettings, evaluator_config: EvaluatorConfig
) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    anthropic_config = evaluator_config.anthropic_prompt_provider_config
    if anthropic_config is None:
        raise ConfigurationError("Anthropic provider config is not set on EvaluatorConfig")
    return ChatAnthropic(
        api_key=anthropic_config.api_key,
        model=prompt_settings.model,
        temperature=prompt_settings.temperature,
    )


def create_provider(
    prompt_settings: PromptSettings, evaluator_config: EvaluatorConfig
) -> BaseChatModel:
    """Create a LangChain chat model from a PromptSettings for use in a chain."""
    if prompt_settings.provider_type == LlmProvider.OPENAI:
        return _create_openai_llm(prompt_settings, evaluator_config)
    if prompt_settings.provider_type == LlmProvider.GOOGLE:
        return _create_google_llm(prompt_settings, evaluator_config)
    if prompt_settings.provider_type == LlmProvider.ANTHROPIC:
        return _create_anthropic_llm(prompt_settings, evaluator_config)
    raise ConfigurationError(
        f"Unsupported LLM provider type: {prompt_settings.provider_type!r}. "
        "Expected openai, google, or anthropic."
    )


__all__ = ["create_provider", "token_usage_from_aimessage"]
