import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

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
  contract: Record<string, { enum?: string[] }>;
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
  for (const line of typeMatch[2].split('\n')) {
    const prop = line.match(/^\s*"([^"]+)":\s*(.+);$/);
    if (prop) properties[prop[1]] = prop[2].trim();
  }

  const relative = sourceMatch[1].replace(/^(\.\.\/)+/, '').replace(/^evals\//, '');
  const contract = JSON.parse(readFileSync(join(EVALS, relative), 'utf-8')) as {
    properties: Record<string, { enum?: string[] }>;
  };

  return [{ file, typeName: typeMatch[1], properties, contract: contract.properties }];
});

describe('input types match the contracts they name', () => {
  it('finds them, so the cases below cannot pass vacuously', () => {
    // Fifteen generated modules; math assembles its payload from per-component results and
    // has no single output schema, so its input type stays hand-written.
    expect(DECLARED).toHaveLength(15);
  });

  it.each(DECLARED)('$typeName names the inputs its contract declares', ({ properties, contract }) => {
    expect(Object.keys(properties).sort()).toEqual(Object.keys(contract).sort());
  });

  it.each(DECLARED)('$typeName carries the contract\'s enum values', ({ typeName, properties, contract }) => {
    // The reason for generating these rather than deriving them: a declared `enum` becomes a
    // literal union, so a bad grade is a compile error instead of a run-time one on a paid
    // call. A field with no enum stays `string` — the length bounds are not expressible.
    for (const [name, spec] of Object.entries(contract)) {
      const expected = spec.enum
        ? spec.enum.map((v) => JSON.stringify(v)).join(' | ')
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
