"""Tests for :mod:`learning_commons_evaluators.telemetry.utils`."""

from __future__ import annotations

import uuid

from learning_commons_evaluators.telemetry.utils import client_id_from_seed


class TestClientIdFromSeed:
    def test_deterministic_for_same_namespace_and_key(self):
        ns = uuid.UUID("018f1234-5678-7abc-8def-0123456789ab")
        assert client_id_from_seed("my-api-key", ns) == client_id_from_seed("my-api-key", ns)

    def test_different_api_keys_differ(self):
        ns = uuid.UUID("018f1234-5678-7abc-8def-0123456789ab")
        assert client_id_from_seed("a", ns) != client_id_from_seed("b", ns)

    def test_same_api_key_different_namespace_differs(self):
        assert client_id_from_seed("k", uuid.uuid4()) != client_id_from_seed("k", uuid.uuid4())

    def test_returns_valid_uuid_string(self):
        uuid.UUID(client_id_from_seed("any-key", uuid.uuid4()))

    def test_strips_whitespace_on_api_key(self):
        ns = uuid.UUID("018f1234-5678-7abc-8def-0123456789ab")
        assert client_id_from_seed("  k  ", ns) == client_id_from_seed("k", ns)
