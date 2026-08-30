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
  keys: string[];
  contractKeys: string[];
}

const DECLARED: Declared[] = evaluatorSources(join(SRC, 'evaluators')).flatMap((file) => {
  const source = readFileSync(file, 'utf-8');

  const typeMatch = source.match(
    /export type (\w+Input) = InputsOf<\{ properties: Record<([^>]+), unknown> \}>/,
  );
  const schemaMatch = source.match(/import INPUT_SCHEMA from '([^']+input_schema\.json)'/);
  if (!typeMatch || !schemaMatch) return [];

  // The contract the module itself imports, resolved the same way the compiler does.
  const relative = schemaMatch[1].replace(/^(\.\.\/)+/, '');
  const contract = JSON.parse(readFileSync(join(EVALS, relative.replace(/^evals\//, '')), 'utf-8'));

  return [
    {
      file,
      typeName: typeMatch[1],
      keys: [...typeMatch[2].matchAll(/'([^']+)'/g)].map((m) => m[1]),
      contractKeys: Object.keys(contract.properties),
    },
  ];
});

describe('input types match the contracts they name', () => {
  it('finds them, so the cases below cannot pass vacuously', () => {
    expect(DECLARED).toHaveLength(16);
  });

  it.each(DECLARED)('$typeName', ({ keys, contractKeys }) => {
    // Written out rather than derived, because deriving from `typeof <json>` is what broke
    // the declaration bundle. This is the check that keeps the two honest.
    expect([...keys].sort()).toEqual([...contractKeys].sort());
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
});
