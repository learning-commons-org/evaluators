/**
 * Logging interface for the Evaluators SDK
 *
 * Provides structured logging with verbosity levels.
 * Users can inject custom loggers or use the default console logger.
 */

/**
 * Log levels in order of verbosity
 */
export enum LogLevel {
  /** Debug messages - very verbose, for development */
  DEBUG = 0,
  /** Informational messages - normal operations */
  INFO = 1,
  /** Warning messages - potentially problematic situations */
  WARN = 2,
  /** Error messages - errors that need attention */
  ERROR = 3,
  /** Silent - no logging */
  SILENT = 4,
}

/**
 * Context object for structured logging
 */
export interface LogContext {
  /** Evaluator type (vocabulary, sentence-structure, etc.) */
  evaluator?: string;
  /** Current operation or stage */
  operation?: string;
  /** Error object if applicable */
  error?: Error;
  /** Additional metadata */
  [key: string]: unknown;
}

/**
 * Logger interface
 *
 * Implement this interface to provide custom logging behavior.
 *
 * @example
 * ```typescript
 * const customLogger: Logger = {
 *   debug: (msg, ctx) => myLogger.debug(msg, ctx),
 *   info: (msg, ctx) => myLogger.info(msg, ctx),
 *   warn: (msg, ctx) => myLogger.warn(msg, ctx),
 *   error: (msg, ctx) => myLogger.error(msg, ctx),
 * };
 *
 * const evaluator = new VocabularyComplexityEvaluator({
 *   googleApiKey: '...',
 *   openaiApiKey: '...',
 *   logger: customLogger,
 *   logLevel: LogLevel.INFO,
 * });
 * ```
 */
export interface Logger {
  /**
   * Log debug message
   * Used for detailed debugging information
   */
  debug(message: string, context?: LogContext): void;

  /**
   * Log informational message
   * Used for normal operations
   */
  info(message: string, context?: LogContext): void;

  /**
   * Log warning message
   * Used for potentially problematic situations
   */
  warn(message: string, context?: LogContext): void;

  /**
   * Log error message
   * Used for errors that need attention
   */
  error(message: string, context?: LogContext): void;
}

/**
 * Default console logger implementation
 */
class ConsoleLogger implements Logger {
  constructor(private level: LogLevel = LogLevel.WARN) {}

  debug(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.DEBUG) {
      console.debug(`[DEBUG] ${message}`, context || '');
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.INFO) {
      console.info(`[INFO] ${message}`, context || '');
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.WARN) {
      console.warn(`[WARN] ${message}`, context || '');
    }
  }

  error(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.ERROR) {
      console.error(`[ERROR] ${message}`, context || '');
    }
  }
}

/**
 * Silent logger - logs nothing
 */
class SilentLogger implements Logger {
  debug(): void {}
  info(): void {}
  warn(): void {}
  error(): void {}
}

/**
 * Create a logger instance
 *
 * @param customLogger - Optional custom logger implementation
 * @param level - Log level (default: WARN)
 * @returns Logger instance
 */
export function createLogger(customLogger?: Logger, level: LogLevel = LogLevel.WARN): Logger {
  // Use custom logger if provided
  if (customLogger) {
    return customLogger;
  }

  // Use silent logger if level is SILENT
  if (level === LogLevel.SILENT) {
    return new SilentLogger();
  }

  // Use console logger with specified level
  return new ConsoleLogger(level);
}

/**
 * Format error for logging
 *
 * @internal
 */
export function formatError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}
