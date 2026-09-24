"""Tests for :mod:`learning_commons_evaluators.telemetry` (send path, scheduling, guards)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from learning_commons_evaluators import (
    create_config,
    create_config_telemetry_with_full_input,
)
from learning_commons_evaluators.schemas.common_inputs import GradeInputField, TextInputField
from learning_commons_evaluators.schemas.input_specs import GradeInputSpec, TextInputSpec
from learning_commons_evaluators.schemas.metadata import Status
from learning_commons_evaluators.schemas.text_complexity import TextComplexityEvaluationInput
from learning_commons_evaluators.telemetry import (
    schedule_send_telemetry,
    send_telemetry,
    should_send_telemetry,
)
from learning_commons_evaluators.telemetry.utils import client_id_from_seed


def _sample_evaluation_input() -> TextComplexityEvaluationInput:
    return TextComplexityEvaluationInput(
        text=TextInputField(spec=TextInputSpec(name="text"), value="hello world"),
        grade_level=GradeInputField(spec=GradeInputSpec(name="grade_level"), value=3),
    )


def _mock_async_httpx_client(mock_client_class: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    mock_client_class.return_value.__aexit__.return_value = None
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.text = ""
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


class TestShouldSendTelemetry:
    def test_false_without_partner_id(self, config):
        assert should_send_telemetry(config) is False

    def test_true_with_partner_id(self):
        cfg = create_config(telemetry_partner_id="tid")
        assert should_send_telemetry(cfg) is True


class TestScheduleSendTelemetry:
    def test_does_not_submit_when_partner_missing(self, config, evaluation_metadata):
        with patch("learning_commons_evaluators.telemetry._get_telemetry_executor") as mock_exec:
            schedule_send_telemetry(evaluation_metadata, None, config)
        mock_exec.assert_not_called()

    @patch("learning_commons_evaluators.telemetry._get_telemetry_executor")
    def test_submits_to_shared_executor(self, mock_get_executor, evaluation_metadata):
        cfg = create_config(telemetry_partner_id="tid")
        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        schedule_send_telemetry(evaluation_metadata, None, cfg)

        mock_get_executor.assert_called_once()
        mock_executor.submit.assert_called_once()


class TestSendTelemetryHttp:
    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_posts_json_body_on_success(self, mock_client_class, evaluation_metadata):
        mock_client = _mock_async_httpx_client(mock_client_class)

        cfg = create_config(telemetry_partner_id="tid")
        evaluation_metadata.status = Status.succeeded
        evaluation_metadata.input_metadata = {"grade_level": {"grade": 3}}

        asyncio.run(send_telemetry(evaluation_metadata, None, cfg))

        mock_client_class.assert_called_once()
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == cfg.telemetry.endpoint
        payload = call_args[1]["json"]
        assert payload["evaluator_type"] == "test-evaluator"
        assert payload["status"] == "success"
        assert payload["grade"] == "3"
        assert "learning-commons-evaluators-python" in payload["sdk_version"]
        assert "input_text" not in payload
        headers = call_args[1]["headers"]
        assert headers["X-Client-ID"] == client_id_from_seed("tid", cfg.client_id_seed)
        assert headers["X-API-Key"] == "tid"

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_uuid_partner_uses_same_value_as_client_id_only(
        self, mock_client_class, evaluation_metadata
    ):
        partner_uuid = "550e8400-e29b-41d4-a716-446655440000"
        mock_client = _mock_async_httpx_client(mock_client_class)
        cfg = create_config(telemetry_partner_id=partner_uuid)
        evaluation_metadata.status = Status.succeeded

        asyncio.run(send_telemetry(evaluation_metadata, None, cfg))

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-Client-ID"] == partner_uuid
        assert "X-API-Key" not in headers

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_includes_input_text_when_full_input_enabled(
        self, mock_client_class, evaluation_metadata
    ):
        mock_client = _mock_async_httpx_client(mock_client_class)

        cfg = create_config_telemetry_with_full_input(telemetry_partner_id="tid")
        evaluation_metadata.status = Status.succeeded
        inp = _sample_evaluation_input()

        asyncio.run(send_telemetry(evaluation_metadata, inp, cfg))

        payload = mock_client.post.call_args[1]["json"]
        assert payload["input_text"] == "hello world"

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_omits_input_text_when_full_input_disabled(
        self, mock_client_class, evaluation_metadata
    ):
        mock_client = _mock_async_httpx_client(mock_client_class)

        cfg = create_config(telemetry_partner_id="tid", send_full_input_with_telemetry=False)
        evaluation_metadata.status = Status.succeeded
        inp = _sample_evaluation_input()

        asyncio.run(send_telemetry(evaluation_metadata, inp, cfg))

        payload = mock_client.post.call_args[1]["json"]
        assert "input_text" not in payload

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_posts_json_body_on_failed_run(self, mock_client_class, evaluation_metadata):
        mock_client = _mock_async_httpx_client(mock_client_class)

        cfg = create_config(telemetry_partner_id="tid")
        evaluation_metadata.status = Status.failed
        evaluation_metadata.error_details = "boom"

        asyncio.run(send_telemetry(evaluation_metadata, None, cfg))

        payload = mock_client.post.call_args[1]["json"]
        assert payload["status"] == "error"
        assert "boom" in (payload.get("error_code") or "")

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_send_telemetry_posts_via_asyncio_run(self, mock_client_class, evaluation_metadata):
        _mock_async_httpx_client(mock_client_class)

        cfg = create_config(telemetry_partner_id="tid")
        evaluation_metadata.status = Status.succeeded

        asyncio.run(send_telemetry(evaluation_metadata, None, cfg))

        mock_client_class.assert_called_once()

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_send_telemetry_no_op_without_partner(
        self, mock_client_class, config, evaluation_metadata
    ):
        asyncio.run(send_telemetry(evaluation_metadata, None, config))
        mock_client_class.assert_not_called()

    @patch("learning_commons_evaluators.telemetry.httpx.AsyncClient")
    def test_timestamp_is_set_at_send_time_not_evaluation_start(
        self, mock_client_class, evaluation_metadata
    ):
        _mock_async_httpx_client(mock_client_class)
        cfg = create_config(telemetry_partner_id="tid")
        evaluation_metadata.timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        evaluation_metadata.status = Status.succeeded

        before = datetime.now(timezone.utc)
        asyncio.run(send_telemetry(evaluation_metadata, None, cfg))
        after = datetime.now(timezone.utc)

        payload = mock_client_class.return_value.__aenter__.return_value.post.call_args[1]["json"]
        sent = datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
        assert before <= sent <= after

    @patch(
        "learning_commons_evaluators.telemetry.evaluation_to_typescript_telemetry_event",
        side_effect=RuntimeError("adapter blew up"),
    )
    def test_send_telemetry_swallows_non_http_errors(self, _mock_adapter, evaluation_metadata):
        mock_logger = MagicMock()
        cfg = create_config(telemetry_partner_id="tid", logger=mock_logger)
        asyncio.run(send_telemetry(evaluation_metadata, None, cfg))
        mock_logger.warning.assert_called_once()


class TestClientIdSeed:
    def test_same_partner_id_across_configs_yields_same_client_id(self):
        cfg_a = create_config(telemetry_partner_id="my-key")
        cfg_b = create_config(telemetry_partner_id="my-key")
        assert cfg_a.client_id_seed == cfg_b.client_id_seed
        assert client_id_from_seed("my-key", cfg_a.client_id_seed) == client_id_from_seed(
            "my-key", cfg_b.client_id_seed
        )
