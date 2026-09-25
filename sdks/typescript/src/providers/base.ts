import type { z } from 'zod';

/**
 * Message format for LLM conversations
 */
export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/** Image formats every supported vendor accepts natively. */
export type ImageMediaType = 'image/png' | 'image/jpeg' | 'image/webp';

/**
 * An image the model is asked to read alongside the prompt text.
 *
 * Carried on the request rather than inside a message so that text-only providers,
 * including caller-supplied ones, keep their `content: string` contract unchanged. A
 * provider that can attach images says so with {@link LLMProvider.supportsAttachments};
 * one that cannot is refused before any call rather than silently sent text alone.
 */
export interface ImageAttachment {
  type: 'image';
  data: Uint8Array;
  mediaType: ImageMediaType;
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
  /** Images to place on the final user turn, ahead of its text. */
  attachments?: readonly ImageAttachment[];
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
   * Whether {@link LLMRequest.attachments} are honoured. Absent means no: an evaluator
   * that needs to attach an image refuses such a provider up front.
   */
  readonly supportsAttachments?: boolean;

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
