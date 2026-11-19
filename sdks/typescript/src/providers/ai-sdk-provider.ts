import { generateText as aiGenerateText, Output } from 'ai';
import { ConfigurationError, refused } from '../errors.js';

/** Node's resolution codes for "that package is not there", ESM and CJS. */
const NOT_INSTALLED = new Set(['ERR_MODULE_NOT_FOUND', 'MODULE_NOT_FOUND']);

/**
 * Turn a failed adapter import into the right error.
 *
 * Only an unresolvable module is the caller's setup. An adapter that *is* installed but
 * throws while loading — a syntax error, a missing transitive dependency — is a real failure,
 * and reporting "install its adapter" for it would send the reader somewhere useless. That
 * case rethrows unchanged so the evaluator wraps it as a dependency failure, and the
 * not-installed case keeps the original as `cause` either way.
 */
function adapterImportError(error: unknown, vendor: string, pkg: string): unknown {
  // Structured signal only, per SPEC §6.5: wording is not a contract, and matching on it
  // would reclassify an adapter that failed to load for some other reason. Walked rather
  // than read off the top, because bundlers and test loaders wrap an import failure in their
  // own error and keep the real one as `cause` — sometimes through more than one layer, hence
  // walking the chain rather than checking a fixed depth.
  const missing = (function isMissing(e: unknown, depth = 0): boolean {
    if (e === null || typeof e !== 'object' || depth > 4) return false;
    const { code, cause } = e as { code?: unknown; cause?: unknown };
    if (typeof code === 'string' && NOT_INSTALLED.has(code)) return true;
    return isMissing(cause, depth + 1);
  })(error);

  return missing
    ? new ConfigurationError(
        `To use the ${vendor} provider, install its adapter: npm install ${pkg}`,
        error,
      )
    : error;
}
import type {
  ImageAttachment,
  LLMProvider,
  LLMRequest,
  LLMResponse,
  Message,
  ProviderConfig,
} from './base.js';

/**
 * A reasoning effort as the vendor adapter's own option, sent as the vendor's parameter
 * unchanged. Not the AI SDK's provider-neutral `reasoning` option, which maps some values to
 * neighbours (Anthropic `minimal` to `low`) where the contract's value is the validated one.
 *
 * For OpenAI, `reasoningSummary: null` stops the adapter adding a `detailed` summary request
 * the Python SDK does not send, and `forceReasoning` stops it dropping the effort for a model
 * id its release does not list as reasoning (4.0.0 does not list `gpt-6-*`).
 */
function reasoningOptions(
  type: ProviderConfig['type'],
  effort: string | undefined
): { providerOptions?: Record<string, Record<string, string | boolean | null | Record<string, string>>> } {
  if (effort === undefined) return {};
  switch (type) {
    case 'openai':
      return {
        providerOptions: {
          openai: { reasoningEffort: effort, reasoningSummary: null, forceReasoning: true },
        },
      };
    case 'anthropic':
      return { providerOptions: { anthropic: { effort } } };
    case 'google':
      return { providerOptions: { google: { thinkingConfig: { thinkingLevel: effort } } } };
    default:
      return {};
  }
}

/** The parts of an AI SDK result that say whether, and why, the provider refused. */
interface RefusalSignals {
  finishReason?: string;
  providerMetadata?: Record<string, Record<string, unknown>> | undefined;
  response?: { headers?: Record<string, string> | undefined } | undefined;
}

/**
 * Throw `LLMRefusalError` when Anthropic refused the request.
 *
 * Anthropic answers a refusal with HTTP 200 and `stop_reason: "refusal"`, which its
 * adapter reports as the `content-filter` finish reason, with the category and
 * explanation under `providerMetadata.anthropic.stopDetails`. Checked before the
 * result's `output` is read: that getter throws a bare "No output generated." for a
 * refusal, which says nothing about why. Older models omit the stop details, so the
 * category and explanation may be absent.
 */
function throwIfRefused(result: RefusalSignals, type: ProviderConfig['type'], label: string, model: string): void {
  if (type !== 'anthropic' || result.finishReason !== 'content-filter') return;
  const details = result.providerMetadata?.anthropic?.stopDetails as
    | { category?: unknown; explanation?: unknown }
    | undefined;
  const headers = result.response?.headers;
  const requestId = headers?.['request-id'] ?? headers?.['x-request-id'];
  throw refused(label, {
    dependency: 'anthropic',
    model,
    category: typeof details?.category === 'string' ? details.category : null,
    explanation: typeof details?.explanation === 'string' ? details.explanation : null,
    requestId: typeof requestId === 'string' ? requestId : null,
  });
}

/**
 * Place attachments on the final user turn, before or after its text as each one's
 * `position` says, in array order, as the AI SDK's content parts. Each image travels as a
 * `file` part — bytes plus media type, the one inline form every vendor adapter accepts
 * (the SDK's older `image` part is deprecated). Turns before the last user turn, and all
 * text-only requests, pass through unchanged.
 */
function withAttachments(messages: Message[], attachments: readonly ImageAttachment[] | undefined) {
  if (!attachments?.length) return messages;
  const last = messages.map((m) => m.role).lastIndexOf('user');
  if (last === -1) {
    throw new Error('Attachments need a user message to be attached to.');
  }
  const parts = (position: ImageAttachment['position']) =>
    attachments
      .filter((a) => a.position === position)
      .map((a) => ({ type: 'file' as const, data: a.data, mediaType: a.mediaType }));
  return messages.map((m, i) =>
    i === last
      ? {
          role: 'user' as const,
          content: [...parts('before_text'), { type: 'text' as const, text: m.content }, ...parts('after_text')],
        }
      : m,
  );
}

