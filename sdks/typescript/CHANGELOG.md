# Changelog

All notable changes to the `@learning-commons/evaluators` TypeScript SDK will be documented in this file.

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
