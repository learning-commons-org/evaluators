import { describe, it, expect } from 'vitest';
import {
  getEvaluators,
  getEvaluator,
  getEvaluatorClass,
  indexById,
} from '../../../src/evaluators/registry.js';
import * as barrel from '../../../src/index.js';
import { InputValidationError } from '../../../src/errors.js';

/**
 * The registry, checked against the public barrel rather than against itself.
 *
 * Two hand-maintained id-to-class maps used to exist in the batch families for want of
 * this. The completeness check reads the barrel independently, so an evaluator that is
 * exported but never registered fails here instead of going quietly missing from
 * `getEvaluators()`.
 *
 * Every parameterised case is built from the barrel, never from `getEvaluators()`. Driving
 * `it.each` off the subject meant a mutant that broke it took test *collection* down with
 * it — zero tests ran and the mutant scored as survived rather than caught.
 */

interface EvaluatorLike {
  metadata: { id: string; stableId: string; idHistory: readonly string[] };
}

/** Evaluator classes reachable from the package's public entry point. */
const EXPORTED = Object.entries(barrel as Record<string, unknown>)
  .filter(
    ([, v]) =>
      typeof v === 'function' && typeof (v as unknown as EvaluatorLike).metadata?.id === 'string',
  )
  .map(([name, v]) => ({ name, cls: v as unknown as EvaluatorLike }));

const FORMER_IDS = EXPORTED.flatMap(({ name, cls }) =>
  cls.metadata.idHistory.map((former) => ({ name, former, cls })),
);

describe('the fixtures these tests are built from', () => {
  it('finds all sixteen evaluators on the barrel', () => {
    expect(EXPORTED).toHaveLength(16);
  });

  it('finds historical ids, so the rename cases are not vacuous', () => {
    expect(FORMER_IDS.length).toBeGreaterThan(0);
  });
});

describe('getEvaluators', () => {
  it('holds every evaluator the package exports', () => {
    const registered = new Set(getEvaluators().map((m) => m.id));
    const missing = EXPORTED.filter(({ cls }) => !registered.has(cls.metadata.id)).map(
      ({ name }) => name,
    );

    expect(missing, `exported but unregistered: ${missing.join(', ')}`).toEqual([]);
  });

  it('holds nothing the package does not export', () => {
    const exported = new Set(EXPORTED.map(({ cls }) => cls.metadata.id));
    const extra = getEvaluators()
      .map((m) => m.id)
      .filter((id) => !exported.has(id));

    expect(extra, `registered but not exported: ${extra.join(', ')}`).toEqual([]);
  });

  it('returns as many as the barrel exports', () => {
    expect(getEvaluators()).toHaveLength(EXPORTED.length);
  });

  it('registers each id once', () => {
    const ids = getEvaluators().map((m) => m.id);

    expect(new Set(ids).size).toBe(ids.length);
  });

  it('cannot be mutated through the returned list', () => {
    // `readonly` is erased at runtime and this hands the array out directly, so without
    // freezing it a caller appending to it corrupts every later lookup.
    expect(() => (getEvaluators() as unknown as unknown[]).push({})).toThrow();
    expect(getEvaluators()).toHaveLength(EXPORTED.length);
  });
});

describe('getEvaluator', () => {
  it.each(EXPORTED)('resolves $name by its current id', ({ cls }) => {
    expect(getEvaluator(cls.metadata.id)).toBe(cls.metadata);
  });

  it.each(FORMER_IDS)('resolves $name by its former id $former', ({ cls, former }) => {
    // Renames stay resolvable, which is what keeps an archived result identifiable.
    expect(getEvaluator(former)).toBe(cls.metadata);
  });

  it('returns undefined for an id no evaluator carries', () => {
    // Not a throw: "not found" is a normal answer, and callers reading archived results
    // ask this before committing to `readOutcome`.
    expect(getEvaluator('literacy.removed.evaluator')).toBeUndefined();
    expect(getEvaluator('')).toBeUndefined();
  });

  it.each(EXPORTED)('does not resolve $name by its stableId', ({ cls }) => {
    // `stableId` identifies the evaluator across renames but is not a lookup key; treating
    // it as one would make two different identifiers silently interchangeable.
    expect(getEvaluator(cls.metadata.stableId)).toBeUndefined();
  });

  it('returns metadata, not the class', () => {
    // The public lookup deliberately does not hand out a constructor: resolving by id
    // erases which named inputs the evaluator takes, and nothing here can express that.
    const resolved = getEvaluator('student_facing_text.ela_reading.meaning_directness');

    expect(resolved).toBeDefined();
    expect(typeof resolved).toBe('object');
    expect(resolved!.defaultProviders.length).toBeGreaterThan(0);
  });
});

