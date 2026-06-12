"""Tests for BraintrustAnthropicAdapter and BraintrustProxyAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from learning_commons_evaluators.schemas.llm_provider import GenerateConfig, LLMResponse


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_anthropic_message(
    text: str = "response text",
    model: str = "claude-opus-4-8-20250514",
    input_tokens: int = 10,
    output_tokens: int = 20,
) -> MagicMock:
    msg = MagicMock()
    text_block = MagicMock(type="text", text=text)
    msg.content = [text_block]
    msg.model = model
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


def _make_async_anthropic_client(message: MagicMock | None = None) -> MagicMock:
    """Return a mock AsyncAnthropic client whose messages.create returns *message*."""
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=message or _make_anthropic_message())
    client.close = AsyncMock()
    return client


# ── BraintrustAnthropicAdapter ────────────────────────────────────────────────


class TestBraintrustAnthropicAdapter:
    def _make_adapter(self, model: str = "claude-opus-4-8-20250514", project: str | None = None):
        """Construct adapter with braintrust and anthropic mocked out."""
        mock_client = _make_async_anthropic_client()
        mock_braintrust = MagicMock()

        with (
            # sys.modules mock covers all braintrust attribute access, including auto_instrument.
            # Do NOT use patch("braintrust.auto_instrument") here — it tries to import the real
            # module before the sys.modules replacement is applied (ModuleNotFoundError).
            patch.dict("sys.modules", {"braintrust": mock_braintrust}),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
        ):
            from learning_commons_braintrust_scorers.adapter import BraintrustAnthropicAdapter

            adapter = BraintrustAnthropicAdapter(model=model, project=project)

        # Attach the mock client so tests can make assertions on it.
        adapter._client = mock_client
        return adapter, mock_client, mock_braintrust

    def test_auto_instrument_called_at_construction(self):
        mock_client = _make_async_anthropic_client()
        mock_braintrust = MagicMock()

        with (
            patch.dict("sys.modules", {"braintrust": mock_braintrust}),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
        ):
            from importlib import reload

            import learning_commons_braintrust_scorers.adapter as mod

            reload(mod)
            mod.BraintrustAnthropicAdapter()

        # Use .called (not assert_called_once) — reload() inside _make_adapter() may have
        # already triggered a call, making assert_called_once() order-dependent across tests.
        assert mock_braintrust.auto_instrument.called

    async def test_generate_returns_llm_response(self):
        msg = _make_anthropic_message(
            text="some output", model="claude-opus-4-8-20250514", input_tokens=5, output_tokens=15
        )
        adapter, mock_client, _ = self._make_adapter()
        mock_client.messages.create.return_value = msg

        result = await adapter.generate(system="sys prompt", human="user prompt")

        assert isinstance(result, LLMResponse)
        assert result.content == "some output"
        assert result.model == "claude-opus-4-8-20250514"
        assert result.input_tokens == 5
        assert result.output_tokens == 15

    async def test_generate_passes_system_and_human(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.generate(system="the system", human="the human")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "the system"
        assert call_kwargs["messages"] == [{"role": "user", "content": "the human"}]

    async def test_generate_default_max_tokens(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.generate(system="s", human="h")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 4096

    async def test_generate_default_temperature(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.generate(system="s", human="h")

        call_kwargs = mock_client.messages.create.call_args[1]
        # When no config is provided, temperature=NOT_GIVEN (field omitted from request)
        from anthropic import NOT_GIVEN
        assert call_kwargs["temperature"] is NOT_GIVEN

    async def test_generate_respects_config_max_tokens(self):
        adapter, mock_client, _ = self._make_adapter()
        config = GenerateConfig(temperature=None, max_tokens=512)

        await adapter.generate(system="s", human="h", config=config)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 512

    async def test_generate_respects_config_temperature(self):
        adapter, mock_client, _ = self._make_adapter()
        config = GenerateConfig(temperature=0.7, max_tokens=None)

        await adapter.generate(system="s", human="h", config=config)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    async def test_generate_config_max_tokens_none_falls_back_to_4096(self):
        adapter, mock_client, _ = self._make_adapter()
        config = GenerateConfig(temperature=0.5, max_tokens=None)

        await adapter.generate(system="s", human="h", config=config)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 4096

    async def test_generate_uses_configured_model(self):
        adapter, mock_client, _ = self._make_adapter(model="claude-haiku-3-5-20251022")

        await adapter.generate(system="s", human="h")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-3-5-20251022"

    async def test_aclose_calls_client_close(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.aclose()

        mock_client.close.assert_called_once()


# ── BraintrustProxyAdapter ────────────────────────────────────────────────────


class TestBraintrustProxyAdapter:
    def _make_adapter(
        self,
        model: str = "claude-opus-4-8-20250514",
        api_key: str = "test-key",  # always provide a key; test ValueError separately
        project: str | None = None,
        env: dict | None = None,
    ):
        mock_client = _make_async_anthropic_client()
        captured: dict = {}

        def capture_constructor(**kwargs):
            captured.update(kwargs)
            return mock_client

        extra_env = env or {}
        with (
            patch("anthropic.AsyncAnthropic", side_effect=capture_constructor),
            patch.dict("os.environ", extra_env, clear=False),
        ):
            from importlib import reload

            import learning_commons_braintrust_scorers.adapter as mod

            reload(mod)
            adapter = mod.BraintrustProxyAdapter(model=model, api_key=api_key, project=project)

        adapter._client = mock_client
        return adapter, mock_client, captured

    def test_raises_when_no_api_key(self):
        import pytest
        from learning_commons_braintrust_scorers.adapter import BraintrustProxyAdapter
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key"):
                BraintrustProxyAdapter(api_key=None)

    def test_proxy_base_url(self):
        _, _, captured = self._make_adapter()
        assert captured["base_url"] == "https://api.braintrust.dev/v1/proxy"

    def test_api_key_from_argument(self):
        _, _, captured = self._make_adapter(api_key="my-key")
        assert captured["auth_token"] == "my-key"

    def test_api_key_from_env(self):
        # Pass api_key=None explicitly so env var is the only source
        _, _, captured = self._make_adapter(api_key=None, env={"BRAINTRUST_API_KEY": "env-key"})
        assert captured["auth_token"] == "env-key"

    def test_api_key_argument_takes_precedence_over_env(self):
        _, _, captured = self._make_adapter(
            api_key="arg-key", env={"BRAINTRUST_API_KEY": "env-key"}
        )
        assert captured["auth_token"] == "arg-key"

    def test_project_sets_bt_parent_header(self):
        _, _, captured = self._make_adapter(project="my-project")
        assert captured["default_headers"] == {"x-bt-parent": "project_name:my-project"}

    def test_no_project_omits_default_headers(self):
        _, _, captured = self._make_adapter(project=None)
        assert captured.get("default_headers", {}) == {}

    async def test_generate_returns_llm_response(self):
        msg = _make_anthropic_message(
            text="proxy output", model="claude-opus-4-8-20250514", input_tokens=8, output_tokens=12
        )
        adapter, mock_client, _ = self._make_adapter()
        mock_client.messages.create.return_value = msg

        result = await adapter.generate(system="sys", human="usr")

        assert isinstance(result, LLMResponse)
        assert result.content == "proxy output"
        assert result.input_tokens == 8
        assert result.output_tokens == 12

    async def test_generate_passes_system_and_human(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.generate(system="the system", human="the human")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "the system"
        assert call_kwargs["messages"] == [{"role": "user", "content": "the human"}]

    async def test_generate_default_max_tokens(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.generate(system="s", human="h")

        assert mock_client.messages.create.call_args[1]["max_tokens"] == 4096

    async def test_generate_default_temperature(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.generate(system="s", human="h")

        from anthropic import NOT_GIVEN
        assert mock_client.messages.create.call_args[1]["temperature"] is NOT_GIVEN

    async def test_generate_respects_config(self):
        adapter, mock_client, _ = self._make_adapter()
        config = GenerateConfig(temperature=0.1, max_tokens=256)

        await adapter.generate(system="s", human="h", config=config)

        kwargs = mock_client.messages.create.call_args[1]
        assert kwargs["max_tokens"] == 256
        assert kwargs["temperature"] == 0.1

    async def test_generate_uses_configured_model(self):
        adapter, mock_client, _ = self._make_adapter(model="claude-haiku-3-5-20251022")

        await adapter.generate(system="s", human="h")

        assert mock_client.messages.create.call_args[1]["model"] == "claude-haiku-3-5-20251022"

    async def test_aclose_calls_client_close(self):
        adapter, mock_client, _ = self._make_adapter()

        await adapter.aclose()

        mock_client.close.assert_called_once()


# ── Protocol conformance ──────────────────────────────────────────────────────


