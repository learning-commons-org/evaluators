# Changelog

All notable changes to the `@learning-commons/evaluators` TypeScript SDK will be documented in this file.

## [0.5.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.4.0...sdks-typescript-v0.5.0) (2026-04-08)


### Features

* Add Conventionality evaluator to TypeScript SDK ([#25](https://github.com/learning-commons-org/evaluators/issues/25)) ([5ca6976](https://github.com/learning-commons-org/evaluators/commit/5ca69768168eb47458693b9abd8a6a5e9402e523))
* Add SMK evaluator to TypeScript SDK ([#21](https://github.com/learning-commons-org/evaluators/issues/21)) ([a90fb42](https://github.com/learning-commons-org/evaluators/commit/a90fb429b6df112e3095f9f361d17d9d42152cf1))
* Implement Batch Evaluator ([#16](https://github.com/learning-commons-org/evaluators/issues/16)) ([a0c78ab](https://github.com/learning-commons-org/evaluators/commit/a0c78ab24fe4b6e7b1a57586b288d842ca954ec2))
* Release TypeScript SDK 0.1.0 ([#20](https://github.com/learning-commons-org/evaluators/issues/20)) ([46eeea9](https://github.com/learning-commons-org/evaluators/commit/46eeea9c1222b8c28761d8ddc795e3364fa55726))

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
