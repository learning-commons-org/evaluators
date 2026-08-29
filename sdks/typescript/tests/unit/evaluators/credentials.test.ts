import { describe, it, expect } from 'vitest';
import { declaredCredentials, configFieldFor } from '../../../src/evaluators/credentials.js';
import { MathStandardsAlignmentEvaluator } from '../../../src/evaluators/index.js';
import MATH_CONFIG from '../../../../../evals/academic-standards-alignment/mathematics/math-standards-alignment/config.json';

describe('declaredCredentials', () => {
  it('collects what the real contract declares', () => {
    expect(declaredCredentials(MATH_CONFIG)).toEqual(['learning_commons_api_key']);
  });

  it('reaches an evaluator through its metadata', () => {
    // How the declaration becomes load-bearing: without this the contract is inert.
    expect(MathStandardsAlignmentEvaluator.metadata.requiredCredentials).toEqual([
      'learning_commons_api_key',
    ]);
  });

  it('returns nothing when a contract declares no non-LLM service', () => {
    expect(declaredCredentials({ steps: [{ id: 'evaluate_x' }] })).toEqual([]);
  });

  it('excludes an optional step', () => {
    // The reason this is declared per entry rather than per evaluator: an optional step
    // runs only when a caller opts in, so requiring its credential up front would
    // demand a key for a call that never happens.
    const credentials = declaredCredentials({
      steps: [
        { id: 'always', required_credentials: ['learning_commons_api_key'] },
        { id: 'opt_in', optional: true, required_credentials: ['some_other_api_key'] },
      ],
    });

    expect(credentials).toEqual(['learning_commons_api_key']);
  });

  it('includes a non-optional step that declares one', () => {
    expect(
      declaredCredentials({ steps: [{ id: 's', required_credentials: ['learning_commons_api_key'] }] }),
    ).toEqual(['learning_commons_api_key']);
  });

  it('reads preprocessing entries as well as steps', () => {
    expect(
      declaredCredentials({
        preprocessing: [{ id: 'fetch', required_credentials: ['learning_commons_api_key'] }],
        steps: [{ id: 's' }],
      }),
    ).toEqual(['learning_commons_api_key']);
  });

  it('reports each credential once, however many entries need it', () => {
    expect(
      declaredCredentials({
        preprocessing: [
          { id: 'a', required_credentials: ['learning_commons_api_key'] },
          { id: 'b', required_credentials: ['learning_commons_api_key'] },
        ],
        steps: [{ id: 's', required_credentials: ['learning_commons_api_key'] }],
      }),
    ).toEqual(['learning_commons_api_key']);
  });
});

describe('configFieldFor', () => {
  // §3.1: rendering a canonical key is §2.1's mechanical casing map, so this is a
  // formula and a provider added later needs no entry anywhere.
  it.each([
    ['openai_api_key', 'openaiApiKey'],
    ['google_api_key', 'googleApiKey'],
    ['anthropic_api_key', 'anthropicApiKey'],
    ['learning_commons_api_key', 'learningCommonsApiKey'],
  ])('%s -> %s', (canonical, field) => {
    expect(configFieldFor(canonical)).toBe(field);
  });

  it('leaves an already-camelCase key alone', () => {
    expect(configFieldFor('googleApiKey')).toBe('googleApiKey');
  });
});
