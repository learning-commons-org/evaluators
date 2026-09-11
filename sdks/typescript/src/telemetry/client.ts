import type { TelemetryConfig, TelemetryEvent } from './types.js';
import type { Logger } from '../logger.js';

/**
 * Telemetry client for sending analytics events
 *
 * Fire-and-forget implementation that never blocks SDK operations.
 * Errors are logged but don't fail evaluations.
 */
export class TelemetryClient {
  private config: TelemetryConfig;
  private logger: Logger;

  constructor(config: TelemetryConfig) {
    this.config = config;
    this.logger = config.logger;
  }

  /**
   * Send telemetry event to analytics service
   *
   * Fire-and-forget: Errors are logged but don't throw.
   */
  async send(event: TelemetryEvent): Promise<void> {
    if (!this.config.enabled) {
      return;
    }

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Client-ID': this.config.clientId,
      };

      // Identified telemetry is opt-in; absent key means anonymous events.
      if (this.config.learningCommonsApiKey) {
        headers['X-API-Key'] = this.config.learningCommonsApiKey;
      }

      const response = await fetch(this.config.endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(event),
        // Don't block SDK operations on slow networks
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      if (!response.ok) {
        this.logger.warn(
          `[Telemetry] Failed to send event: ${response.status} ${response.statusText}`
        );
      }
    } catch (error) {
      if (error instanceof Error) {
        // Don't log timeout errors (expected on slow networks)
        if (error.name !== 'TimeoutError' && error.name !== 'AbortError') {
          this.logger.warn(`[Telemetry] Error sending event: ${error.message}`);
        }
      }
    }
  }
}