describe('getEvaluatorClass', () => {
  it('is not reachable from the package entry point', () => {
    // Internal on purpose. If this starts being exported, the erased-input hazard in
    // RegisteredEvaluator's docstring becomes a public one.
    //
    // Only the function is asserted here. `RegisteredEvaluator` is a type, erased before
    // this runs, so a runtime check on it would pass whether or not it were exported —
    // `typeTest` below is what actually holds that line.
    expect(barrel).not.toHaveProperty('getEvaluatorClass');
  });

  it.each(EXPORTED)('resolves $name to a constructible class', ({ cls }) => {
    const E = getEvaluatorClass(cls.metadata.id);

    expect(E).toBe(cls);
    expect(typeof E).toBe('function');
  });

  it('returns a class whose own schema still rejects foreign inputs', () => {
    // What replaces type safety here: the evaluator validates its declared inputs, so a
    // caller that resolves by id and guesses wrong fails loudly rather than silently.
    const E = getEvaluatorClass(
      'academic_standards_alignment.mathematics.math_standards_alignment',
    )!;

    return expect(
      new E({ anthropicApiKey: 'k', learningCommonsApiKey: 'k' }).evaluate({
        text: 'not what math takes',
        grade_level: '5',
      }),
    ).rejects.toThrow(InputValidationError);
  });

  it('returns undefined for an id no evaluator carries', () => {
    expect(getEvaluatorClass('literacy.removed.evaluator')).toBeUndefined();
  });
});

/**
 * Compile-time half of the check above: neither the constructible type nor its accessor may
 * be reachable from the public entry point. If either is exported, the expected error does
 * not occur and `@ts-expect-error` itself fails the build.
 */
export type TypeTest = [
  // @ts-expect-error - RegisteredEvaluator is internal
  import('../../../src/index.js').RegisteredEvaluator,
  // @ts-expect-error - getEvaluatorClass is internal
  typeof import('../../../src/index.js').getEvaluatorClass,
];

describe('indexById', () => {
  // The real registry cannot contain a duplicate, so the collision path is driven directly.
  const stub = (id: string, idHistory: readonly string[], name: string) =>
    ({ metadata: { id, idHistory, name } }) as unknown as Parameters<typeof indexById>[0][number];

  it('indexes an evaluator under its current id and every former one', () => {
    const E = stub('current.id', ['old.id', 'older.id'], 'Thing');

    const index = indexById([E]);

    expect(index.get('current.id')).toBe(E);
    expect(index.get('old.id')).toBe(E);
    expect(index.get('older.id')).toBe(E);
    expect(index.size).toBe(3);
  });

  it('throws when two evaluators claim the same current id', () => {
    // `new Map` would keep the last silently, and lookups would return the wrong evaluator.
    const a = stub('shared.id', [], 'First');
    const b = stub('shared.id', [], 'Second');

    expect(() => indexById([a, b])).toThrow(/shared\.id.*First.*Second/);
  });

  it('throws when one evaluator\'s former id is another\'s current id', () => {
    // The plausible collision: a rename frees a name that something else later takes.
    const a = stub('a.current', ['contested.id'], 'First');
    const b = stub('contested.id', [], 'Second');

    expect(() => indexById([a, b])).toThrow(/contested\.id/);
  });

  it('tolerates an evaluator listing the same id twice', () => {
    // Same evaluator, so nothing is ambiguous — only a cross-evaluator clash is an error.
    const E = stub('same.id', ['same.id'], 'Thing');

    expect(() => indexById([E])).not.toThrow();
  });
});
