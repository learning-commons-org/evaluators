import { describe, it, expect } from 'vitest';
import {
  getSystemPrompt,
  getUserPrompt,
} from '../../../src/prompts/vocabulary-complexity/index.js';

/**
 * vocabulary-complexity declares two mutually exclusive branches on grade, and a
 * `flesch_kincaid_grade` preprocessing entry conditioned on the grades-3-4 one. Which
 * branch a grade takes, and whether its prompt binds `{fk_score}`, are facts stated in
 * `config.json` — these pin that the prompt layer reads them rather than restating them.
 */

const TEXT = 'Great whirling storms roar out of the oceans in many parts of the world.';
const BACKGROUND = 'Students know that storms bring wind and rain.';

describe('the branch follows the contract, not a hardcoded grade list', () => {
  it('gives grades 3-4 a different system prompt from grades 5-12', () => {
    // A single hardcoded branch — or a wrong one — collapses these to the same text.
    expect(getSystemPrompt('3')).toBe(getSystemPrompt('4'));
    expect(getSystemPrompt('7')).toBe(getSystemPrompt('12'));
    expect(getSystemPrompt('3')).not.toBe(getSystemPrompt('7'));
  });

  it('gives grades 3-4 a different user template from grades 5-12', () => {
    const younger = getUserPrompt(TEXT, '3', BACKGROUND, 4.2);
    const older = getUserPrompt(TEXT, '7', BACKGROUND);

    expect(younger).not.toBe(older);
  });
});

describe('{fk_score} is bound only where the contract declares it', () => {
  it('substitutes the score into the grades-3-4 prompt', () => {
    const prompt = getUserPrompt(TEXT, '3', BACKGROUND, 4.2);

    expect(prompt).toContain('4.2');
    expect(prompt).not.toContain('{fk_score}');
  });

  it('renders the grades 5-12 prompt identically with or without a score', () => {
    // The other-grades template declares no {fk_score}, so a score passed to it must make
    // no difference — if it ever did, something is substituting a value the contract did
    // not declare for that branch.
    expect(getUserPrompt(TEXT, '7', BACKGROUND)).toBe(getUserPrompt(TEXT, '7', BACKGROUND, 9.9));
  });

  it('never leaks the string "undefined" into a prompt that binds the score', () => {
    // Grade 3 binds it, so an absent score must not stringify. The evaluator cannot reach
    // this combination, which is exactly why the guard needs its own test.
    const prompt = getUserPrompt(TEXT, '3', BACKGROUND, undefined);

    expect(prompt).not.toContain('undefined');
  });
});
