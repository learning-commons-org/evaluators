import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createLogger, formatError, LogLevel, type Logger } from '../../src/logger.js';

/**
 * The logger had no tests: only `warn` and `error` were exercised, incidentally, by
 * evaluators that happened to log. Level gating is the whole point of the module — a broken
 * comparison either floods a partner's stdout or silences a warning they needed.
 */

let calls: Record<'debug' | 'info' | 'warn' | 'error', string[]>;

beforeEach(() => {
  calls = { debug: [], info: [], warn: [], error: [] };
  for (const method of ['debug', 'info', 'warn', 'error'] as const) {
    vi.spyOn(console, method).mockImplementation((msg) => void calls[method].push(String(msg)));
  }
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('createLogger level gating', () => {
  it('emits everything at DEBUG', () => {
    const logger = createLogger(undefined, LogLevel.DEBUG);

    logger.debug('d');
    logger.info('i');
    logger.warn('w');
    logger.error('e');

    expect(calls.debug).toEqual(['[DEBUG] d']);
    expect(calls.info).toEqual(['[INFO] i']);
    expect(calls.warn).toEqual(['[WARN] w']);
    expect(calls.error).toEqual(['[ERROR] e']);
  });

  it('drops messages below the configured level', () => {
    const logger = createLogger(undefined, LogLevel.WARN);

    logger.debug('d');
    logger.info('i');
    logger.warn('w');

    expect(calls.debug).toEqual([]);
    expect(calls.info).toEqual([]);
    expect(calls.warn).toEqual(['[WARN] w']);
  });

  it('defaults to WARN', () => {
    // The default matters: it is what every partner gets who never sets `logLevel`.
    const logger = createLogger();

    logger.info('i');
    logger.warn('w');

    expect(calls.info).toEqual([]);
    expect(calls.warn).toEqual(['[WARN] w']);
  });

  it.each([
    [LogLevel.DEBUG, 'debug'] as const,
    [LogLevel.INFO, 'info'] as const,
    [LogLevel.WARN, 'warn'] as const,
    [LogLevel.ERROR, 'error'] as const,
  ])('emits %s at exactly its own level', (level, method) => {
    // The boundary, not just either side of it: each gate is `<=`, and a `<` would make the
    // level you asked for the first one silently dropped.
    createLogger(undefined, level)[method]('m');

    expect(calls[method]).toHaveLength(1);
  });

  it('suppresses warnings but not errors at ERROR', () => {
    // The highest level that still logs. `error`'s own gate can never be false here, since
    // SILENT is handled by returning a different logger entirely.
    const logger = createLogger(undefined, LogLevel.ERROR);

    logger.warn('w');
    logger.error('e');

    expect(calls.warn).toEqual([]);
    expect(calls.error).toEqual(['[ERROR] e']);
  });

  it('emits nothing at SILENT, including errors', () => {
    const logger = createLogger(undefined, LogLevel.SILENT);

    logger.debug('d');
    logger.info('i');
    logger.warn('w');
    logger.error('e');

    expect(Object.values(calls).flat()).toEqual([]);
  });

  it.each(['debug', 'info', 'warn', 'error'] as const)(
    '%s passes context through and substitutes empty string when absent',
    (method) => {
      // Logging `undefined` as the second argument prints the word "undefined" in most
      // consoles, which reads as a value the caller supplied.
      const logger = createLogger(undefined, LogLevel.DEBUG);
      const spy = vi.mocked(console[method]);

      logger[method]('with', { evaluator: 'x' });
      logger[method]('without');

      expect(spy.mock.calls[0][1]).toEqual({ evaluator: 'x' });
      expect(spy.mock.calls[1][1]).toBe('');
    },
  );
});

describe('createLogger with a custom logger', () => {
  function spyLogger(): Logger {
    return { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
  }

  it('returns the custom logger unwrapped', () => {
    const custom = spyLogger();

    expect(createLogger(custom)).toBe(custom);
  });

  it('does not apply level gating to a custom logger', () => {
    // The level belongs to the console implementation. A partner passing their own logger
    // filters on their side, so swallowing calls here would hide records they expected.
    const custom = spyLogger();

    createLogger(custom, LogLevel.SILENT).error('e');

    expect(custom.error).toHaveBeenCalledWith('e');
    expect(calls.error).toEqual([]);
  });
});

describe('formatError', () => {
  it('names the error type alongside the message', () => {
    expect(formatError(new TypeError('bad input'))).toBe('TypeError: bad input');
  });

  it('keeps a custom error name', () => {
    const error = new Error('boom');
    error.name = 'RateLimitError';

    expect(formatError(error)).toBe('RateLimitError: boom');
  });

  it('keeps the colon when the message is empty', () => {
    // `String(error)` drops it, so this is what distinguishes formatting an Error from
    // stringifying one — for every other Error the two happen to agree.
    expect(formatError(new Error(''))).toBe('Error: ');
  });

  it('stringifies what was thrown when it is not an Error', () => {
    // Providers throw strings and plain objects; the logger must not crash on them.
    expect(formatError('just a string')).toBe('just a string');
    expect(formatError(undefined)).toBe('undefined');
    expect(formatError(null)).toBe('null');
    expect(formatError(404)).toBe('404');
  });
});
