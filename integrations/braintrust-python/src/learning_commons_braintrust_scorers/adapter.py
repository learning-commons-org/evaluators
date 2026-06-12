"""Braintrust adapters implementing LLMGeneratorProtocol.

Two adapters share a common base that handles the Anthropic generation call:

``BraintrustAnthropicAdapter``
    Uses ``braintrust.auto_instrument()`` to intercept Anthropic SDK calls.
    Requires the ``[braintrust]`` optional dependency::

        pip install learning-commons-braintrust-scorers[braintrust]

    Usage::

        from learning_commons_braintrust_scorers import BraintrustAnthropicAdapter

        adapter = BraintrustAnthropicAdapter(project="my-project")
        evaluator = GradeLevelAppropriatenessEvaluator(config=..., llm_provider=adapter)

``BraintrustProxyAdapter``
    Routes calls through ``https://api.braintrust.dev/v1/proxy``.
    No Braintrust SDK required — only the ``anthropic`` package::

        pip install learning-commons-braintrust-scorers

    Usage::

        from learning_commons_braintrust_scorers import BraintrustProxyAdapter

        adapter = BraintrustProxyAdapter(project="my-project")
        evaluator = GradeLevelAppropriatenessEvaluator(config=..., llm_provider=adapter)
"""

from __future__ import annotations

import anthropic
from anthropic import NOT_GIVEN

from learning_commons_evaluators.schemas.llm_provider import GenerateConfig, LLMResponse

_DEFAULT_MODEL = "claude-opus-4-8-20250514"
_DEFAULT_MAX_TOKENS = 4096


class _AnthropicAdapterBase:
    """Shared Anthropic generation logic for Braintrust adapters.

    Subclasses set ``self._client`` and ``self._model`` in ``__init__``.
    """

    _client: anthropic.AsyncAnthropic
    _model: str

    async def generate(
        self,
        *,
        system: str,
        human: str,
        config: GenerateConfig | None = None,
    ) -> LLMResponse:
        msg = await self._client.messages.create(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": human}],
            max_tokens=config.max_tokens if (config and config.max_tokens is not None) else _DEFAULT_MAX_TOKENS,
            # Use NOT_GIVEN (not None) so the field is omitted from the request body.
            # Passing None serialises as {"temperature": null} which the Anthropic API rejects.
            temperature=config.temperature if (config and config.temperature is not None) else NOT_GIVEN,
        )
        # Find the first text block; content may include ThinkingBlock or ToolUseBlock.
        text_block = next((b for b in msg.content if b.type == "text"), None)
        if text_block is None:
            raise ValueError(
                f"Anthropic response from {msg.model} contained no text block "
                f"(content types: {[b.type for b in msg.content]})"
            )
        return LLMResponse(
            content=text_block.text,
            model=msg.model,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )

    async def aclose(self) -> None:
        await self._client.close()


class BraintrustAnthropicAdapter(_AnthropicAdapterBase):
    """Adapter using Braintrust auto-instrumentation of the Anthropic SDK.

    Calls ``braintrust.auto_instrument()`` at construction time (idempotent).
    When ``project`` is provided, calls ``braintrust.init(project=project)``
    so that traces are associated with the correct Braintrust project.

    Requires ``pip install learning-commons-braintrust-scorers[braintrust]``.

    Args:
        model: Anthropic model ID.
        project: Braintrust project name. When provided, initialises the
                 Braintrust SDK so traces appear under this project in the UI.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        *,
        project: str | None = None,
    ) -> None:
        import braintrust

        braintrust.auto_instrument()
        if project:
            braintrust.init(project=project)
        self._client = anthropic.AsyncAnthropic()
        self._model = model


class BraintrustProxyAdapter(_AnthropicAdapterBase):
    """Adapter using Braintrust AI Proxy — no Braintrust SDK required.

    Routes Anthropic API calls through ``https://api.braintrust.dev/v1/proxy``.
    Braintrust logs all calls automatically via HTTP interception.

    Args:
        model: Anthropic model ID.
        api_key: Braintrust API key. Falls back to the ``BRAINTRUST_API_KEY``
                 environment variable. Raises ``ValueError`` if neither is set
                 or if the resolved value is blank.
        project: Braintrust project name. Passed as the ``x-bt-parent`` header
                 so traces appear under the correct project in the Braintrust UI.

    Raises:
        ValueError: At construction time when no non-blank API key is available.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        *,
        api_key: str | None = None,
        project: str | None = None,
    ) -> None:
        import os

        resolved_key = (api_key or os.environ.get("BRAINTRUST_API_KEY") or "").strip()
        if not resolved_key:
            raise ValueError(
                "Braintrust API key is required. Provide it via the api_key argument "
                "or set the BRAINTRUST_API_KEY environment variable."
            )

        self._client = anthropic.AsyncAnthropic(
            base_url="https://api.braintrust.dev/v1/proxy",
            auth_token=resolved_key,
            default_headers={"x-bt-parent": f"project_name:{project}"} if project else {},
        )
        self._model = model
