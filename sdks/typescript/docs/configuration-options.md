# Configuration Options

All evaluators use the same `BaseEvaluatorConfig` interface:

```typescript
interface BaseEvaluatorConfig {
  googleApiKey?: string; // Google API key (required by some evaluators)
  openaiApiKey?: string; // OpenAI API key (required by some evaluators)
  anthropicApiKey?: string; // Anthropic API key (required if an evaluator defaults to Claude or when `modelOverride` uses `Provider.Anthropic`)
  modelOverride?: ModelOverride; // Override the provider and model (see Model Override section)
  maxRetries?: number; // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger; // Custom logger
  logLevel?: LogLevel; // Log verbosity (default: WARN)
  partnerKey?: string; // Learning Commons partner key for authenticated telemetry
}
```

**Note:** Which API keys are required depends on the evaluator. The SDK validates required keys at runtime based on the evaluator's metadata:

- **Vocabulary**: Requires both `googleApiKey` and `openaiApiKey`
- **Sentence Structure**: Requires `openaiApiKey` only
- **Subject Matter Knowledge**: Requires `googleApiKey` only
- **Conventionality**: Requires `googleApiKey` only
- **Text Complexity**: Requires both `googleApiKey` and `openaiApiKey`
- **Grade Level Appropriateness**: Requires `googleApiKey` only
- **Purpose**: Requires `googleApiKey` only

When `modelOverride` is set, the default key requirements are bypassed — only the key for the override provider is required (e.g. `anthropicApiKey` when using `Provider.Anthropic`).
