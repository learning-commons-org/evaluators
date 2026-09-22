"""Clients for the non-LLM services evaluators call.

LLM vendors live in :mod:`learning_commons_evaluators.providers`, behind one protocol with
one adapter each. Everything else belongs here: today the Learning Commons Knowledge
Graph, which the math standards evaluator reads its learning components from.

``_generated/`` holds the OpenAPI-generated transport. It is committed but private — it is
regenerated wholesale by ``make generate-kg-client``, so nothing outside this package
should name it. The hand-written wrapper that will be the supported surface lands next;
until then this package carries the transport and nothing imports it.
"""
