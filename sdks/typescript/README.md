# @learning-commons/evaluators

[![npm version](https://img.shields.io/npm/v/@learning-commons/evaluators)](https://www.npmjs.com/package/@learning-commons/evaluators)

TypeScript SDK for [Learning Commons evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction).

## Installation

Install the `@learning-commons/evaluators` and [Vercel AI](https://sdk.vercel.ai) SDKs:

```bash
npm install @learning-commons/evaluators ai
```

Next, install the provider adapter(s) for your LLM(s):

```bash
npm install @ai-sdk/openai     # OpenAI
npm install @ai-sdk/google     # Google Gemini
npm install @ai-sdk/anthropic  # Anthropic
```

## Quickstart

```typescript
import { GradeLevelAppropriatenessEvaluator } from "@learning-commons/evaluators";

const evaluator = new GradeLevelAppropriatenessEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate({ text: "The cat's out of the bag now." });
console.log(result.result.grade); // 4-5
```

## Documentation

| Evaluator                   | Documentation                                                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Grade Level Appropriateness | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/grade-level-appropriateness-evaluator/about-this-evaluator) |
| Background Knowledge Demands | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/subject-matter-knowledge/about-this-evaluator)              |
| Vocabulary Complexity       | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/vocabulary-evaluator/about-this-evaluator)                  |
| Sentence Structure          | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/sentence-structure-evaluator/about-this-evaluator)          |
| Meaning Directness          | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/conventionality/about-this-evaluator)                       |
| Purpose Clarity             | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/purpose/about-this-evaluator)                               |
| Reference Knowledge Demands | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/intertextuality)                                            |
| Organizational Structure    | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/organizational-structure)                                   |

For more implementation details, visit [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## License

MIT