/**
 * Vercel AI SDK provider implementation
 * Supports OpenAI, Anthropic, and Google Gemini
 */
export class VercelAIProvider implements LLMProvider {
  readonly label: string;
  readonly supportsAttachments = true;
  private readonly model: string;

  constructor(private config: ProviderConfig) {
    if (config.type === 'custom') {
      throw new Error(
        'VercelAIProvider does not support custom type. Use config.customProvider directly.'
      );
    }
    if (!config.model || config.model.trim() === '') {
      throw new Error(
        `model is required for VercelAIProvider (type: "${config.type}"). No default is assumed.`
      );
    }
    this.model = config.model;
    this.label = `${config.type}:${config.model}`;
  }

  /**
   * Generate structured output using Vercel AI SDK's generateText with output
   */
  async generateStructured<T>(request: LLMRequest<T>): Promise<LLMResponse<T>> {
    const model = await this.getModel();
    const startTime = Date.now();

    const systemMsg = request.messages.find((m) => m.role === 'system');
    const nonSystemMessages = request.messages.filter((m) => m.role !== 'system');

    const result = await aiGenerateText({
      model,
      ...(systemMsg ? { system: systemMsg.content } : {}),
      messages: withAttachments(nonSystemMessages, request.attachments),
      output: Output.object({ schema: request.schema }),
      // A null temperature means "send nothing" — see config.schema.json for
      // which models require that.
      ...(request.temperature != null ? { temperature: request.temperature } : {}),
      maxRetries: this.config.maxRetries ?? 0,
      // maxOutputTokens is the vendor option; `maxTokens` is silently discarded.
      ...(request.maxTokens !== undefined ? { maxOutputTokens: request.maxTokens } : {}),
      ...reasoningOptions(this.config.type, request.reasoningEffort),
    });
    // Before `output` is read: for a refusal that getter throws without saying why.
    throwIfRefused(result, this.config.type, this.label, this.model);
    const { output, usage } = result;

    return {
      data: output as T,
      model: this.model,
      usage: {
        inputTokens: usage.inputTokens || 0,
        outputTokens: usage.outputTokens || 0,
      },
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Generate plain text using Vercel AI SDK's generateText
   */
  async generateText(
    messages: Message[],
    temperature?: number | null
  ): Promise<import('./base.js').TextGenerationResponse> {
    const model = await this.getModel();
    const startTime = Date.now();

    const systemMsg = messages.find((m) => m.role === 'system');
    const nonSystemMessages = messages.filter((m) => m.role !== 'system');
    // Only an absent argument falls back to config; an explicit null means
    // "send nothing" and must not be overridden by it.
    const effectiveTemperature =
      temperature === undefined ? this.config.temperature : temperature;

    const result = await aiGenerateText({
      model,
      ...(systemMsg ? { system: systemMsg.content } : {}),
      messages: nonSystemMessages,
      ...(effectiveTemperature != null ? { temperature: effectiveTemperature } : {}),
      maxRetries: this.config.maxRetries ?? 0,
    });
    throwIfRefused(result, this.config.type, this.label, this.model);
    const { text, usage } = result;

    return {
      text,
      usage: {
        inputTokens: usage.inputTokens || 0,
        outputTokens: usage.outputTokens || 0,
      },
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Get the configured language model.
   *
   * Uses dynamic imports so consumers only need to install the provider packages
   * they actually use. The `webpackIgnore` / `turbopackIgnore` / `@vite-ignore`
   * magic comments stop bundlers (Next.js, webpack, Vite/Rollup, etc.) from
   * statically resolving the uninstalled providers at build time — without them,
   * bundling fails with "Module not found: Can't resolve '@ai-sdk/...'" even
   * though the import is guarded at runtime.
   */
  private async getModel() {
    const apiKey = this.config.apiKey;

    switch (this.config.type) {
      case 'openai': {
        const { createOpenAI } = await import(
          /* webpackIgnore: true */ /* turbopackIgnore: true */ /* @vite-ignore */ '@ai-sdk/openai'
        ).catch((error: unknown) => {
          throw adapterImportError(error, 'OpenAI', '@ai-sdk/openai');
        });
        return createOpenAI(apiKey ? { apiKey } : {})(this.model);
      }
      case 'anthropic': {
        const { createAnthropic } = await import(
          /* webpackIgnore: true */ /* turbopackIgnore: true */ /* @vite-ignore */ '@ai-sdk/anthropic'
        ).catch((error: unknown) => {
          throw adapterImportError(error, 'Anthropic', '@ai-sdk/anthropic');
        });
        return createAnthropic(apiKey ? { apiKey } : {})(this.model);
      }
      case 'google': {
        const { createGoogleGenerativeAI } = await import(
          /* webpackIgnore: true */ /* turbopackIgnore: true */ /* @vite-ignore */ '@ai-sdk/google'
        ).catch((error: unknown) => {
          throw adapterImportError(error, 'Google', '@ai-sdk/google');
        });
        return createGoogleGenerativeAI(apiKey ? { apiKey } : {})(this.model);
      }
      default:
        throw new Error(`Unsupported provider type: ${this.config.type}`);
    }
  }
}

/**
 * Factory function to create a provider instance
 */
export function createProvider(config: ProviderConfig): LLMProvider {
  if (config.type === 'custom' && config.customProvider) {
    return config.customProvider;
  }

  return new VercelAIProvider(config);
}
