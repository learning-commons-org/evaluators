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

const result = await evaluator.evaluate("The cat's out of the bag now.");
console.log(result.score); // 4-5
```

## Documentation

| Evaluator                   | Documentation                                                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Grade Level Appropriateness | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/grade-level-appropriateness-evaluator/about-this-evaluator) |
| Subject Matter Knowledge    | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/subject-matter-knowledge/about-this-evaluator)              |
| Vocabulary                  | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/vocabulary-evaluator/about-this-evaluator)                  |
| Sentence Structure          | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/sentence-structure-evaluator/about-this-evaluator)          |
| Conventionality             | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/conventionality/about-this-evaluator)                       |
| Purpose                     | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/purpose/about-this-evaluator)                               |

For more implementation details, visit [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## License

MIT
