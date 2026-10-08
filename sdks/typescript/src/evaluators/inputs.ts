import { InputValidationError } from '../errors.js';

/**
 * Validating a caller's inputs against the schema the evaluator declares.
 *
 * Each evaluator's `input_schema.json` is the only description of what it accepts, so
 * the bounds, the accepted grades and the set of field names all come from there. A
 * global default applied to every evaluator would silently ignore a contract asking for
 * something narrower, which §4.1 forbids.
 */

/** One schema node, as much of it as validation reads. `$ref` points at a `$defs` entry. */
export interface DeclaredFieldSchema {
  type?: string;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
  enum?: string[];
  $ref?: string;
  additionalProperties?: boolean;
  required?: string[];
  properties?: Record<string, DeclaredFieldSchema>;
  items?: DeclaredFieldSchema;
  /** An attached item's bounds, read by the image loader rather than by validation. */
  'x-image'?: unknown;
}

/** The shape of an `input_schema.json`, as much of it as validation reads. */
export interface DeclaredInputSchema {
  properties: Record<string, DeclaredFieldSchema>;
  required?: string[];
  $defs?: Record<string, DeclaredFieldSchema>;
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
 * or out-of-bounds string, a non-integer or out-of-bounds integer, a value outside a
 * declared `enum`, or an array input with a count outside `minItems`/`maxItems` or an
 * item that fails its own declaration.
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

    if (spec.type === 'array') {
      validateArrayField(field, value, spec, schema.$defs ?? {});
      continue;
    }

    if (spec.type === 'string' && typeof value !== 'string') {
      throw new InputValidationError(`${field} must be a string.`);
    }

    if (spec.type === 'integer') {
      validateIntegerField(field, value, spec);
      continue;
    }

    if (typeof value === 'string') {
      validateStringField(field, value, spec);
    }
  }
}

function resolveField(
  spec: DeclaredFieldSchema,
  defs: Record<string, DeclaredFieldSchema>,
): DeclaredFieldSchema {
  if (!spec.$ref) return spec;
  const key = spec.$ref.replace('#/$defs/', '');
  const def = defs[key];
  if (!def) {
    throw new InputValidationError(`Cannot resolve $ref "${spec.$ref}".`);
  }
  return def;
}

function validateIntegerField(field: string, value: unknown, spec: DeclaredFieldSchema): void {
  // Booleans, floats, numeric strings, and values past the safe-integer range are
  // not integers here. Past that range the value is not exact, and String(value)
  // can render exponential notation instead of the decimal digits the prompt binds.
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) {
    throw new InputValidationError(`${field} must be an integer.`);
  }

  if (spec.minimum !== undefined && value < spec.minimum) {
    throw new InputValidationError(`${field} must be at least ${spec.minimum}.`);
  }

  if (spec.maximum !== undefined && value > spec.maximum) {
    throw new InputValidationError(`${field} must be at most ${spec.maximum}.`);
  }
}

function validateArrayField(
  field: string,
  value: unknown,
  spec: DeclaredFieldSchema,
  defs: Record<string, DeclaredFieldSchema>,
): void {
  if (!Array.isArray(value)) {
    throw new InputValidationError(`${field} must be an array.`);
  }
  const count = (n: number) => `${n} item${n === 1 ? '' : 's'}`;
  if (spec.minItems !== undefined && value.length < spec.minItems) {
    throw new InputValidationError(`${field} needs at least ${count(spec.minItems)}; received ${value.length}.`);
  }
  if (spec.maxItems !== undefined && value.length > spec.maxItems) {
    throw new InputValidationError(`${field} accepts at most ${count(spec.maxItems)}; received ${value.length}.`);
  }
  const items = spec.items ? resolveField(spec.items, defs) : undefined;
  if (items?.type !== 'string' && items?.type !== 'object') {
    // A contract fault, not a caller's: the eval-schemas check admits only these two.
    throw new Error(
      `${field} is declared as an array of ${String(items?.type)}; only arrays of strings or objects are supported.`,
    );
  }
  value.forEach((item, i) => {
    const where = `${field}[${i}]`;
    if (items.type === 'object') {
      validateObjectField(where, item, items);
      return;
    }
    if (typeof item !== 'string') {
      throw new InputValidationError(`${where} must be a string.`);
    }
    validateStringField(where, item, items);
  });
}

function validateObjectField(path: string, value: unknown, spec: DeclaredFieldSchema): void {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new InputValidationError(`${path} must be an object.`);
  }
  const record = value as Record<string, unknown>;
  const properties = spec.properties ?? {};
  const declared = Object.keys(properties);
  if (spec.additionalProperties === false) {
    for (const key of Object.keys(record)) {
      if (!declared.includes(key)) {
        throw new InputValidationError(
          `Unknown input "${path}.${key}". This object accepts: ${declared.join(', ')}.`,
        );
      }
    }
  }
  const required = spec.required ?? [];
  for (const prop of [...required, ...declared.filter((name) => !required.includes(name))]) {
    const propSpec = properties[prop];
    const propValue = record[prop];
    const propPath = `${path}.${prop}`;
    if (propSpec.type !== 'string') {
      // A contract fault, as above: object fields are strings.
      throw new Error(`${propPath} is declared as ${String(propSpec.type)}; only string fields are supported.`);
    }
    if (propValue === undefined || propValue === null) {
      if (required.includes(prop)) {
        throw new InputValidationError(`${propPath} is required.`);
      }
      continue;
    }
    if (typeof propValue !== 'string') {
      throw new InputValidationError(`${propPath} must be a string.`);
    }
    validateStringField(propPath, propValue, propSpec);
  }
}

function validateStringField(field: string, value: string, spec: DeclaredFieldSchema): void {
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
