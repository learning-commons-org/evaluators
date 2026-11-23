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

/** Where an attachment goes on the final user turn, relative to its text; the contract declares it. */
export type AttachmentPosition = 'before_text' | 'after_text';

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
  position: AttachmentPosition;
}

/**
 * Request configuration for structured LLM generation
 */
export interface LLMRequest<T> {
  messages: Message[];
  schema: z.ZodSchema<T>;
  /** `null` sends no temperature at all, for models that reject an explicit value. */
  temperature?: number | null;
  /**
   * The most tokens the model may generate, reasoning tokens included on a reasoning model.
   * Absent leaves the provider's own limit. An evaluator sets it from a step's
   * `generation.max_output_tokens`, only on the model its contract declares: never under
   * `modelOverride` or for an injected `llmProvider`. A completion that stops at the limit
   * is reported as an `LLMOutputProcessingError`, not returned cut off.
   */
  maxTokens?: number;
  /** Images for the final user turn, in array order, each before or after its text as its `position` says. */
  attachments?: readonly ImageAttachment[];
  /**
   * How much the model reasons, in the vendor's own terms: OpenAI's `reasoning.effort`,
   * Anthropic's `effort`, Google's `thinkingLevel`. Absent sends nothing and leaves the
   * model at its default, which is not the same as `'none'`. An evaluator sets it only for
   * a step that declares one, and only on the model its contract declares: never under
   * `modelOverride` or for an injected `llmProvider`. Which values each vendor takes is
   * `config.schema.json`'s rule.
   */
  reasoningEffort?: string;
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
 * Optional settings for {@link LLMProvider.generateText}, passed as its third argument.
 *
 * An object rather than another positional parameter, so a later setting is added here
 * without changing the method's signature again. An evaluator passes it only when it has a
 * setting to send, so an implementation that takes two arguments is called as before.
 */
export interface TextGenerationOptions {
  /** As {@link LLMRequest.maxTokens}. */
  maxTokens?: number;
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
   * argument falls back to `ProviderConfig.temperature`. `options` is optional, and an
   * implementation may leave the parameter out entirely.
   */
  generateText(
    messages: Message[],
    temperature?: number | null,
    options?: TextGenerationOptions
  ): Promise<TextGenerationResponse>;
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
