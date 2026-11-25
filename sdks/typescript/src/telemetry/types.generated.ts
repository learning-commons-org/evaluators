// GENERATED — do not edit directly.
// Source: ../../evals/telemetry/event.schema.json
// Regenerate: python3 scripts/generate_telemetry_schema.py (from the repo root)
//
// The telemetry event's types and wire serialization. Keys are written in schema
// order, an unset optional field is omitted, and a key the schema does not declare
// is never written, whatever else the object passed in carries.

/** The `schema_version` this SDK's events are built against. */
export const TELEMETRY_SCHEMA_VERSION = 1 as const;

/** What an evaluation did, from the collector's point of view. */
export type EvaluationStatus = 'success' | 'error';

/** The SDK an event came from. */
export type SdkLanguage = 'python' | 'typescript';

/** Token counts reported by the model provider. */
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
}

/** One step of an evaluation: what ran, on which model, for how long, at what cost. */
export interface StageDetail {
  /** Stage name, e.g. `background_knowledge` or `complexity_evaluation`. */
  stage: string;

  /** `provider:model` for this stage. */
  provider: string;

  /** This stage's latency in milliseconds, including its retries. */
  latency_ms: number;
  token_usage?: TokenUsage;

  /**
   * Declared but never set by either SDK; to be replaced by `output_failure_kind`
   * (telemetry Phase B1).
   */
  schema_validation_failed?: boolean;
}

/**
 * The only place per-evaluator variation may live. Each property is one named, typed block
 * that an evaluator emits only when it has something to report in it; every block is
 * optional.
 */
export interface TelemetryMetadata {
  /**
   * One entry per completed step, in run order. Emitted by every evaluator that runs model
   * steps (single-step, multi-step, and Math Standards Alignment).
   */
  stage_details?: StageDetail[];
}

/**
 * One evaluation, reported once to the Learning Commons telemetry collector, whether it
 * succeeded or failed. This file is the single source of truth for the event both SDKs
 * send: their types and wire serialization are generated from it by
 * scripts/generate_telemetry_schema.py. Property order here is the order keys are written
 * on the wire, and an optional property is omitted rather than sent as null. No property
 * may carry the text being evaluated. Per-evaluator variation lives only in the named,
 * typed blocks under `metadata`; the rest of the envelope is the same for every evaluator.
 * Changing the wire shape means bumping `schema_version` in the same change (the
 * telemetry-schema check enforces it).
 */
export interface TelemetryEvent {
  /**
   * Version of this schema the event was built against. Bumped in the same change as any
   * wire-shape change; an event without it predates versioning.
   */
  schema_version: 1;

  /**
   * When the event was emitted (the evaluation's completion), as JavaScript's
   * Date.toISOString writes it: millisecond precision, Z suffix.
   */
  timestamp: string;

  /**
   * The emitting SDK's version. The Python SDK prefixes it with its package identifier; the
   * TypeScript SDK sends it bare.
   */
  sdk_version: string;

  /** Which SDK emitted the event. */
  sdk_language: SdkLanguage;

  /** The evaluator's current dotted registry id. */
  evaluator_type: string;

  /**
   * The grade evaluated. Always present: empty string for an evaluator that takes no grade,
   * or when the evaluation failed before the grade was known.
   */
  grade: string;
  status: EvaluationStatus;

  /** The error's class name, on a failed evaluation only. */
  error_code?: string;

  /** Wall-clock duration of the whole evaluation in milliseconds, including a failed one. */
  latency_ms: number;

  /**
   * Length of the evaluator's primary text input in UTF-16 code units (JavaScript's
   * String.length); 0 when the inputs were never validated.
   */
  text_length_chars: number;

  /**
   * `provider:model` for the model that answered, or that was being called when the
   * evaluation failed. `provider1+provider2` for an evaluator that reports a combined
   * label.
   */
  provider: string;

  /** Token usage summed over the steps that completed. Absent when no step completed. */
  token_usage?: TokenUsage;

  /** Per-evaluator extension blocks. Absent when no block has anything to report. */
  metadata?: TelemetryMetadata;

  /** true when the caller configured a model override; absent otherwise. */
  model_override?: boolean;
}

/** A `TokenUsage` as it goes on the wire. */
export function tokenUsageToWire(value: TokenUsage): Record<string, unknown> {
  const wire: Record<string, unknown> = {};
  wire['input_tokens'] = value.input_tokens;
  wire['output_tokens'] = value.output_tokens;
  return wire;
}

/** A `StageDetail` as it goes on the wire. */
export function stageDetailToWire(value: StageDetail): Record<string, unknown> {
  const wire: Record<string, unknown> = {};
  wire['stage'] = value.stage;
  wire['provider'] = value.provider;
  wire['latency_ms'] = value.latency_ms;
  if (value.token_usage !== undefined) wire['token_usage'] = tokenUsageToWire(value.token_usage);
  if (value.schema_validation_failed !== undefined) wire['schema_validation_failed'] = value.schema_validation_failed;
  return wire;
}

/** A `TelemetryMetadata` as it goes on the wire. */
export function telemetryMetadataToWire(value: TelemetryMetadata): Record<string, unknown> {
  const wire: Record<string, unknown> = {};
  if (value.stage_details !== undefined) wire['stage_details'] = value.stage_details.map(stageDetailToWire);
  return wire;
}

/** A `TelemetryEvent` as it goes on the wire. */
export function telemetryEventToWire(value: TelemetryEvent): Record<string, unknown> {
  const wire: Record<string, unknown> = {};
  wire['schema_version'] = value.schema_version;
  wire['timestamp'] = value.timestamp;
  wire['sdk_version'] = value.sdk_version;
  wire['sdk_language'] = value.sdk_language;
  wire['evaluator_type'] = value.evaluator_type;
  wire['grade'] = value.grade;
  wire['status'] = value.status;
  if (value.error_code !== undefined) wire['error_code'] = value.error_code;
  wire['latency_ms'] = value.latency_ms;
  wire['text_length_chars'] = value.text_length_chars;
  wire['provider'] = value.provider;
  if (value.token_usage !== undefined) wire['token_usage'] = tokenUsageToWire(value.token_usage);
  if (value.metadata !== undefined) wire['metadata'] = telemetryMetadataToWire(value.metadata);
  if (value.model_override !== undefined) wire['model_override'] = value.model_override;
  return wire;
}
