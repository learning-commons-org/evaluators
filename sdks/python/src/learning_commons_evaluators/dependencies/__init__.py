"""Clients for the non-LLM services evaluators call.

LLM vendors live in :mod:`learning_commons_evaluators.providers`, behind one protocol with
one adapter each. Everything else lives here: today the Learning Commons Knowledge Graph,
which the math standards evaluator reads its learning components from.

The public surface is :mod:`.knowledge_graph`. Underneath it, ``_generated/`` holds the
OpenAPI-generated transport, which is committed but private — it is regenerated wholesale
by ``make generate-kg-client``, so nothing outside the wrapper should name it.
"""

from learning_commons_evaluators.dependencies.knowledge_graph import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    STANDARD_SEARCH_LIMIT,
    AcademicStandard,
    KnowledgeGraphClient,
    LearningComponent,
    LearningComponentSet,
    StandardMatch,
    normalize_statement_code,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "STANDARD_SEARCH_LIMIT",
    "AcademicStandard",
    "KnowledgeGraphClient",
    "LearningComponent",
    "LearningComponentSet",
    "StandardMatch",
    "normalize_statement_code",
]
