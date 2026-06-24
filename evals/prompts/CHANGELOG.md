# Prompts Changelog

All notable changes to the evaluator prompt files will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.6.0](https://github.com/learning-commons-org/evaluators/compare/evals-prompts-v1.5.0...evals-prompts-v1.6.0) (2026-06-24)


### Features

* add Quill productive-coaching feedback evaluators (early access) ([#114](https://github.com/learning-commons-org/evaluators/pull/114)) ([1294761](https://github.com/learning-commons-org/evaluators/commit/129476104f783450dfcc7e0f1b499fdeeb76ba4d))
* add Intertextuality evaluator (early access) ([#113](https://github.com/learning-commons-org/evaluators/pull/113)) ([6e5a703](https://github.com/learning-commons-org/evaluators/commit/6e5a70335c014fc1e8d804816c2c459dc5407a67))

## [1.5.0](https://github.com/learning-commons-org/evaluators/compare/evals-prompts-v1.4.0...evals-prompts-v1.5.0) (2026-05-07)


### Features

* add Purpose evaluator (early access) ([#51](https://github.com/learning-commons-org/evaluators/issues/51)) ([5fe4f82](https://github.com/learning-commons-org/evaluators/commit/5fe4f82cd3990f6b4c46e66d2ab1f812c5923840))

## [1.4.0] - 2026-03-20

### Added
- `conventionality/system.txt` — system prompt for early access Conventionality evaluator
- `conventionality/user.txt` — user prompt for early access Conventionality evaluator 

## [1.3.0] - 2026-03-18

### Added
- `subject-matter-knowledge/system.txt` — system prompt for the SMK evaluator
- `subject-matter-knowledge/user.txt` — user prompt for the SMK evaluator

## [1.2.0] - 2026-02-19

### Added
- `vocabulary/other-grades-system.txt` — system prompt for Vocabulary evaluator (grades 5–12)
- `vocabulary/other-grades-user.txt` — user prompt for Vocabulary evaluator (grades 5–12)

### Changed
- `vocabulary/grades-3-4-system.txt` — updated to reference "Qualitative Text Complexity rubric (SAP)"

## [1.1.0] - 2026-02-18

### Added
- `sentence-structure/rubric-grades-5-12.txt` — SS complexity scoring rubric for grades 5–12

### Changed
- `sentence-structure/complexity-system.txt` — updated to reference "Qualitative Text Complexity rubric (SAP)"
- `sentence-structure/analysis-user.txt` — added `Basic Complex` and `Advanced Complex` to the sentence type definitions

## [1.0.0] - 2025-09-23

### Added
- `grade-level-appropriateness/system.txt` — system prompt for the GLA evaluator
- `grade-level-appropriateness/user.txt` — user prompt for the GLA evaluator
- `sentence-structure/analysis-system.txt` — system prompt for SS sentence analysis
- `sentence-structure/analysis-user.txt` — user prompt for SS sentence analysis
- `sentence-structure/complexity-system.txt` — system prompt for SS complexity scoring
- `sentence-structure/complexity-user.txt` — user prompt for SS complexity scoring
- `sentence-structure/rubric-grade-3.txt` — SS complexity scoring rubric for grade 3
- `sentence-structure/rubric-grade-4.txt` — SS complexity scoring rubric for grade 4
- `vocabulary/background-knowledge.txt` — background knowledge context for the Vocabulary evaluator
- `vocabulary/grades-3-4-system.txt` — system prompt for Vocabulary evaluator (grades 3–4)
- `vocabulary/grades-3-4-user.txt` — user prompt for Vocabulary evaluator (grades 3–4)
