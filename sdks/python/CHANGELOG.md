# Changelog

All notable changes to the `learning-commons-evaluators` Python SDK will be documented in this file.

## [1.0.0](https://github.com/learning-commons-org/evaluators/compare/sdks-python-v0.2.1...sdks-python-v1.0.0) (2026-09-29)


### ⚠ BREAKING CHANGES

* **sdk:** the Python SDK now requires Python 3.11 or newer. 3.10 reaches end of life in October 2026.
* **sdk:** evaluator ids move from `student_facing_text.*` to `text_complexity.*`. Results, telemetry and `metadata.id` all carry the new value, and lookups by the former id return nothing — `stable_id` is unchanged for callers keying across time.
* **sdk:** `learning_commons_evaluators.evaluators.student_facing_text.*` and `learning_commons_evaluators.schemas.student_facing_text.*` are now `...text_complexity.*`. Evaluator classes keep their names and are still re-exported from the package root, so `from learning_commons_evaluators import PurposeClarityEvaluator` is unaffected; only deep imports and the evaluator ids in results and telemetry change.
* **sdk:** the 0.2.0 public surface (VocabularyEvaluator, ConventionalityEvaluator, GradeLevelAppropriatenessEvaluator, their input and settings classes, EvaluatorConfig with nested provider configs, the create_config* factories, TelemetryConfig, the answer / explanation result shape, and the error hierarchy) is removed. The 1.0 surface replaces it in the following PRs; no aliases or migration shims are provided.

### Features

* **sdk:** complete the Text Complexity family on the single-step base (DSCR-2188) ([#313](https://github.com/learning-commons-org/evaluators/issues/313)) ([c1569d4](https://github.com/learning-commons-org/evaluators/commit/c1569d47e5fb8e772fc0e4b784bfdc4d3e77569a))
* **sdk:** contract loader, spec error taxonomy, and native provider adapters ([#277](https://github.com/learning-commons-org/evaluators/issues/277)) ([03d1a58](https://github.com/learning-commons-org/evaluators/commit/03d1a58775fd8c5d1a42670b84b367c659077e64))
* **sdk:** generate the Knowledge Graph OpenAPI client (DSCR-2185) ([5a1277b](https://github.com/learning-commons-org/evaluators/commit/5a1277b1c562d6ac3a247a042aa40148abe9b7da))
* **sdk:** Math Standards Alignment, by UUID or by standard code (DSCR-2190) ([#312](https://github.com/learning-commons-org/evaluators/issues/312)) ([f679d1c](https://github.com/learning-commons-org/evaluators/commit/f679d1c5025bd726934f3c6ad0b73ba6400a2c54))
* **sdk:** Python SDK Knowledge Graph client (DSCR-2185) ([46a33c3](https://github.com/learning-commons-org/evaluators/commit/46a33c38ed1c853451edac014953e6e65fd3177d))
* **sdk:** Python SDK telemetry emission from the evaluator base ([#291](https://github.com/learning-commons-org/evaluators/issues/291)) ([9409caa](https://github.com/learning-commons-org/evaluators/commit/9409caa204e6cf419e5464075fe4e940ddee11ba))
* **sdk:** single-step evaluators, flat config, envelope, and registry with three pilots ([#278](https://github.com/learning-commons-org/evaluators/issues/278)) ([5f19227](https://github.com/learning-commons-org/evaluators/commit/5f192279110c78e9047c2e81e58b9de65013ed56))
* **sdk:** the Feedback family's six remaining evaluators (DSCR-2189) ([#314](https://github.com/learning-commons-org/evaluators/issues/314)) ([bd4546d](https://github.com/learning-commons-org/evaluators/commit/bd4546d204c5df52be61e1ef63d34101540fde15))
* **sdk:** the multi-step evaluator base ([#286](https://github.com/learning-commons-org/evaluators/issues/286)) ([d0ab310](https://github.com/learning-commons-org/evaluators/commit/d0ab310a737d9a4f70906cbad1b9cad0f098a5fa))
* **sdk:** Vocabulary Complexity and Sentence Structure on the multi-step base ([#284](https://github.com/learning-commons-org/evaluators/issues/284)) ([dc2b04a](https://github.com/learning-commons-org/evaluators/commit/dc2b04ae5af3002a18b24db10b2a89cbe083c20e))


### Documentation

* **sdk:** bring the Python README up to the TypeScript README's coverage ([#320](https://github.com/learning-commons-org/evaluators/issues/320)) ([98d2cba](https://github.com/learning-commons-org/evaluators/commit/98d2cbaa9b6861218c6d436914f8a2a4410c6a76))


### Build System

* **sdk:** declare Python 3.14 support ([509657a](https://github.com/learning-commons-org/evaluators/commit/509657af8673b67cdaf57e69fd4917a08d70bc93))
* **sdk:** generate the Knowledge Graph client from a filtered spec ([#303](https://github.com/learning-commons-org/evaluators/issues/303)) ([111e19f](https://github.com/learning-commons-org/evaluators/commit/111e19feb430b590f39a1c1fbaf0f173450332cd))
* **sdk:** regenerate the math contract for the declared identifier ([e5daa07](https://github.com/learning-commons-org/evaluators/commit/e5daa07549840499d92e3123608f54e2e813e572))
* **sdk:** require Python 3.11 ([bad803e](https://github.com/learning-commons-org/evaluators/commit/bad803ef7ae1f9527a31007071bac3247e50154a))


### Code Refactoring

* **sdk:** remove the 0.2.0 evaluators, settings machinery, and LangChain provider ([#276](https://github.com/learning-commons-org/evaluators/issues/276)) ([415b119](https://github.com/learning-commons-org/evaluators/commit/415b119fcc9f89114df00f253eb006ad0c45a12d))
* **sdk:** rename the Text Complexity family through the Python SDK ([f7f8ab3](https://github.com/learning-commons-org/evaluators/commit/f7f8ab30af870f112770669fdf93754fa5581e3d))

## [0.2.1](https://github.com/learning-commons-org/evaluators/compare/sdks-python-v0.2.0...sdks-python-v0.2.1) (2026-09-18)


### Documentation

* Audit READMEs for v1.0 launch ([#213](https://github.com/learning-commons-org/evaluators/issues/213)) ([7e0a650](https://github.com/learning-commons-org/evaluators/commit/7e0a65008075a479f512d2a8410ed116a76ce19d))

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
