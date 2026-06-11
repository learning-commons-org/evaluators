# Changelog

All notable changes to the `learning-commons-evaluators` Python SDK will be documented in this file.

## [0.2.0](https://github.com/learning-commons-org/evaluators/compare/sdks-python-v0.1.0...sdks-python-v0.2.0) (2026-06-11)


### Features

* **python-sdk:** add Grade Level Appropriateness evaluator ([#92](https://github.com/learning-commons-org/evaluators/issues/92)) ([7232104](https://github.com/learning-commons-org/evaluators/commit/7232104b90870ea9fab2ca630535f004db73ebf8))

## 0.1.0 (2026-05-22)

Initial early release of the Python SDK for Learning Commons educational evaluators.

### Features
  - **Vocabulary Evaluator** — grades 3–12 vocabulary difficulty assessment.
  - **Conventionality Evaluator** — evaluates how explicit, literal, and straightforward a text's meaning is versus how abstract, ironic, figurative, or archaic it is, relative to grades 3–12.
  - **Async-first API** — evaluators expose `async evaluate(...)`, with a synchronous `evaluate_sync(...)` wrapper for non-async callers.
  - **Provider abstraction** — model-agnostic via LangChain; OpenAI, Google, and Anthropic supported.
