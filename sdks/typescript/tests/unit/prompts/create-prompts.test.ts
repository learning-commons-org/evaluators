import { describe, it, expect } from 'vitest';
import { createPromptRenderers } from '../../../src/prompts/create-prompts.js';

const CONFIG = {
  evaluator: { id: 'literacy.gla.example' },
  steps: [
    {
      id: 'evaluate_example',
      prompt: { placeholders: { text: {}, grade_level: {} } },
    },
  ],
};

describe('createPromptRenderers', () => {
  it('substitutes only placeholders declared in the config', () => {
    const { getUserPrompt } = createPromptRenderers(
      'system',
      'Read {text} for grade {grade_level}. Leave {undeclared} alone.',
      CONFIG,
    );
    expect(getUserPrompt({ text: 'a passage', grade_level: '5', undeclared: 'nope' }))
      .toBe('Read a passage for grade 5. Leave {undeclared} alone.');
  });

  it('leaves declared placeholders intact when no input is provided', () => {
    const { getSystemPrompt } = createPromptRenderers('Grade: {grade_level}', 'user', CONFIG);
    expect(getSystemPrompt({})).toBe('Grade: {grade_level}');
  });

  it('replaces repeated occurrences of a placeholder', () => {
    const { getUserPrompt } = createPromptRenderers('system', '{text} and {text}', CONFIG);
    expect(getUserPrompt({ text: 'x' })).toBe('x and x');
  });

  it('throws when the conventional evaluate_{slug} step is missing', () => {
    const badConfig = {
      evaluator: { id: 'literacy.gla.example' },
      steps: [{ id: 'evaluate_other', prompt: { placeholders: {} } }],
    };
    expect(() => createPromptRenderers('system', 'user', badConfig)).toThrow(
      'Step "evaluate_example" not found in literacy.gla.example config.json',
    );
  });
});
