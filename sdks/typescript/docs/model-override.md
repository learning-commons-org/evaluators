# Model Override

By default each evaluator uses a recommended provider and model tuned for that task. You can override this with any supported provider — OpenAI, Google, or Anthropic — using the `modelOverride` option.

When `modelOverride` is set:

- All LLM calls within the evaluator use the specified provider and model
- Only the API key for the override provider is required (e.g. `anthropicApiKey` when using `Provider.Anthropic`); default provider keys are not validated
- A warning is logged to indicate results may differ from the defaults
- Telemetry records `model_override: true` so override usage is tracked separately

**Validation:** The SDK validates `modelOverride` at construction time and throws `ConfigurationError` if:

- `provider` is not one of the supported `Provider` values (`openai`, `google`, `anthropic`)
- `model` is empty or blank — no default is assumed; you must always specify the model ID explicitly
- The API key for the chosen provider is missing

If the model ID is valid at construction but doesn't exist on the provider's API, `ConfigurationError` is thrown when `evaluate()` is called.

```typescript
import { VocabularyEvaluator, Provider } from "@learning-commons/evaluators";

const evaluator = new VocabularyEvaluator({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  modelOverride: {
    provider: Provider.Anthropic,
    model: "claude-sonnet-4-6",
  },
});

const result = await evaluator.evaluate("Your text here", "5");
console.log(result.metadata.model); // "anthropic:claude-sonnet-4-6"
```

See the [Installation](#installation) section for provider adapter setup if you haven't already.

> **Note:** Evaluators are validated and quality-tested against their default models. Results with other models may vary. Check `result.metadata.model` to confirm which model was used.
