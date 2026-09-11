import { describe, it, expect } from 'vitest';
import { createPromptRenderers } from '../../../src/prompts/create-prompts.js';

const KEYS = ['text', 'grade_level'];

describe('createPromptRenderers', () => {
  it('substitutes only the placeholders it was given', () => {
    const { getUserPrompt } = createPromptRenderers(
      'system',
      'Read {text} for grade {grade_level}. Leave {undeclared} alone.',
      KEYS,
    );

    expect(getUserPrompt({ text: 'a passage', grade_level: '5', undeclared: 'nope' })).toBe(
      'Read a passage for grade 5. Leave {undeclared} alone.',
    );
  });

  it('leaves a declared placeholder intact when no input is provided', () => {
    const { getSystemPrompt } = createPromptRenderers('Grade: {grade_level}', 'user', KEYS);

    expect(getSystemPrompt({})).toBe('Grade: {grade_level}');
  });

  it('replaces every occurrence of a placeholder', () => {
    const { getUserPrompt } = createPromptRenderers('system', '{text} and {text}', KEYS);

    expect(getUserPrompt({ text: 'x' })).toBe('x and x');
  });

  it('substitutes nothing when no placeholders are declared', () => {
    const { getUserPrompt } = createPromptRenderers('system', 'Read {text}.', []);

    expect(getUserPrompt({ text: 'a passage' })).toBe('Read {text}.');
  });
});
