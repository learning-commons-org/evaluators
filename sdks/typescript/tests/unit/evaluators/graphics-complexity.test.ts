import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import CONFIG from '../../../../../evals/graphics/ela/graphics-complexity/config.json';
import { GraphicsComplexityEvaluator } from '../../../src/evaluators/graphics/ela/graphics-complexity.js';
import { Provider } from '../../../src/evaluators/base.js';
import { ConfigurationError, InputValidationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const STEP = CONFIG.steps[0];
const CONTRACT_DIR = join(process.cwd(), '..', '..', 'evals/graphics/ela/graphics-complexity');
const image = (name: string) => join(CONTRACT_DIR, 'images', name);
const CZERNY = [image('GUT-35601_czerny.png'), image('GUT-35601_czerny_2.png'), image('GUT-35601_czerny_3.png')];
const bytes = (path: string) => new Uint8Array(readFileSync(path));

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

const RETURNED = {
  complexity_score: 'slightly_complex' as const,
  reasoning: 'Three captioned portraits that restate the text.',
  details: { detailed_summary: [], adjustment_and_scaffolding: [], recommended_use_cases: [] },
};

const MOCK_RESPONSE = {
  data: {
    ...RETURNED,
    graphics: [
      { label: 'Image 1', role: 'supporting', demand_notes: 'A portrait.', complexity: 'slightly_complex' },
      { label: 'Image 2', role: 'supporting', demand_notes: 'A portrait.', complexity: 'slightly_complex' },
      { label: 'Image 3', role: 'supporting', demand_notes: 'A portrait.', complexity: 'slightly_complex' },
    ],
    joint_reading: { applies: false, which: [], complexity: null, reasoning: 'Each stands alone.' },
    aggregation_rule: 'highest_individual',
  },
  model: STEP.model.name,
  usage: { inputTokens: 2000, outputTokens: 400 },
  latencyMs: 900,
};

const TEXT = 'His name was Carl Czerny. Here is his picture.';

function setup() {
  const evaluator = new GraphicsComplexityEvaluator({ googleApiKey: 'test-key', telemetry: false });
  // @ts-expect-error accessing private for testing
  const provider: LLMProvider = evaluator.provider;
  vi.mocked(provider.generateStructured).mockResolvedValue(MOCK_RESPONSE);
  const call = () => vi.mocked(provider.generateStructured).mock.calls[0][0];
  return { evaluator, provider, call };
}

describe('GraphicsComplexityEvaluator - Constructor and metadata', () => {
  it('throws when the Google API key is missing', () => {
    expect(() => new GraphicsComplexityEvaluator({ googleApiKey: '' })).toThrow(/Missing required credential: googleApiKey/);
  });

  it('refuses a bring-your-own provider that does not declare attachment support', () => {
    const textOnly: LLMProvider = { label: 'custom:text-only', generateStructured: vi.fn(), generateText: vi.fn() };
    expect(() => new GraphicsComplexityEvaluator({ llmProvider: textOnly, telemetry: false })).toThrow(ConfigurationError);
  });

  it('derives identity, provider, grades and outcome from config.json', () => {
    const { metadata } = GraphicsComplexityEvaluator;
    expect(metadata.id).toBe(CONFIG.evaluator.id);
    expect(metadata.stableId).toBe(CONFIG.evaluator.stable_id);
    expect(metadata.defaultProviders).toEqual([Provider.Google]);
    expect(metadata.supportedGrades).toEqual(CONFIG.evaluator.supported_grades);
    expect(metadata.outcome).toEqual({ score: 'complexity_score', reasoning: 'reasoning' });
  });
});

describe('GraphicsComplexityEvaluator - LLM call contract', () => {
  beforeEach(() => vi.clearAllMocks());

  it('attaches every image after the text, in image_paths order', async () => {
    const { evaluator, call } = setup();
    await evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY });

    expect(call().attachments).toEqual(
      CZERNY.map((path) => ({ type: 'image', data: bytes(path), mediaType: 'image/png', position: 'after_text' })),
    );
    for (const path of CZERNY) expect(call().messages[1].content).not.toContain(path);
  });

  it('renders the text, grade, Flesch-Kincaid score and labels into the user prompt', async () => {
    const { evaluator, call } = setup();
    await evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY, figure_labels: 'Mother,Father ,  Czerny' });

    const user = call().messages[1].content;
    expect(user).toContain(`Text to Evaluate - text: ${TEXT}`);
    expect(user).toContain('It is intended for grade 4');
    expect(user).toMatch(/Flesch–Kincaid grade level: -?\d+(\.\d+)?\n/);
    expect(user).toContain('Graphics in scope: Mother, Father, Czerny');
    expect(user).not.toMatch(/\{\w+\}/);
  });

  it('labels the images "Image 1" to "Image N" when figure_labels is omitted', async () => {
    const { evaluator, call } = setup();
    await evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY });
    expect(call().messages[1].content).toContain('Graphics in scope: Image 1, Image 2, Image 3');
  });

  it('sends the system prompt verbatim and the temperature from config.json', async () => {
    const { evaluator, call } = setup();
    await evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY });
    expect(call().messages[0].content).toBe(readFileSync(join(CONTRACT_DIR, 'system.txt'), 'utf-8'));
    expect(call().temperature).toBe(STEP.generation.temperature);
  });

  it('asks the model for the x-model-only fields and returns without them', async () => {
    const { evaluator, call } = setup();
    const result = await evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY });

    const sent = Object.keys((call().schema as unknown as { shape: object }).shape);
    expect(sent).toEqual(expect.arrayContaining(['graphics', 'joint_reading', 'aggregation_rule']));
    expect(result.result).toEqual(RETURNED);
    expect(result.evaluator).toBe(CONFIG.evaluator.id);
    expect(result.metadata.tokenUsage).toEqual({ inputTokens: 2000, outputTokens: 400 });
  });
});

