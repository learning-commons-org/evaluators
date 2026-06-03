"""LLM providers for use in chains (e.g. LangChain).

create_provider() returns a langchain_core BaseChatModel (OpenAI, Google, Anthropic).

Config types (LLMProviderConfig and provider-specific configs:
AnthropicLLMProviderConfig, GoogleLLMProviderConfig, OpenAILLMProviderConfig)
live in learning_commons_evaluators.schemas.config.
"""

from learning_commons_evaluators.providers.langchain import (
    create_provider,
    token_usage_from_aimessage,
)

__all__ = ["create_provider", "token_usage_from_aimessage"]
