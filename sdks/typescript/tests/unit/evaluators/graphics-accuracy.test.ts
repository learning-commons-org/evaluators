import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import CONFIG from '../../../../../evals/graphics/math/graphics-accuracy/config.json';
import INPUT_SCHEMA from '../../../../../evals/graphics/math/graphics-accuracy/input_schema.json';
import {
  GraphicsAccuracyEvaluator,
  composeGraphicsAccuracyClaim,
} from '../../../src/evaluators/graphics/math/graphics-accuracy.js';
import { Provider } from '../../../src/evaluators/base.js';
import { ConfigurationError, InputValidationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const STEP = CONFIG.steps[0];
const CONTRACT_DIR = join(process.cwd(), '..', '..', 'evals/graphics/math/graphics-accuracy');
const APPLES = join(CONTRACT_DIR, 'images/apples-in-baskets.png');
const APPLES_BYTES = new Uint8Array(readFileSync(APPLES));

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
    observed: 'Three baskets holding 4, 5 and 3 apples.',
    defects: [] as string[],
    reasoning: '4 + 5 + 3 = 12. The image yields 12; the specification states 12; therefore is_correct = true.',
    errors: [] as string[],
    correction: '12',
    basis: 'supported' as const,
    is_correct: true,
  },
  model: STEP.model.name,
  usage: { inputTokens: 900, outputTokens: 150 },
  latencyMs: 700,
};

const QUESTION = 'How many apples are in the three baskets altogether?';

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

  it('names is_correct as the score and reasoning as the reasoning', () => {
    expect(GraphicsAccuracyEvaluator.metadata.outcome).toEqual({ score: 'is_correct', reasoning: 'reasoning' });
  });
});

describe('composeGraphicsAccuracyClaim', () => {
  it('produces the measured claim text and trims its parts', () => {
    expect(composeGraphicsAccuracyClaim(` ${QUESTION} `, ' 12 ')).toBe(`Question: "${QUESTION}" The answer is 12.`);
  });

  it('matches the form the contract documents for the claim input', () => {
    // The contract's `claim` description is the canonical statement of the format; the helper
    // must not drift from it, or callers following the docs and callers using the helper would
    // send different text.
    const documented = INPUT_SCHEMA.properties.claim.description.match(/`(Question: "<question>" The answer is <answer>\.)`/);
    expect(documented, 'claim description names the question + answer form').not.toBeNull();
    const expected = documented![1].replace('<question>', QUESTION).replace('<answer>', '12');
    expect(composeGraphicsAccuracyClaim(QUESTION, '12')).toBe(expected);
  });

  it('refuses a blank question or answer, which would otherwise be judged as a wrong image', () => {
    expect(() => composeGraphicsAccuracyClaim(QUESTION, '')).toThrow(InputValidationError);
    expect(() => composeGraphicsAccuracyClaim(QUESTION, '  ')).toThrow(/the answer is blank/);
    expect(() => composeGraphicsAccuracyClaim('', '12')).toThrow(/the question is blank/);
    expect(() => composeGraphicsAccuracyClaim(' \n ', ' ')).toThrow(/the question is blank/);
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
    await evaluator.evaluate({ image_paths: [APPLES], claim: composeGraphicsAccuracyClaim(QUESTION, '12') });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.messages).toHaveLength(2);
    expect(call.messages[0].role).toBe('system');
    expect(call.messages[1].role).toBe('user');
    expect(call.messages[1].content).toContain(`Question: "${QUESTION}" The answer is 12.`);
    expect(call.messages[1].content).not.toContain('{claim}');
    // The path is an input, not prompt text; it must never reach the model.
    expect(call.messages[1].content).not.toContain(APPLES);
    expect(call.attachments).toEqual([{ type: 'image', data: APPLES_BYTES, mediaType: 'image/png' }]);
  });

  it('sends the system prompt verbatim from the contract', async () => {
    await evaluator.evaluate({ image_paths: [APPLES], claim: 'The chart shows 12 apples.' });
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.messages[0].content).toBe(readFileSync(join(CONTRACT_DIR, 'system.txt'), 'utf-8'));
  });

  it('passes the temperature from config.json', async () => {
    await evaluator.evaluate({ image_paths: [APPLES], claim: 'The chart shows 12 apples.' });
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.temperature).toBe(STEP.generation.temperature);
  });

  it('maps the response onto the envelope', async () => {
    const result = await evaluator.evaluate({ image_paths: [APPLES], claim: composeGraphicsAccuracyClaim(QUESTION, '12') });
    expect(result.evaluator).toBe(CONFIG.evaluator.id);
    expect(result.result).toEqual(MOCK_RESPONSE.data);
    expect(result.result.basis).toBe('supported');
    expect(result.metadata.model).toBe(`${STEP.model.provider}:${STEP.model.name}`);
    expect(result.metadata.tokenUsage).toEqual({ inputTokens: 900, outputTokens: 150 });
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
    await expect(evaluator.evaluate({ image_paths: [APPLES] } as never)).rejects.toThrow(InputValidationError);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a whitespace-only claim', async () => {
    await expect(evaluator.evaluate({ image_paths: [APPLES], claim: '   ' })).rejects.toThrow(/cannot be empty/);
  });

  it('rejects a single path passed as a string instead of an array', async () => {
    await expect(evaluator.evaluate({ image_paths: APPLES, claim: 'x' } as never)).rejects.toThrow(
      /image_paths must be an array/,
    );
  });

  it('rejects no images and more than one image, by the contract’s minItems/maxItems', async () => {
    await expect(evaluator.evaluate({ image_paths: [], claim: 'x' })).rejects.toThrow(/at least 1 item; received 0/);
    await expect(evaluator.evaluate({ image_paths: [APPLES, APPLES], claim: 'x' })).rejects.toThrow(
      /at most 1 item; received 2/,
    );
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a whitespace-only path before trying to read it', async () => {
    await expect(evaluator.evaluate({ image_paths: ['   '], claim: 'x' })).rejects.toThrow(/image_paths\[0\] cannot be empty/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects an unknown input, so the old single-path shape fails loudly', async () => {
    await expect(evaluator.evaluate({ image: APPLES, claim: 'x' } as never)).rejects.toThrow(/Unknown input "image"/);
  });

  it('rejects an image path that does not exist, before any model call', async () => {
    await expect(
      evaluator.evaluate({ image_paths: [join(CONTRACT_DIR, 'images/nope.png')], claim: 'x' }),
    ).rejects.toThrow(/image_paths\[0\]: could not read file/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a file that is not an image', async () => {
    await expect(
      evaluator.evaluate({ image_paths: [join(CONTRACT_DIR, 'system.txt')], claim: 'x' }),
    ).rejects.toThrow(/not an accepted image/);
  });

  it('enforces the contract’s x-image edge bound before any model call', async () => {
    const tooWide = join(process.cwd(), 'tests/fixtures/images/2677x1605.png');
    await expect(evaluator.evaluate({ image_paths: [tooWide], claim: 'x' })).rejects.toThrow(/2677×1605 px/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });
});
