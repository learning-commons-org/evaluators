# Prompts Changelog

All notable changes to the evaluator prompt files will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.5.0](https://github.com/learning-commons-org/evaluators/compare/evals-prompts-v1.4.0...evals-prompts-v1.5.0) (2026-04-08)


### Features

* add Conventionality evaluator notebooks ([#23](https://github.com/learning-commons-org/evaluators/issues/23)) ([b17cfb7](https://github.com/learning-commons-org/evaluators/commit/b17cfb728723d27277fcc4a986d95c6189010cd4))
* Add conventionality prompt ([#22](https://github.com/learning-commons-org/evaluators/issues/22)) ([4838eaf](https://github.com/learning-commons-org/evaluators/commit/4838eaf8a8ff2907dcbd2471adb23a45d707ffd6))
* Add SMK evaluator to TypeScript SDK ([#21](https://github.com/learning-commons-org/evaluators/issues/21)) ([a90fb42](https://github.com/learning-commons-org/evaluators/commit/a90fb429b6df112e3095f9f361d17d9d42152cf1))
* add Subject Matter Knowledge (SMK) evaluator ([#17](https://github.com/learning-commons-org/evaluators/issues/17)) ([9ba45d5](https://github.com/learning-commons-org/evaluators/commit/9ba45d5c8a3280d3676188f0906f081509858674))
* Expand Vocab with evals for other grades ([#6](https://github.com/learning-commons-org/evaluators/issues/6)) ([8988061](https://github.com/learning-commons-org/evaluators/commit/8988061cf4a09598a2be196e10f99310598f221b))
* initial upload of Evaluators repository ([7bfc69d](https://github.com/learning-commons-org/evaluators/commit/7bfc69d1dbc623cf49a1e1118ef3852874bff1ba))
* Release TypeScript SDK 0.1.0 ([#20](https://github.com/learning-commons-org/evaluators/issues/20)) ([46eeea9](https://github.com/learning-commons-org/evaluators/commit/46eeea9c1222b8c28761d8ddc795e3364fa55726))
* Update SS with evals for Grade 5-12 ([#5](https://github.com/learning-commons-org/evaluators/issues/5)) ([43c343a](https://github.com/learning-commons-org/evaluators/commit/43c343abe155f7c19a09e9a93d4a629a51ed0ee3))

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
