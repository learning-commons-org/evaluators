import { describe, it, expect } from 'vitest';
import {
  validateInputs,
  primaryTextField,
  type DeclaredInputSchema,
} from '../../../src/evaluators/inputs.js';
import { InputValidationError } from '../../../src/errors.js';

/** Two text inputs and a closed enum — between them these cover every branch. */
const SCHEMA: DeclaredInputSchema = {
  properties: {
    text: { type: 'string', minLength: 10, maxLength: 40 },
    grade_level: { type: 'string', enum: ['3', '4', '5'] },
    note: { type: 'string', minLength: 1, maxLength: 20 },
  },
  required: ['text', 'grade_level'],
};

const valid = { text: 'a'.repeat(12), grade_level: '4' };

describe('validateInputs — accepted', () => {
  it('accepts exactly the required inputs', () => {
    expect(() => validateInputs(valid, SCHEMA)).not.toThrow();
  });

  it('accepts an optional input when supplied', () => {
    expect(() => validateInputs({ ...valid, note: 'fine' }, SCHEMA)).not.toThrow();
  });

  it('accepts an absent optional input', () => {
    expect(() => validateInputs(valid, SCHEMA)).not.toThrow();
  });

  it('accepts the bounds themselves, not just inside them', () => {
    expect(() => validateInputs({ ...valid, text: 'a'.repeat(10) }, SCHEMA)).not.toThrow();
    expect(() => validateInputs({ ...valid, text: 'a'.repeat(40) }, SCHEMA)).not.toThrow();
  });

  it('accepts a schema that declares no required list', () => {
    expect(() => validateInputs({ text: 'a'.repeat(12) }, { properties: SCHEMA.properties })).not.toThrow();
  });
});

describe('validateInputs — rejected', () => {
  it('rejects an unknown key and names what is accepted', () => {
    expect(() => validateInputs({ ...valid, nope: 'x' }, SCHEMA)).toThrow(
      'Unknown input "nope". This evaluator accepts: text, grade_level, note.',
    );
  });

  it('rejects a missing required input', () => {
    expect(() => validateInputs({ grade_level: '4' }, SCHEMA)).toThrow('text is required.');
  });

  it('treats an explicit null as absent', () => {
    expect(() => validateInputs({ ...valid, text: null }, SCHEMA)).toThrow('text is required.');
  });

  it('rejects a non-string where a string is declared', () => {
    expect(() => validateInputs({ ...valid, text: 42 }, SCHEMA)).toThrow('text must be a string.');
  });

  it.each(['   ', '\n\t', ''])('rejects blank text (%j)', (blank) => {
    expect(() => validateInputs({ ...valid, text: blank }, SCHEMA)).toThrow(
      'text cannot be empty or contain only whitespace',
    );
  });

  it('rejects text under the declared minimum', () => {
    expect(() => validateInputs({ ...valid, text: 'a'.repeat(9) }, SCHEMA)).toThrow(
      'text is too short. Minimum length is 10 characters.',
    );
  });

  it('rejects text over the declared maximum', () => {
    expect(() => validateInputs({ ...valid, text: 'a'.repeat(41) }, SCHEMA)).toThrow(
      'text is too long. Maximum length is 40 characters.',
    );
  });

  it('rejects a value outside a declared enum and lists the accepted ones', () => {
    expect(() => validateInputs({ ...valid, grade_level: '9' }, SCHEMA)).toThrow(
      'Invalid grade_level "9". Accepted values: 3, 4, 5.',
    );
  });

  it('throws InputValidationError, not a bare Error', () => {
    expect(() => validateInputs({}, SCHEMA)).toThrow(InputValidationError);
  });
});

describe('validateInputs — order is fixed', () => {
  // Two bad inputs must always yield the same message, here and in any other SDK
  // reading the same schema, or the two disagree about what the caller did wrong.
  it('reports a required field before an optional one', () => {
    expect(() =>
      validateInputs({ text: 'short', grade_level: '4', note: '' }, SCHEMA),
    ).toThrow(/^text is too short/);
  });

  it('reports required fields in declared order', () => {
    expect(() => validateInputs({ text: 'short', grade_level: '9' }, SCHEMA)).toThrow(
      /^text is too short/,
    );
  });

  it('still validates an optional field when the required ones are fine', () => {
    // Guards the field ordering: optional fields are appended after required ones, and
    // an ordering that dropped them would accept invalid input silently.
    expect(() => validateInputs({ ...valid, note: 'a'.repeat(21) }, SCHEMA)).toThrow(
      'note is too long. Maximum length is 20 characters.',
    );
  });

  it('does not bound-check an enum field', () => {
    // An enum is a closed set; length has no meaning for it.
    const enumOnly: DeclaredInputSchema = {
      properties: { grade_level: { type: 'string', enum: ['3'], minLength: 99 } },
      required: ['grade_level'],
    };

    expect(() => validateInputs({ grade_level: '3' }, enumOnly)).not.toThrow();
  });
});

describe('primaryTextField', () => {
  it('picks the first declared string that is not an enum', () => {
    expect(primaryTextField(SCHEMA)).toBe('text');
  });

  it('skips an enum declared first', () => {
    expect(
      primaryTextField({
        properties: {
          grade_level: { type: 'string', enum: ['3'] },
          student_text: { type: 'string', maxLength: 10 },
        },
      }),
    ).toBe('student_text');
  });

  it('returns undefined when nothing qualifies', () => {
    expect(primaryTextField({ properties: { n: { type: 'integer' } } })).toBeUndefined();
  });
});
