import { generateText, Output } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
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
  constructor(private config: ProviderConfig) {
    if (config.type === 'custom') {
      throw new Error(
        'VercelAIProvider does not support custom type. Use config.customProvider directly.'
      );
    }
  }

  /**
   * Generate structured output using Vercel AI SDK's generateText with output
   */
  async generateStructured<T>(request: LLMRequest<T>): Promise<LLMResponse<T>> {
    const model = this.getModel(request.model);
    const startTime = Date.now();

    try {
      const baseParams = {
        model,
        messages: request.messages,
        output: Output.object({ schema: request.schema }),
        temperature: request.temperature ?? 0,
        maxRetries: this.config.maxRetries ?? 0,
      };

      const params = request.maxTokens !== undefined
        ? { ...baseParams, maxTokens: request.maxTokens }
        : baseParams;

      const { output, usage } = await generateText(params as Parameters<typeof generateText>[0]);

      return {
        data: output,
        model: request.model || this.getDefaultModel(),
        usage: {
          inputTokens: usage.inputTokens || 0,
          outputTokens: usage.outputTokens || 0,
        },
        latencyMs: Date.now() - startTime,
      };
    } catch (error) {
      throw new Error(
        `Failed to generate structured output: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Generate plain text using Vercel AI SDK's generateText
   */
  async generateText(messages: Message[], temperature?: number): Promise<import('./base.js').TextGenerationResponse> {
    const model = this.getModel();
    const startTime = Date.now();

    try {
      const params = {
        model,
        messages,
        temperature: temperature ?? this.config.temperature ?? 0,
        maxRetries: this.config.maxRetries ?? 0,
      };

      const { text, usage } = await generateText(params as Parameters<typeof generateText>[0]);

      return {
        text,
        usage: {
          inputTokens: usage.inputTokens || 0,
          outputTokens: usage.outputTokens || 0,
        },
        latencyMs: Date.now() - startTime,
      };
    } catch (error) {
      throw new Error(
        `Failed to generate text: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Get the configured language model
   */
  private getModel(requestModel?: string) {
    const modelId = requestModel || this.config.model || this.getDefaultModel();
    const apiKey = this.config.apiKey;

    switch (this.config.type) {
      case 'openai': {
        const provider = createOpenAI(apiKey ? { apiKey } : {});
        return provider(modelId);
      }
      case 'anthropic': {
        const provider = createAnthropic(apiKey ? { apiKey } : {});
        return provider(modelId);
      }
      case 'google': {
        const provider = createGoogleGenerativeAI(apiKey ? { apiKey } : {});
        return provider(modelId);
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
