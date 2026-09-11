// TODO: Generate these types from the telemetry service OpenAPI/JSON Schema
// instead of maintaining them manually. This will prevent drift between
// client and server schemas.

/**
 * Evaluation status
 */
export type EvaluationStatus = 'success' | 'error';

/**
 * Token usage metrics from LLM providers
 */
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
}

/**
 * Per-stage details for multi-stage evaluations
 */
export interface StageDetail {
  /** Stage name (e.g., "background_knowledge", "complexity_evaluation") */
  stage: string;

  /** Provider used for this stage (e.g., "openai:gpt-4o") */
  provider: string;

  /** Total latency including all retries (ms) */
  latency_ms: number;

  /** Token usage aggregated across all attempts */
  token_usage?: TokenUsage;

  /**
   * Whether schema validation failed (indicates prompt needs clearer instructions)
   *
   * TODO: Not currently tracked. Vercel AI SDK abstracts validation away.
   * To implement: Add custom retry wrapper that catches validation errors.
   */
  schema_validation_failed?: boolean;
}

/**
 * Extensible metadata for telemetry events
 */
export interface TelemetryMetadata {
  /** Detailed breakdown by stage (for multi-stage evaluations) */
  stage_details?: StageDetail[];

}

/**
 * Telemetry event payload
 */
export interface TelemetryEvent {
  timestamp: string;
  sdk_version: string;
  evaluator_type: string;
  grade?: string;
  status: EvaluationStatus;
  error_code?: string;
  latency_ms: number;
  text_length_chars: number;
  provider: string; // Format: "provider:model" or "provider1+provider2" for multi-provider
  token_usage?: TokenUsage; // Aggregated across all stages and attempts
  metadata?: TelemetryMetadata; // Optional per-stage breakdown
  model_override?: boolean; // true when the caller supplied a modelOverride
  input_text?: string; // Input text (only if recordInputs enabled)
}

/**
 * Configuration for telemetry client
 */
export interface TelemetryConfig {
  /** Analytics service endpoint URL */
  endpoint: string;

  /** Learning Commons key for identified telemetry (sent as X-API-Key). Absent → anonymous. */
  learningCommonsApiKey?: string;

  /** Client ID for anonymous tracking (persistent UUID from ~/.config/learning-commons/config.json) */
  clientId: string;

  /** Enable telemetry (default: true) */
  enabled: boolean;

  /** Logger instance (respects the SDK's configured log level and custom logger) */
  logger: import('../logger.js').Logger;
}
