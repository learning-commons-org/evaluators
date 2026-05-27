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
npm install @ai-sdk/openai   # OpenAI
npm install @ai-sdk/google   # Google Gemini
npm install @ai-sdk/anthropic  # Anthropic
```

## Quickstart

```typescript
import { VocabularyEvaluator } from "@learning-commons/evaluators";

const evaluator = new VocabularyEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
});

const result = await evaluator.evaluate("Your text here", "5");

console.log(result.score); // "Moderately complex"
```

## Documentation

For more implementation details, visit [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## License

MIT
