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
  temperature?: number;
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
   * Generate plain text from LLM
   */
  generateText(messages: Message[], temperature?: number): Promise<TextGenerationResponse>;
}

/**
 * Named constants for LLM provider types — use instead of raw string literals.
 */
export const Providers = {
  google: 'google',
  openai: 'openai',
  anthropic: 'anthropic',
  custom: 'custom',
} as const;

/**
 * Configuration for LLM provider
 */
export interface ProviderConfig {
  type: 'openai' | 'anthropic' | 'google' | 'custom';
  apiKey?: string;
  model?: string;
  temperature?: number;
  baseURL?: string;
  customProvider?: LLMProvider;
  maxRetries?: number;
}
