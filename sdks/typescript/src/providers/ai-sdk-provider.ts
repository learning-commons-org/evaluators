import { generateText as aiGenerateText, Output } from 'ai';
import type {
  LLMProvider,
  LLMRequest,
  LLMResponse,
  Message,
  ProviderConfig,
} from './base.js';

/**
 * Default models for each provider based on Python implementation
 */
const DEFAULT_MODELS = {
  openai: 'gpt-4o',
  anthropic: 'claude-sonnet-4-5-20250929',
  google: 'gemini-2.5-pro',
} as const;

/**
 * Vercel AI SDK provider implementation
 * Supports OpenAI, Anthropic, and Google Gemini
 */
export class VercelAIProvider implements LLMProvider {
  readonly label: string;

  constructor(private config: ProviderConfig) {
    if (config.type === 'custom') {
      throw new Error(
        'VercelAIProvider does not support custom type. Use config.customProvider directly.'
      );
    }
    this.label = `${config.type}:${config.model ?? DEFAULT_MODELS[config.type]}`;
  }

  /**
   * Generate structured output using Vercel AI SDK's generateText with output
   */
  async generateStructured<T>(request: LLMRequest<T>): Promise<LLMResponse<T>> {
    const model = await this.getModel(request.model);
    const startTime = Date.now();

    const { output, usage } = await aiGenerateText({
      model,
      messages: request.messages,
      output: Output.object({ schema: request.schema }),
      temperature: request.temperature ?? 0,
      maxRetries: this.config.maxRetries ?? 0,
      ...(request.maxTokens !== undefined ? { maxTokens: request.maxTokens } : {}),
    });

    return {
      data: output as T,
      model: request.model || this.getDefaultModel(),
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

    const { text, usage } = await aiGenerateText({
      model,
      messages,
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
   * Uses dynamic imports so consumers only need to install the provider packages they use.
   */
  private async getModel(requestModel?: string) {
    const modelId = requestModel || this.config.model || this.getDefaultModel();
    const apiKey = this.config.apiKey;

    switch (this.config.type) {
      case 'openai': {
        const { createOpenAI } = await import('@ai-sdk/openai').catch(() => {
          throw new Error(
            'To use the OpenAI provider, install its adapter: npm install @ai-sdk/openai'
          );
        });
        return createOpenAI(apiKey ? { apiKey } : {})(modelId);
      }
      case 'anthropic': {
        const { createAnthropic } = await import('@ai-sdk/anthropic').catch(() => {
          throw new Error(
            'To use the Anthropic provider, install its adapter: npm install @ai-sdk/anthropic'
          );
        });
        return createAnthropic(apiKey ? { apiKey } : {})(modelId);
      }
      case 'google': {
        const { createGoogleGenerativeAI } = await import('@ai-sdk/google').catch(() => {
          throw new Error(
            'To use the Google provider, install its adapter: npm install @ai-sdk/google'
          );
        });
        return createGoogleGenerativeAI(apiKey ? { apiKey } : {})(modelId);
      }
      default:
        throw new Error(`Unsupported provider type: ${this.config.type}`);
    }
  }

  /**
   * Get default model for the configured provider
   */
  private getDefaultModel(): string {
    const providerType = this.config.type;

    if (providerType === 'custom') {
      throw new Error('Cannot get default model for custom provider type');
    }

    return DEFAULT_MODELS[providerType];
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
