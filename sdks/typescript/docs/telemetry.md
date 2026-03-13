# Telemetry

## Why We Collect Telemetry

We use telemetry data to improve evaluator quality, identify edge cases, and optimize performance. This helps us build better tools for our developer partners.

Telemetry is **anonymous by default**. If you'd like to partner with us to improve your specific use case, you can optionally provide an API key (see Configuration section below). This allows us to connect with you and collaborate more deeply.

## What We Collect

**By default, telemetry is enabled** and sends:
- Performance metrics (latency, token usage)
- Metadata (evaluator type, grade, SDK version)

**Input text is NOT collected by default.** You can opt in via `recordInputs: true` — see [Enable Input Text Collection](#enable-input-text-collection) below.

We **never** collect your API keys (only an anonymous identifier).

If you prefer not to send any telemetry, you can disable it entirely — see [Disable Telemetry Completely](#disable-telemetry-completely) below.

## Example Telemetry Event

```json
{
  "timestamp": "2026-02-05T19:30:00.000Z",
  "sdk_version": "0.1.0",
  "evaluator_type": "vocabulary",
  "grade": "3",
  "status": "success",
  "latency_ms": 3500,
  "text_length_chars": 456,
  "provider": "openai:gpt-4o-2024-11-20 + google:gemini-2.5-pro",
  "token_usage": {
    "input_tokens": 650,
    "output_tokens": 350
  },
  "metadata": {
    "stage_details": [
      {
        "stage": "background_knowledge",
        "provider": "openai:gpt-4o-2024-11-20",
        "latency_ms": 1200,
        "token_usage": {
          "input_tokens": 250,
          "output_tokens": 150
        }
      },
      {
        "stage": "complexity_evaluation",
        "provider": "google:gemini-2.5-pro",
        "latency_ms": 2300,
        "token_usage": {
          "input_tokens": 400,
          "output_tokens": 200
        }
      }
    ]
  }
}
```

## Field Reference

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp when evaluation started |
| `sdk_version` | Version of the SDK (e.g., "0.1.0") |
| `evaluator_type` | Which evaluator ran (e.g., "vocabulary", "sentence-structure") |
| `grade` | Grade level evaluated (e.g., "5", "K") |
| `status` | Evaluation outcome: "success" or "error" |
| `error_code` | Error type if status is "error" (e.g., "Error", "TypeError") |
| `latency_ms` | Total evaluation time in milliseconds |
| `text_length_chars` | Length of input text in characters |
| `provider` | LLM provider(s) used (e.g., "openai:gpt-4o", "google:gemini-2.5-pro+openai:gpt-4o") |
| `token_usage` | Total tokens consumed (input, output) |
| `input_text` | The text being evaluated (only included if `recordInputs: true`) |
| `metadata.stage_details` | Per-stage breakdown for multi-stage evaluators (optional) |

## Configuration

### Default (Anonymous)

```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY!,
  openaiApiKey: process.env.OPENAI_API_KEY!,
  // telemetry: true (default - anonymous)
});
```

### Partner with Us (Authenticated)

To help us support your specific use case, provide an API key:

```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY!,
  openaiApiKey: process.env.OPENAI_API_KEY!,
  partnerKey: process.env.LEARNING_COMMONS_PARTNER_KEY!,  // Contact us for a key
});
```

### Disable Telemetry Completely

```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY!,
  openaiApiKey: process.env.OPENAI_API_KEY!,
  telemetry: false,  // No data sent
});
```

### Enable Input Text Collection

```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY!,
  openaiApiKey: process.env.OPENAI_API_KEY!,
  telemetry: {
    enabled: true,
    recordInputs: true,  // Also send input text with telemetry
  },
});
```
