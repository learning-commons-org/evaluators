# Results

Successful evaluations return an `EvaluationResult` with three top-level fields (`answer`, `explanation`, `metadata`):

| Field                 | Description                                                 |
| --------------------- | ----------------------------------------------------------- |
| `answer`              | The evaluation score and label                              |
| `explanation.summary` | Main reasoning string from the model                        |
| `explanation.details` | Evaluator-specific structured fields (dict)                 |
| `metadata`            | Run metadata: timing, status, token usage, per-step details |

```python
result.metadata.status              # Status.succeeded on success
result.metadata.processing_time_ms
result.metadata.total_token_usage   # dict[LLMProvider, TokenUsage]
result.metadata.step_details        # per prompt step: timing, token usage, prompt settings
```

On failure, the same metadata object (`result.metadata` on success) is updated with `status=failed` and a sanitized `error_details`, emitted on the evaluation end log line, then `evaluate` / `evaluate_sync` **re-raise** without returning a result.
