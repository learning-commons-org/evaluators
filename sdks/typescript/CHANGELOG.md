# Changelog

All notable changes to the `@learning-commons/evaluators` TypeScript SDK will be documented in this file.

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
