import { generateText as aiGenerateText, Output } from 'ai';
import type {
  LLMProvider,
  LLMRequest,
  LLMResponse,
  Message,
  ProviderConfig,
} from './base.js';

/**
 * Vercel AI SDK provider implementation
 * Supports OpenAI, Anthropic, and Google Gemini
 */
export class VercelAIProvider implements LLMProvider {
  readonly label: string;
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

    const { output, usage } = await aiGenerateText({
      model,
      ...(systemMsg ? { system: systemMsg.content } : {}),
      messages: nonSystemMessages,
      output: Output.object({ schema: request.schema }),
      temperature: request.temperature ?? 0,
      maxRetries: this.config.maxRetries ?? 0,
      // maxOutputTokens is the vendor option; `maxTokens` is silently discarded.
      ...(request.maxTokens !== undefined ? { maxOutputTokens: request.maxTokens } : {}),
    });

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
  async generateText(messages: Message[], temperature?: number): Promise<import('./base.js').TextGenerationResponse> {
    const model = await this.getModel();
    const startTime = Date.now();

    const systemMsg = messages.find((m) => m.role === 'system');
    const nonSystemMessages = messages.filter((m) => m.role !== 'system');

    const { text, usage } = await aiGenerateText({
      model,
      ...(systemMsg ? { system: systemMsg.content } : {}),
      messages: nonSystemMessages,
      temperature: temperature ?? this.config.temperature ?? 0,
      maxRetries: this.config.maxRetries ?? 0,
    });

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
        ).catch(() => {
          throw new Error(
            'To use the OpenAI provider, install its adapter: npm install @ai-sdk/openai'
          );
        });
        return createOpenAI(apiKey ? { apiKey } : {})(this.model);
      }
      case 'anthropic': {
        const { createAnthropic } = await import(
          /* webpackIgnore: true */ /* turbopackIgnore: true */ /* @vite-ignore */ '@ai-sdk/anthropic'
        ).catch(() => {
          throw new Error(
            'To use the Anthropic provider, install its adapter: npm install @ai-sdk/anthropic'
          );
        });
        return createAnthropic(apiKey ? { apiKey } : {})(this.model);
      }
      case 'google': {
        const { createGoogleGenerativeAI } = await import(
          /* webpackIgnore: true */ /* turbopackIgnore: true */ /* @vite-ignore */ '@ai-sdk/google'
        ).catch(() => {
          throw new Error(
            'To use the Google provider, install its adapter: npm install @ai-sdk/google'
          );
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
