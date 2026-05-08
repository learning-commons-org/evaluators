# Error Handling

The SDK provides specific error types to help you handle different scenarios:

```typescript
import {
  ConfigurationError,
  ValidationError,
  APIError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
} from "@learning-commons/evaluators";

try {
  const evaluator = new VocabularyEvaluator({ googleApiKey, openaiApiKey });
  const result = await evaluator.evaluate(text, grade);
} catch (error) {
  if (error instanceof ConfigurationError) {
    // Missing or invalid API keys — fix your config
    console.error("Configuration error:", error.message);
  } else if (error instanceof ValidationError) {
    // Invalid input (text too short, invalid grade, etc.)
    console.error("Invalid input:", error.message);
  } else if (error instanceof AuthenticationError) {
    // Invalid API keys
    console.error("Check your API keys:", error.message);
  } else if (error instanceof RateLimitError) {
    // Rate limit exceeded - wait and retry
    console.error("Rate limited. Retry after:", error.retryAfter);
  } else if (error instanceof NetworkError) {
    // Network connectivity issues
    console.error("Network error:", error.message);
  } else if (error instanceof TimeoutError) {
    // Request timed out
    console.error("Timeout:", error.message);
  } else if (error instanceof APIError) {
    // Other API errors
    console.error("API error:", error.message, "Status:", error.statusCode);
  }
}
```
