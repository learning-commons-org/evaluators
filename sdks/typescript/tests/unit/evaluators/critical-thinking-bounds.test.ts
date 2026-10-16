/**
 * Critical Thinking refuses an input outside the bounds its schema declares,
 * before any model call.
 */
import { describe, expect, it } from 'vitest';
import { CriticalThinkingEvaluator } from '../../../src/evaluators/durable-skills/ela-writing/critical-thinking.js';
import { InputValidationError } from '../../../src/errors.js';
import type { CriticalThinkingInput } from '../../../src/schemas/durable-skills/ela-writing/critical-thinking.js';

const ASSIGNMENT = 'Using the sources, argue whether the town should limit cars downtown.';
const ESSAY =
  'Dear city council, the article says the face is a mesa. The student names that ' +
  'source and restates its claim, then stops. No other evidence is weighed, and the ' +
  'essay does not answer whether the town should limit cars downtown.';
const PASSAGE = 'The face is a mesa, according to the article the student was given.';

function input(overrides: Partial<CriticalThinkingInput>): CriticalThinkingInput {
  return {
    assignment_text: ASSIGNMENT,
    source_passages: [{ text: PASSAGE }],
    essay_text: ESSAY,
    ...overrides,
  };
}

const evaluator = new CriticalThinkingEvaluator({
  anthropicApiKey: 'k',
  telemetry: false,
});

describe('Critical Thinking input bounds', () => {
  it.each([
    ['a'.repeat(199), 'essay_text', 'essay_text is too short. Minimum length is 200 characters.'],
    ['a'.repeat(12001), 'essay_text', 'essay_text is too long. Maximum length is 12000 characters.'],
    ['a'.repeat(19), 'assignment_text', 'assignment_text is too short. Minimum length is 20 characters.'],
    ['a'.repeat(3001), 'assignment_text', 'assignment_text is too long. Maximum length is 3000 characters.'],
  ] as const)('rejects %s on %s', async (value, field, message) => {
    await expect(evaluator.evaluate(input({ [field]: value }))).rejects.toThrow(message);
    await expect(evaluator.evaluate(input({ [field]: value }))).rejects.toBeInstanceOf(
      InputValidationError,
    );
  });

  it('rejects a passage text outside 50 to 9000 characters', async () => {
    await expect(
      evaluator.evaluate(input({ source_passages: [{ text: 'a'.repeat(49) }] })),
    ).rejects.toThrow('source_passages[0].text is too short. Minimum length is 50 characters.');
    await expect(
      evaluator.evaluate(input({ source_passages: [{ text: 'a'.repeat(9001) }] })),
    ).rejects.toThrow('source_passages[0].text is too long. Maximum length is 9000 characters.');
  });

  it('rejects a title over 300 characters and an author over 200', async () => {
    await expect(
      evaluator.evaluate(input({ source_passages: [{ title: 't'.repeat(301), text: PASSAGE }] })),
    ).rejects.toThrow('source_passages[0].title is too long. Maximum length is 300 characters.');
    await expect(
      evaluator.evaluate(input({ source_passages: [{ author: 'a'.repeat(201), text: PASSAGE }] })),
    ).rejects.toThrow('source_passages[0].author is too long. Maximum length is 200 characters.');
  });

  it('rejects more than five passages', async () => {
    await expect(
      evaluator.evaluate(input({ source_passages: Array.from({ length: 6 }, () => ({ text: PASSAGE })) })),
    ).rejects.toThrow('source_passages accepts at most 5 items; received 6.');
  });
});
