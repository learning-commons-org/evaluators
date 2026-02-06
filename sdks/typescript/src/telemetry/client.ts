import type { TelemetryConfig, TelemetryEvent } from './types.js';

/**
 * Telemetry client for sending analytics events
 *
 * Fire-and-forget implementation that never blocks SDK operations.
 * Errors are logged but don't fail evaluations.
 */
export class TelemetryClient {
  private config: TelemetryConfig;

  constructor(config: TelemetryConfig) {
    this.config = config;
  }

  /**
   * Send telemetry event to analytics service
   *
   * Fire-and-forget: Errors are logged but don't throw.
   */
  async send(event: TelemetryEvent): Promise<void> {
    // Skip if telemetry disabled
    if (!this.config.enabled) {
      return;
    }

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Client-ID': this.config.clientId,
      };

      // Add API key if provided
      if (this.config.apiKey) {
        headers['X-API-Key'] = this.config.apiKey;
      }

      const response = await fetch(this.config.endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(event),
        // Don't block SDK operations on slow networks
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      if (!response.ok) {
        console.error(
          `[Telemetry] Failed to send event: ${response.status} ${response.statusText}`
        );
      }
    } catch (error) {
      // Log error but never throw (fire-and-forget)
      if (error instanceof Error) {
        // Don't log timeout errors (expected on slow networks)
        if (error.name !== 'TimeoutError' && error.name !== 'AbortError') {
          console.error('[Telemetry] Error sending event:', error.message);
        }
      }
    }
  }
}
