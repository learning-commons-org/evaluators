import type { z } from 'zod';

/**
 * Message format for LLM conversations
 */
export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * Request configuration for structured LLM generation
 */
export interface LLMRequest<T> {
  messages: Message[];
  schema: z.ZodSchema<T>;
  /** `null` sends no temperature at all, for models that reject an explicit value. */
  temperature?: number | null;
  maxTokens?: number;
}

/**
 * Response from LLM with usage metadata
 */
export interface LLMResponse<T> {
  data: T;
  model: string;
  usage: {
    inputTokens: number;
    outputTokens: number;
  };
  latencyMs: number;
}

/**
 * Response from plain text generation
 */
export interface TextGenerationResponse {
  text: string;
  usage: {
    inputTokens: number;
    outputTokens: number;
  };
  latencyMs: number;
}

/**
 * Base interface for LLM provider implementations
 */
export interface LLMProvider {
  /** Canonical label for the provider and model in use (e.g. "openai:gpt-4o") */
  readonly label: string;

  /**
   * Generate structured output from LLM using Zod schema
   */
  generateStructured<T>(request: LLMRequest<T>): Promise<LLMResponse<T>>;

  /**
   * Generate plain text from LLM. `null` sends no temperature; omitting the
   * argument falls back to `ProviderConfig.temperature`.
   */
  generateText(messages: Message[], temperature?: number | null): Promise<TextGenerationResponse>;
}

/**
 * Configuration for LLM provider
 */
export interface ProviderConfig {
  type: 'openai' | 'anthropic' | 'google' | 'custom';
  apiKey?: string;
  model?: string;
  /** `null` sends no temperature at all. */
  temperature?: number | null;
  baseURL?: string;
  customProvider?: LLMProvider;
  maxRetries?: number;
}
