"""Live Knowledge Graph calls: the three endpoints the SDK uses, against the real service.

Skipped unless ``RUN_INTEGRATION_TESTS=1`` and ``LEARNING_COMMONS_API_KEY`` is set. The unit
tests cover the client's behaviour through a mock transport; what only a live run can tell
us is that the vendored OpenAPI spec still describes the service — that the fields the
generated models require are the fields it actually sends.

The standard below is a Common Core one that has been stable for years and carries learning
components, which is what makes it a usable canary. A failure here means either the spec
needs refreshing (``make fetch-kg-openapi && make generate-kg-client``) or the service
changed; it does not mean the client's logic regressed.

One exception, worth knowing before debugging a certificate error: ``httpx`` follows the
system proxy, so a local intercepting proxy re-signs the response with a root that is in
the OS keychain but not in ``certifi``, and these tests fail with a ``NetworkError`` that
is about the proxy rather than the service. Bypass it for this host::

    NO_PROXY=api.learningcommons.org RUN_INTEGRATION_TESTS=1 make integration-test
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest

from learning_commons_evaluators.dependencies.knowledge_graph import KnowledgeGraphClient
from learning_commons_evaluators.errors import StandardNotFoundError
from learning_commons_evaluators.schemas.kg_taxonomy import AcademicSubject, Jurisdiction

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("LEARNING_COMMONS_API_KEY"),
        reason="set LEARNING_COMMONS_API_KEY to run live Knowledge Graph tests",
    ),
]

_STATEMENT_CODE = "3.MD.C.7.D"


@pytest.fixture
async def kg() -> AsyncIterator[KnowledgeGraphClient]:
    client = KnowledgeGraphClient(os.environ["LEARNING_COMMONS_API_KEY"], max_retries=2)
    try:
        yield client
    finally:
        await client.aclose()


async def test_the_three_endpoints_round_trip(kg: KnowledgeGraphClient) -> None:
    matches = await kg.search_standards(
        _STATEMENT_CODE,
        jurisdiction=Jurisdiction.MULTI_STATE,
        academic_subject=AcademicSubject.MATHEMATICS,
    )
    assert matches, "the canary standard should always resolve"
    assert matches[0].normalized_code == _STATEMENT_CODE

    standard = await kg.get_academic_standard(matches[0].case_identifier_uuid)
    assert standard.case_identifier_uuid == matches[0].case_identifier_uuid
    assert standard.description

    components = await kg.get_learning_component_set(standard.case_identifier_uuid)
    assert components.components, "the canary standard should have learning components"
    assert all(c.identifier and c.description for c in components.components)


async def test_an_unknown_statement_code_is_not_found(kg: KnowledgeGraphClient) -> None:
    with pytest.raises(StandardNotFoundError):
        await kg.search_standards("ZZ.NOT.A.REAL.CODE")
