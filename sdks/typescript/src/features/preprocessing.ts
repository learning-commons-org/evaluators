import textReadability from 'text-readability';

export interface PostTransformConfig {
  type: string;
  precision?: number;
}

export interface PreprocessingImplementation {
  library: string;
  function: string;
  post_transform?: PostTransformConfig;
}

// ---------------------------------------------------------------------------
// Library adapters
// To add support for a new library: add one entry here.
// ---------------------------------------------------------------------------

interface LibraryAdapter {
  call(fnName: string, text: string): number;
}

const LIBRARY_ADAPTERS: Partial<Record<string, LibraryAdapter>> = {
  'text-readability': {
    call(fnName, text) {
      const fn = textReadability[fnName];
      if (typeof fn !== 'function') {
        throw new Error(`Function "${fnName}" not found in text-readability.`);
      }
      return fn.call(textReadability, text);
    },
  },
};

// ---------------------------------------------------------------------------
// Post-transform handlers
// To add a new transform type: add one entry here.
// ---------------------------------------------------------------------------

type PostTransformHandler = (value: number, config: PostTransformConfig) => number;

const POST_TRANSFORMS: Partial<Record<string, PostTransformHandler>> = {
  round(value, { precision = 0 }) {
    const factor = 10 ** precision;
    return Math.round(value * factor) / factor;
  },
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Runs a single config-declared preprocessing step against `text`.
 * Pass the language-specific implementation block (e.g. config.implementation.typescript).
 *
 * Throws if the library or post_transform type is not registered above.
 */
export function runPreprocessingStep(text: string, impl: PreprocessingImplementation): number {
  const adapter = LIBRARY_ADAPTERS[impl.library];
  if (!adapter) {
    const supported = Object.keys(LIBRARY_ADAPTERS).join(', ');
    throw new Error(
      `Unsupported preprocessing library "${impl.library}". Supported: ${supported}.`,
    );
  }

  let result = adapter.call(impl.function, text);

  if (impl.post_transform) {
    const transform = POST_TRANSFORMS[impl.post_transform.type];
    if (!transform) {
      const supported = Object.keys(POST_TRANSFORMS).join(', ');
      throw new Error(
        `Unsupported post_transform type "${impl.post_transform.type}". Supported: ${supported}.`,
      );
    }
    result = transform(result, impl.post_transform);
  }

  return result;
}
