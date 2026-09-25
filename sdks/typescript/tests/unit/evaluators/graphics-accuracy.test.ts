import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import CONFIG from '../../../../../evals/academic-standards-alignment/mathematics/graphics-accuracy/config.json';
import {
  GraphicsAccuracyEvaluator,
  composeSpecification,
} from '../../../src/evaluators/academic-standards-alignment/mathematics/graphics-accuracy.js';
import { Provider } from '../../../src/evaluators/base.js';
import { ConfigurationError, InputValidationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const STEP = CONFIG.steps[0];
const CONTRACT_DIR = join(process.cwd(), '..', '..', 'evals/academic-standards-alignment/mathematics/graphics-accuracy');
const LADYBIRDS = join(CONTRACT_DIR, 'images/ladybirds.png');
const LADYBIRDS_BYTES = new Uint8Array(readFileSync(LADYBIRDS));

const createMockProvider = (config?: { type?: string; model?: string }): LLMProvider => ({
  label: config?.type && config?.model ? `${config.type}:${config.model}` : 'mock:model',
  supportsAttachments: true,
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    createProvider: vi.fn((config) => createMockProvider(config)),
  };
});

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

const MOCK_RESPONSE = {
  data: {
    observed: 'Five ladybirds with 2, 3, 3, 5 and 6 dots.',
    analysis: '2 + 3 + 3 + 5 + 6 = 19. The image yields 19; the specification states 19; therefore is_correct = true.',
    errors: [] as string[],
    correction: '19',
    basis: 'supported' as const,
    is_correct: true,
  },
  model: STEP.model.name,
  usage: { inputTokens: 900, outputTokens: 150 },
  latencyMs: 700,
};

const QUESTION = 'How many dots do all ladybirds have together?';

describe('GraphicsAccuracyEvaluator - Constructor', () => {
  it('throws when the Google API key is missing', () => {
    expect(() => new GraphicsAccuracyEvaluator({ googleApiKey: '' })).toThrow(
      /Missing required credential: googleApiKey/,
    );
  });

  it('refuses a bring-your-own provider that does not declare attachment support', () => {
    const textOnly: LLMProvider = { label: 'custom:text-only', generateStructured: vi.fn(), generateText: vi.fn() };
    expect(() => new GraphicsAccuracyEvaluator({ llmProvider: textOnly, telemetry: false })).toThrow(ConfigurationError);
    expect(() => new GraphicsAccuracyEvaluator({ llmProvider: textOnly, telemetry: false })).toThrow(
      /does not declare support for attachments/,
    );
  });

  it('accepts a bring-your-own provider that declares attachment support', () => {
    const withImages: LLMProvider = { label: 'custom:vision', supportsAttachments: true, generateStructured: vi.fn(), generateText: vi.fn() };
    expect(() => new GraphicsAccuracyEvaluator({ llmProvider: withImages, telemetry: false })).not.toThrow();
  });
});

describe('GraphicsAccuracyEvaluator - Metadata', () => {
  it('derives identity from config.json', () => {
    expect(GraphicsAccuracyEvaluator.metadata.id).toBe(CONFIG.evaluator.id);
    expect(GraphicsAccuracyEvaluator.metadata.stableId).toBe(CONFIG.evaluator.stable_id);
    expect(GraphicsAccuracyEvaluator.metadata.name).toBe(CONFIG.evaluator.name);
    expect(GraphicsAccuracyEvaluator.metadata.description).toBe(CONFIG.evaluator.description);
  });

  it('is Google-only, as the contract declares', () => {
    expect(GraphicsAccuracyEvaluator.metadata.defaultProviders).toEqual([Provider.Google]);
  });

  it('declares K–12', () => {
    expect(GraphicsAccuracyEvaluator.metadata.supportedGrades).toEqual(CONFIG.evaluator.supported_grades);
  });

  it('names is_correct as the score and analysis as the reasoning', () => {
    expect(GraphicsAccuracyEvaluator.metadata.outcome).toEqual({ score: 'is_correct', reasoning: 'analysis' });
  });
});

describe('composeSpecification', () => {
  it('produces the benchmarked claim text and trims its parts', () => {
    expect(composeSpecification(` ${QUESTION} `, ' 19 ')).toBe(`Question: "${QUESTION}" The answer is 19.`);
  });
});

