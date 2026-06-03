# Changelog

All notable changes to the `learning-commons-evaluators` Python SDK will be documented in this file.

## 0.1.0 (2026-05-22)

Initial early release of the Python SDK for Learning Commons educational evaluators.

### Features
  - **Vocabulary Evaluator** — grades 3–12 vocabulary difficulty assessment.
  - **Conventionality Evaluator** — evaluates how explicit, literal, and straightforward a text's meaning is versus how abstract, ironic, figurative, or archaic it is, relative to grades 3–12.
  - **Async-first API** — evaluators expose `async evaluate(...)`, with a synchronous `evaluate_sync(...)` wrapper for non-async callers.
  - **Provider abstraction** — model-agnostic via LangChain; OpenAI, Google, and Anthropic supported. 