describe('GraphicsComplexityEvaluator - input validation', () => {
  beforeEach(() => vi.clearAllMocks());

  it.each([
    ['too few', 'Mother, Father', /received 2 for 3 images/],
    ['too many', 'A, B, C, D', /received 4 for 3 images/],
    ['a blank one', 'A, , C', /one distinct, non-empty label per image/],
    ['a repeat', 'A, B, A', /one distinct, non-empty label per image/],
  ])('rejects figure_labels with %s before any model call', async (_, figure_labels, message) => {
    const { evaluator, provider } = setup();
    await expect(evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY, figure_labels })).rejects.toThrow(
      message,
    );
    expect(provider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects whitespace-only figure_labels as it would any blank string input', async () => {
    const { evaluator } = setup();
    await expect(evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: CZERNY, figure_labels: '  ' })).rejects.toThrow(
      /figure_labels cannot be empty/,
    );
  });

  it('accepts at most five images and at least one, by the contract’s minItems/maxItems', async () => {
    const { evaluator, provider } = setup();
    const six = [...CZERNY, ...CZERNY];
    await expect(evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: six })).rejects.toThrow(/at most 5 items; received 6/);
    await expect(evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: [] })).rejects.toThrow(/at least 1 item; received 0/);
    expect(provider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a grade outside 3–12', async () => {
    const { evaluator } = setup();
    await expect(evaluator.evaluate({ text: TEXT, grade_level: '2' as never, image_paths: CZERNY })).rejects.toThrow(InputValidationError);
  });

  it('names the image that cannot be read, by its position, before any model call', async () => {
    const { evaluator, provider } = setup();
    await expect(
      evaluator.evaluate({ text: TEXT, grade_level: '4', image_paths: [CZERNY[0], join(CONTRACT_DIR, 'system.txt')] }),
    ).rejects.toThrow(/image_paths\[1\]: .* is not an accepted image/);
    expect(provider.generateStructured).not.toHaveBeenCalled();
  });
});