describe('GraphicsAccuracyEvaluator - LLM call contract', () => {
  let evaluator: GraphicsAccuracyEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    evaluator = new GraphicsAccuracyEvaluator({ googleApiKey: 'test-key', telemetry: false });
    // @ts-expect-error accessing private for testing
    mockProvider = evaluator.provider;
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);
  });

  afterEach(() => vi.restoreAllMocks());

  it('sends the image bytes as a request attachment and the rendered claim as the user text', async () => {
    await evaluator.evaluate({ image: LADYBIRDS, claim: composeSpecification(QUESTION, '19') });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.messages).toHaveLength(2);
    expect(call.messages[0].role).toBe('system');
    expect(call.messages[1].role).toBe('user');
    expect(call.messages[1].content).toContain(`Question: "${QUESTION}" The answer is 19.`);
    expect(call.messages[1].content).not.toContain('{claim}');
    // The path is an input, not prompt text; it must never reach the model.
    expect(call.messages[1].content).not.toContain(LADYBIRDS);
    expect(call.attachments).toEqual([{ type: 'image', data: LADYBIRDS_BYTES, mediaType: 'image/png' }]);
  });

  it('sends the system prompt verbatim from the contract', async () => {
    await evaluator.evaluate({ image: LADYBIRDS, claim: 'The chart shows 12 apples.' });
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.messages[0].content).toBe(readFileSync(join(CONTRACT_DIR, 'system.txt'), 'utf-8'));
  });

  it('passes the temperature from config.json', async () => {
    await evaluator.evaluate({ image: LADYBIRDS, claim: 'The chart shows 12 apples.' });
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.temperature).toBe(STEP.generation.temperature);
  });

  it('maps the response onto the envelope', async () => {
    const result = await evaluator.evaluate({ image: LADYBIRDS, claim: composeSpecification(QUESTION, '19') });
    expect(result.evaluator).toBe(CONFIG.evaluator.id);
    expect(result.result).toEqual(MOCK_RESPONSE.data);
    expect(result.result.basis).toBe('supported');
    expect(result.metadata.model).toBe(`${STEP.model.provider}:${STEP.model.name}`);
    expect(result.metadata.tokenUsage).toEqual({ inputTokens: 900, outputTokens: 150 });
  });

  it('loads the image from an http(s) URL', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(LADYBIRDS_BYTES, { status: 200 }));
    await evaluator.evaluate({ image: 'https://example.org/ladybirds.png', claim: 'Five ladybirds.' });
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.attachments).toEqual([{ type: 'image', data: LADYBIRDS_BYTES, mediaType: 'image/png' }]);
  });
});

describe('GraphicsAccuracyEvaluator - input validation', () => {
  let evaluator: GraphicsAccuracyEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    evaluator = new GraphicsAccuracyEvaluator({ googleApiKey: 'test-key', telemetry: false });
    // @ts-expect-error accessing private for testing
    mockProvider = evaluator.provider;
  });

  it('rejects a missing claim before any model call', async () => {
    await expect(evaluator.evaluate({ image: LADYBIRDS } as never)).rejects.toThrow(InputValidationError);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a whitespace-only claim', async () => {
    await expect(evaluator.evaluate({ image: LADYBIRDS, claim: '   ' })).rejects.toThrow(/cannot be empty/);
  });

  it('rejects a whitespace-only image source before trying to read it', async () => {
    await expect(evaluator.evaluate({ image: '   ', claim: 'x' })).rejects.toThrow(/image cannot be empty/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects an unknown input, so the old question + answer shape fails loudly', async () => {
    await expect(
      evaluator.evaluate({ image: LADYBIRDS, question: QUESTION, answer: '19' } as never),
    ).rejects.toThrow(/Unknown input "question"/);
  });

  it('rejects an image path that does not exist, before any model call', async () => {
    await expect(
      evaluator.evaluate({ image: join(CONTRACT_DIR, 'images/nope.png'), claim: 'x' }),
    ).rejects.toThrow(/could not read file/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a file that is not an image', async () => {
    await expect(
      evaluator.evaluate({ image: join(CONTRACT_DIR, 'system.txt'), claim: 'x' }),
    ).rejects.toThrow(/not a PNG, JPEG or WEBP/);
  });
});
