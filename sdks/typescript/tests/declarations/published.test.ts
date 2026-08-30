import { describe, it, expect } from 'vitest';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The published declaration file, checked against a real build.
 *
 * These live outside `tests/unit` on purpose, and outside `tests/dist` because
 * `.gitignore` excludes every `dist/` path — a suite placed there is not even committed. `npm run test:unit` does not build, and CI's
 * build job runs *after* the test job, so a `dist`-dependent assertion placed in the unit
 * suite silently skips on every CI run — which is what happened to the first version of
 * these checks. `npm run verify:dist` runs them immediately after `npm run build`, and they
 * fail rather than skip when `dist` is absent.
 *
 * What they encode: the bundle once carried 136 `tsc` errors, because a public input type
 * written as `InputsOf<typeof INPUT_SCHEMA>` made the dts bundler inline every contract as
 * `var` value declarations, illegal in an ambient context. Anyone compiling without
 * `skipLibCheck` — the default — failed on our types instead of their own.
 */

const TS_ROOT = join(import.meta.dirname, '../..');
const ENTRIES = ['dist/index.d.ts', 'dist/batch/index.d.ts'];

/**
 * The repo's own compiler, not whatever `npx tsc` resolves to.
 *
 * Going through `npx` can pick up a global install or fetch a different version, which would
 * let this pass or fail for reasons unrelated to the declarations under test.
 */
const TSC = join(TS_ROOT, 'node_modules/.bin/tsc');

function read(entry: string): string {
  const path = join(TS_ROOT, entry);
  if (!existsSync(path)) {
    throw new Error(
      `${entry} is missing. These checks run against a build: \`npm run build\` first, ` +
        'or use `npm run verify:dist`.',
    );
  }
  return readFileSync(path, 'utf-8');
}

describe('the published declarations typecheck on their own', () => {
  it.each(ENTRIES)('%s reports no errors under a consumer-default tsc', (entry) => {
    read(entry); // fail loudly if the build is missing

    // No `skipLibCheck`: that is the whole point. tsc exits non-zero on any error, so the
    // assertion is that this call does not throw.
    expect(() =>
      execFileSync(
        TSC,
        [
          '--noEmit',
          '--strict',
          '--target',
          'es2022',
          '--module',
          'nodenext',
          '--moduleResolution',
          'nodenext',
          entry,
        ],
        { cwd: TS_ROOT, stdio: 'pipe', encoding: 'utf-8' },
      ),
    ).not.toThrow();
  }, 180_000);

  it.each(ENTRIES)('%s declares no values', (entry) => {
    // The 136 errors were all non-ambient `var X = <json literal>` statements. A declaration
    // file may declare values — `declare const` is fine — so the invariant is specifically
    // that no bare `var` survives, which is the same defect stated without a compiler.
    const vars = [...read(entry).matchAll(/^var (\w+)/gm)].map((m) => m[1]);

    expect(vars, `${entry} declares values: ${vars.slice(0, 5).join(', ')}`).toEqual([]);
  });
});

describe('every type a caller needs is reachable from the built package', () => {
  /** Names in the built bundle's export statements, aliases resolved. */
  function exportedNames(entry: string): string[] {
    return [...read(entry).matchAll(/^export (?:type )?\{([^}]*)\}/gm)]
      .flatMap((m) => m[1].split(','))
      .map((e) => e.replace(/^\s*type\s+/, '').trim().split(' as ').pop()!.trim())
      .filter(Boolean);
  }

  it('exports an input type for every evaluator', () => {
    const exported = exportedNames('dist/index.d.ts');
    const declared = [...read('dist/index.d.ts').matchAll(/type (\w+Input) =/g)].map((m) => m[1]);

    expect(declared.length).toBeGreaterThanOrEqual(16);

    const missing = declared.filter((name) => !exported.includes(name));
    expect(missing, `declared but not exported: ${missing.join(', ')}`).toEqual([]);
  });

  it('exports a result type and output schema for every evaluator that has one', () => {
    const exported = exportedNames('dist/index.d.ts');
    const source = read('dist/index.d.ts');
    const declared = [
      ...[...source.matchAll(/type (\w+Result) =/g)].map((m) => m[1]),
      ...[...source.matchAll(/declare const (\w+OutputSchema)/g)].map((m) => m[1]),
    ];

    expect(declared.length).toBeGreaterThan(0);

    const missing = declared.filter((name) => !exported.includes(name));
    expect(missing, `declared but not exported: ${missing.join(', ')}`).toEqual([]);
  });
});
