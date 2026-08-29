import { InputValidationError } from '../errors.js';

/**
 * Validating a caller's inputs against the schema the evaluator declares.
 *
 * Each evaluator's `input_schema.json` is the only description of what it accepts, so
 * the bounds, the accepted grades and the set of field names all come from there. A
 * global default applied to every evaluator would silently ignore a contract asking for
 * something narrower, which §4.1 forbids.
 */

/** The shape of an `input_schema.json`, as much of it as validation reads. */
export interface DeclaredInputSchema {
  properties: Record<
    string,
    { type?: string; minLength?: number; maxLength?: number; enum?: string[] }
  >;
  required?: string[];
}

/**
 * The inputs an evaluator accepts, derived from its declared schema.
 *
 * Keys come from the schema, so adding an input to a contract is a compile error in
 * every call site that does not pass it. Values are `string` because TypeScript widens
 * imported JSON string literals — the declared `enum` and bounds are enforced at
 * runtime by {@link validateInputs}, which is the authoritative check either way.
 */
export type InputsOf<S extends { properties: object }> = Record<keyof S['properties'], string>;

/**
 * Check `inputs` against `schema`, in the order §4.1 fixes.
 *
 * Fields are visited in declared order — `required` first, then any remaining
 * properties — so a caller passing two bad inputs always gets the same message, in
 * this SDK and in any other reading the same schema.
 *
 * @throws {InputValidationError} On an unknown key, a missing field, a whitespace-only
 * or out-of-bounds string, or a value outside a declared `enum`.
 */
export function validateInputs(
  inputs: Record<string, unknown>,
  schema: DeclaredInputSchema,
): void {
  // A JS caller, or an `any`, can hand over something that is not an object at all.
  // Reaching Object.keys with it would raise a TypeError, which is neither diagnosable
  // nor part of the taxonomy.
  if (inputs === null || typeof inputs !== 'object' || Array.isArray(inputs)) {
    throw new InputValidationError(
      `Expected an object of inputs, received ${inputs === null ? 'null' : typeof inputs}.`,
    );
  }

  const declared = Object.keys(schema.properties);

  // Contracts declare `additionalProperties: false`, so an unexpected key is a caller
  // mistake worth naming rather than something to quietly drop.
  for (const key of Object.keys(inputs)) {
    if (!declared.includes(key)) {
      throw new InputValidationError(
        `Unknown input "${key}". This evaluator accepts: ${declared.join(', ')}.`,
      );
    }
  }

  const required = schema.required ?? [];
  const order = [...required, ...declared.filter((f) => !required.includes(f))];

  for (const field of order) {
    const spec = schema.properties[field];
    const value = inputs[field];

    if (value === undefined || value === null) {
      if (required.includes(field)) {
        throw new InputValidationError(`${field} is required.`);
      }
      continue;
    }

    if (spec.type === 'string' && typeof value !== 'string') {
      throw new InputValidationError(`${field} must be a string.`);
    }

    if (typeof value === 'string') {
      validateStringField(field, value, spec);
    }
  }
}

function validateStringField(
  field: string,
  value: string,
  spec: { minLength?: number; maxLength?: number; enum?: string[] },
): void {
  if (spec.enum) {
    if (!spec.enum.includes(value)) {
      throw new InputValidationError(
        `Invalid ${field} "${value}". Accepted values: ${spec.enum.join(', ')}.`,
      );
    }
    return;
  }

  // Trimming decides whether the value is blank and nothing more: the bounds below
  // measure the string as the caller sent it, which is also what reaches the model.
  if (!value.trim()) {
    throw new InputValidationError(`${field} cannot be empty or contain only whitespace`);
  }

  if (spec.minLength !== undefined && value.length < spec.minLength) {
    throw new InputValidationError(
      `${field} is too short. Minimum length is ${spec.minLength} characters.`,
    );
  }

  if (spec.maxLength !== undefined && value.length > spec.maxLength) {
    throw new InputValidationError(
      `${field} is too long. Maximum length is ${spec.maxLength} characters.`,
    );
  }
}

/**
 * The field a report or telemetry treats as the primary text.
 *
 * The wire still carries one text length, so an evaluator with two texts has to pick
 * one: the first declared string input that is not an enum. Interim — Q-10 replaces the
 * single length with a per-input map.
 */
export function primaryTextField(schema: DeclaredInputSchema): string | undefined {
  return Object.keys(schema.properties).find((field) => {
    const spec = schema.properties[field];
    return spec.type === 'string' && !spec.enum;
  });
}
