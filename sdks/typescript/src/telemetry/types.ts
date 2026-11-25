// The event's types are generated from evals/telemetry/event.schema.json, the single
// source of truth both SDKs generate from; see types.generated.ts. Only what is not part
// of the wire format is written by hand here.
export {
  TELEMETRY_SCHEMA_VERSION,
  telemetryEventToWire,
  type EvaluationStatus,
  type SdkLanguage,
  type StageDetail,
  type TelemetryEvent,
  type TelemetryMetadata,
  type TokenUsage,
} from './types.generated.js';

/** The `sdk_language` every event from this SDK carries. */
export const SDK_LANGUAGE = 'typescript' as const;

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
