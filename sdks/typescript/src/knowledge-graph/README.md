# Knowledge Graph client

HTTP client for the [Learning Commons Knowledge Graph API](https://api.learningcommons.org/knowledge-graph/v0), used by `MathStandardsAlignmentEvaluator` to fetch academic standards and learning components.

## Files

| File | Purpose |
|---|---|
| `kg-api.d.ts` | **Generated.** TypeScript types from the KG OpenAPI spec — do not edit by hand |
| `types.ts` | Internal interfaces: `AcademicStandard`, `LearningComponent`, `StandardsRepository`, `parseGradeFromStandard` |
| `repository.ts` | `KnowledgeGraphApiRepository` — HTTP client for the live KG API |
| `client.ts` | `KnowledgeGraphClient` — promise cache + concurrency limiter |
| `index.ts` | Barrel |

## Regenerating `kg-api.d.ts`

Types are generated from the KG OpenAPI spec at:
```
https://docs.learningcommons.org/api-reference/knowledge-graph-api/openapi.yaml
```

To regenerate after a spec update:
```bash
npm run generate:kg-types
```

> **Note on spec enums:** `normalizedStatementType` and `gradeLevel` use `string` in our interfaces rather than the spec's enum types. The spec enums are incomplete — they omit values the API actually returns (`"Mathematical Practice"`, `"HS"`). The generated `kg-api.d.ts` is used selectively for schema types that are accurate.
