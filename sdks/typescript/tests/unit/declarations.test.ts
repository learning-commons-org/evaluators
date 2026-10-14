import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import * as barrel from '../../src/index.js';

/**
 * What the package publishes as types, and what a consumer can actually reach.
 *
 * Two defects motivated this. The declaration bundle contained 136 `tsc` errors, because a
 * public input type written as `InputsOf<typeof INPUT_SCHEMA>` made the dts bundler inline
 * every contract as `var` declarations — illegal in an ambient context, so anyone compiling
 * without `skipLibCheck` failed on our types rather than theirs. And sixteen input types were
 * declared but never exported, so the argument type of the primary API had no name.
 *
 * The input types now name their keys directly, which is what these check against the
 * contracts, since a literal union can drift where a derived type could not.
 */

const SRC = join(import.meta.dirname, '../../src');
const EVALS = join(import.meta.dirname, '../../../../evals');

/** Every evaluator source that declares an input type. */
function evaluatorSources(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return evaluatorSources(path);
    return path.endsWith('.ts') ? [path] : [];
  });
}

interface Declared {
  file: string;
  typeName: string;
  /** Property name -> the TypeScript type text the generator emitted. */
  properties: Record<string, string>;
  /** The properties the generator emitted as optional (`"name"?:`). */
  optional: string[];
  contract: Record<string, { enum?: string[]; type?: string }>;
  required: string[];
}

/** The generated schema modules, which now carry each evaluator's input type. */
function generatedModules(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return generatedModules(path);
    return path.endsWith('.ts') ? [path] : [];
  });
}

const DECLARED: Declared[] = generatedModules(join(SRC, 'schemas')).flatMap((file) => {
  const source = readFileSync(file, 'utf-8');

  // `export type XInput = { ... };` as the generator prints it.
  const typeMatch = source.match(/export type (\w+Input) = \{\n([\s\S]*?)\n\};/);
  const sourceMatch = source.match(/^\/\/\s+(\S*input_schema\.json)$/m);
  if (!typeMatch || !sourceMatch) return [];

  const properties: Record<string, string> = {};
  const optional: string[] = [];
  for (const line of typeMatch[2].split('\n')) {
    const prop = line.match(/^\s*"([^"]+)"(\?)?:\s*(.+);$/);
    if (!prop) continue;
    properties[prop[1]] = prop[3].trim();
    if (prop[2]) optional.push(prop[1]);
  }

  const relative = sourceMatch[1].replace(/^(\.\.\/)+/, '').replace(/^evals\//, '');
  const contract = JSON.parse(readFileSync(join(EVALS, relative), 'utf-8')) as {
    properties: Record<string, { enum?: string[]; type?: string }>;
    required?: string[];
  };

  return [
    { file, typeName: typeMatch[1], properties, optional, contract: contract.properties, required: contract.required ?? [] },
  ];
});

type EvaluatorLike = { metadata: { id: string } };

/** The name stem each exported evaluator shares with its generated `<Stem>Input` type. */
const EVALUATOR_STEMS = Object.entries(barrel as Record<string, unknown>)
  .filter(
    ([, v]) =>
      typeof v === 'function' && typeof (v as unknown as EvaluatorLike).metadata?.id === 'string',
  )
  .map(([name]) => name.replace(/Evaluator$/, ''))
  // Math assembles its payload from per-component results and has no single output schema,
  // so its input type stays hand-written and has no generated module.
  .filter((stem) => stem !== 'MathStandardsAlignment')
  .sort();

describe('input types match the contracts they name', () => {
  it('has one generated module per exported evaluator, so the cases below cannot pass vacuously', () => {
    // By name against the barrel rather than a pinned count: a module or an evaluator going
    // missing fails here and says which, and adding an evaluator bumps nothing.
    expect(EVALUATOR_STEMS.length).toBeGreaterThan(0);
    expect(DECLARED.map((d) => d.typeName.replace(/Input$/, '')).sort()).toEqual(EVALUATOR_STEMS);
  });

  it.each(DECLARED)('$typeName names the inputs its contract declares', ({ properties, contract }) => {
    expect(Object.keys(properties).sort()).toEqual(Object.keys(contract).sort());
  });

  it.each(DECLARED)('$typeName is optional exactly where its contract does not require', ({ optional, contract, required }) => {
    expect(optional.sort()).toEqual(Object.keys(contract).filter((name) => !required.includes(name)).sort());
  });

  it.each(DECLARED)('$typeName carries the contract\'s enum values and array shape', ({ typeName, properties, contract }) => {
    // The reason for generating these rather than deriving them: a declared `enum` becomes a
    // literal union, so a bad grade is a compile error instead of a run-time one on a paid
    // call. An array of strings (an attached input's paths) is `string[]`. Anything else stays
    // `string` — the length and count bounds are not expressible.
    for (const [name, spec] of Object.entries(contract)) {
      const expected = spec.enum
        ? spec.enum.map((v) => JSON.stringify(v)).join(' | ')
        : spec.type === 'array'
          ? 'string[]'
          : 'string';

      expect(properties[name], `${typeName}.${name}`).toBe(expected);
    }
  });
});

describe('the source never reintroduces the cause', () => {
  it('never derives a public input type from an imported contract', () => {
    // Source-level, so it fails before a build rather than after one.
    const offenders = evaluatorSources(join(SRC, 'evaluators')).filter((file) =>
      /export type \w+Input = InputsOf<typeof /.test(readFileSync(file, 'utf-8')),
    );

    expect(offenders.map((f) => f.replace(SRC, 'src'))).toEqual([]);
  });

  it('leaves the input types to the generator', () => {
    // A hand-written one would drift from its contract's enum values, which is what the
    // generator exists to prevent. Math is the exception and declares its own.
    const offenders = evaluatorSources(join(SRC, 'evaluators'))
      .filter((file) => /export type \w+Input = \{/.test(readFileSync(file, 'utf-8')))
      .filter((file) => !file.includes('math-standards-alignment'));

    expect(offenders.map((f) => f.replace(SRC, 'src'))).toEqual([]);
  });
});
