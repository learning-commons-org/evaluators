# Knowledge Graph client

HTTP client for the [Learning Commons Knowledge Graph API](https://api.learningcommons.org/knowledge-graph/v0), used by `MathStandardsAlignmentEvaluator` to fetch academic standards and learning components.

## Files

| File | Purpose |
|---|---|
| `kg-api.d.ts` | **Generated.** TypeScript types from the KG OpenAPI spec — do not edit by hand |
| `types.ts` | Internal types: `AcademicStandard`, `LearningComponent`, `StandardInfo`, `parseGradeFromStandard` |
| `client.ts` | `KnowledgeGraphClient` — HTTP calls, concurrency limiting, promise caching |
| `index.ts` | Barrel |

## Regenerating `kg-api.d.ts`

```bash
npm run generate:kg-types
```

Pulls the spec from `https://docs.learningcommons.org/api-reference/knowledge-graph-api/openapi.yaml`.

> **Note on spec enums:** `normalizedStatementType` and `gradeLevel` use `string` in our interfaces rather than the spec's enum types — the spec enums are incomplete (omit `"Mathematical Practice"` and `"HS"`).
