# Changelog

All notable changes to the `@learning-commons/evaluators` TypeScript SDK will be documented in this file.

## [0.6.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.5.0...sdks-typescript-v0.6.0) (2026-05-22)


### Features

* **ts-sdk:** add bypassRowLimit option for batch evaluator ([#77](https://github.com/learning-commons-org/evaluators/issues/77)) ([902a60f](https://github.com/learning-commons-org/evaluators/commit/902a60fc934372a151f1d40c0b49ef3313d12609))
* **ts-sdk:** expose per-call token usage on EvaluationMetadata ([#59](https://github.com/learning-commons-org/evaluators/issues/59)) ([3c8fa0f](https://github.com/learning-commons-org/evaluators/commit/3c8fa0fd8e2389fc902c9cf1f63985b40d2e4b2c))

## [0.5.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.4.0...sdks-typescript-v0.5.0) (2026-05-07)


### Features

* **ts-sdk:** add modelOverride option to all evaluators ([#34](https://github.com/learning-commons-org/evaluators/issues/34)) ([c57c4fc](https://github.com/learning-commons-org/evaluators/commit/c57c4fc86bc56846afe92e6d451705642e399309))
* **ts-sdk:** Add Purpose evaluator ([#57](https://github.com/learning-commons-org/evaluators/issues/57)) ([8b6d715](https://github.com/learning-commons-org/evaluators/commit/8b6d715b49ba1911de35ccc1b6aeaef888289a1d))

## [0.4.0] — 2026-03-23

### Added

- **Batch CSV Evaluator** — CLI tool and programmatic API for evaluating multiple texts from a CSV file in parallel. Runs the `text-complexity` group (GLA, SMK, Vocabulary, Sentence Structure, and Conventionality) across up to 50 rows and produces CSV and HTML reports.

---

## [0.3.0] — 2026-03-20

### Added

- **Conventionality Evaluator** — evaluates how explicit, literal, and straightforward a text's meaning is versus how abstract, ironic, figurative, or archaic it is, relative to grades 3–12.
- **Conventionality added to TextComplexityEvaluator** — composite evaluator now runs vocabulary, sentence structure, SMK, and conventionality in parallel; result includes `conventionality` key.

---

## [0.2.0] — 2026-03-18

### Added

- **Subject Matter Knowledge (SMK) Evaluator** — evaluates background knowledge demands of educational texts relative to grades 3–12.
- **SMK added to TextComplexityEvaluator** — composite evaluator now runs vocabulary, sentence structure, and SMK in parallel; result includes `subjectMatterKnowledge` key.
- **Prompt versioning** — prompts updated to v1.3.0 (`evals/prompts/subject-matter-knowledge/`).

---

## [0.1.0] — Early Release

Initial early release of the TypeScript SDK for Learning Commons educational evaluators.

### Added

- **Vocabulary Evaluator** — grades 3–12 vocabulary difficulty assessment.
- **Sentence Structure Evaluator** — syntactic complexity analysis by grade level.
- **Grade Level Appropriateness (GLA) Evaluator** — overall grade-level suitability scoring.
- **Text Complexity Evaluator** — composite evaluation combining Vocabulary, Sentence Structure, and GLA.
- **Provider abstraction** — model-agnostic via Vercel AI SDK; OpenAI, Google, and Anthropic supported.
- **Telemetry** — opt-in, with `partnerKey` and `recordInputs` (defaults to `false`).
- **Prompt versioning** — prompts versioned in `evals/prompts/` (v1.2.0), shared with Python notebooks.
