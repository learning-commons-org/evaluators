import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import * as sdk from '../../src/index.js';

/**
 * The README and MIGRATION guide, checked against the SDK they describe.
 *
 * The README shipped `result.result.grade` — a field no schema has ever declared — as the
 * first code anyone runs, and listed 8 of the 16 evaluators. Prose goes stale silently, so
 * the claims that can be mechanically checked are checked here.
 */

const root = join(import.meta.dirname, '../..');
const README = readFileSync(join(root, 'README.md'), 'utf-8');
const MIGRATION = readFileSync(join(root, 'MIGRATION.md'), 'utf-8');

/** Every evaluator class the barrel exports. */
type EvaluatorLike = { metadata: { id: string; supportedGrades: readonly string[] } };

const EVALUATORS = Object.entries(sdk as Record<string, unknown>)
  .filter(
    ([, v]) =>
      typeof v === 'function' && typeof (v as unknown as EvaluatorLike).metadata?.id === 'string',
  )
  .map(([name, v]) => ({ name, metadata: (v as unknown as EvaluatorLike).metadata }));

describe('README', () => {
  it('finds the evaluators to check', () => {
    expect(EVALUATORS).toHaveLength(16);
  });

  it.each(EVALUATORS)('names $name', ({ name }) => {
    // The old README documented 8 of 16, omitting the whole feedback family and math.
    expect(README).toContain(`\`${name}\``);
  });

  it('states the count it actually documents', () => {
    expect(README).toContain('sixteen');
  });

  it('does not reference the removed exports', () => {
    // Renamed in 1.0.0; a stale name here sends readers to an import that throws.
    for (const gone of [
      'SmkEvaluator',
      'ConventionalityEvaluator',
      'PurposeEvaluator',
      'VocabularyEvaluator',
      'TextComplexityEvaluator',
      'ValidationError',
      'TimeoutError',
    ]) {
      expect(README, `README still mentions ${gone}`).not.toContain(`\`${gone}\``);
    }
  });

  it('reads the payload off the envelope, not off the result', () => {
    // The exact defect the audit found: `result.result.grade` on the first snippet.
    expect(README).not.toContain('result.result.');
    expect(README).not.toMatch(/\.grade\b(?!_)/);
  });

  it('documents every option the base config accepts', () => {
    const config = readFileSync(join(root, 'src/evaluators/base.ts'), 'utf-8');
    const block = config.slice(config.indexOf('export interface BaseEvaluatorConfig'));
    const options = [
      ...block.slice(0, block.indexOf('\n}')).matchAll(/^\s{2}(\w+)\?:/gm),
    ].map((m) => m[1]);

    expect(options.length).toBeGreaterThan(5);
    for (const option of options) {
      expect(README, `README does not document \`${option}\``).toContain(`\`${option}\``);
    }
  });

  it('names each evaluator with a grade range its contract supports', () => {
    for (const { name, metadata } of EVALUATORS) {
      const grades = metadata.supportedGrades;
      const row = README.split('\n').find((line) => line.includes(`\`${name}\``) && line.includes('|'));
      expect(row, `no table row for ${name}`).toBeDefined();
      // en dash, as the tables use
      expect(row, `${name} row does not show ${grades[0]}-${grades[grades.length - 1]}`).toContain(
        `${grades[0]}–${grades[grades.length - 1]}`,
      );
    }
  });
});

describe('the README on npm', () => {
  // Rendered on npmjs.com and browsable in node_modules, where only what `files` lists
  // exists. A relative link to something unpublished is dead in both places.
  const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf-8')) as {
    files: string[];
  };

  /** Relative markdown link targets, minus any anchor. */
  const RELATIVE_LINKS = [...README.matchAll(/\]\((\.\/[^)#]+)/g)].map((m) =>
    m[1].replace(/^\.\//, ''),
  );

  it('makes relative links, so this is not vacuous', () => {
    expect(RELATIVE_LINKS.length).toBeGreaterThan(0);
  });

  it.each(RELATIVE_LINKS)('%s exists on disk', (target) => {
    expect(existsSync(join(root, target)), `${target} is linked but missing`).toBe(true);
  });

  it.each(RELATIVE_LINKS)('%s is in the published files allowlist', (target) => {
    // Covered either by its own entry or by a directory entry that contains it.
    const published = pkg.files.some((entry) => target === entry || target.startsWith(`${entry}/`));

    expect(published, `${target} is linked from the README but \`files\` omits it`).toBe(true);
  });
});

describe('MIGRATION', () => {
  it('every name in a rename table\'s current column is exported', () => {
    // A rename row is `| `old` | `new` |` and nothing else — the current cell is exactly one
    // backticked identifier. Cells carrying prose describe a changed shape rather than a
    // rename (a removed property, a new constructor signature), and naming an export is not
    // what they are doing, so they are skipped rather than mis-asserted.
    const claimed = MIGRATION.split('\n')
      .filter((line) => line.startsWith('| `') && line.split('|').length === 4)
      .flatMap((line) => {
        const current = line.split('|')[2].trim();
        const single = current.match(/^`(\w+)`$/);
        return single ? [single[1]] : [];
      });

    expect(claimed.length).toBeGreaterThan(5);

    const missing = [...new Set(claimed)].filter((n) => !(n in sdk));
    expect(missing, `MIGRATION names exports that do not exist: ${missing.join(', ')}`).toEqual([]);
  });

  it('every name it presents as removed really is gone', () => {
    for (const gone of [
      'SmkEvaluator',
      'ConventionalityEvaluator',
      'PurposeEvaluator',
      'VocabularyEvaluator',
      'TextComplexityEvaluator',
      'evaluateTextComplexity',
      'ValidationError',
      'TimeoutError',
      'APIError',
      'Providers',
    ]) {
      expect(MIGRATION, `MIGRATION should mention ${gone}`).toContain(gone);
      expect(gone in sdk, `${gone} is documented as removed but is still exported`).toBe(false);
    }
  });

  it('the reparenting it warns about is real', () => {
    // The subtle one: a caller catching KnowledgeGraphError used to see this.
    expect(MIGRATION).toContain('StandardNotFoundError');

    const error = new sdk.StandardNotFoundError('no such code', '9.ZZ.9');
    expect(error).toBeInstanceOf(sdk.InputValidationError);
    expect(error).not.toBeInstanceOf(sdk.KnowledgeGraphError);
  });

  it('the error parents it describes are the real ones', () => {
    for (const name of [
      'AuthenticationError',
      'RateLimitError',
      'NetworkError',
      'RequestTimeoutError',
      'LLMProviderError',
      'KnowledgeGraphError',
    ]) {
      const Cls = sdk[name as keyof typeof sdk] as new (
        m: string,
        o: { dependency: string },
      ) => Error;
      expect(
        new Cls('x', { dependency: 'openai' }),
        `${name} extends DependencyError`,
      ).toBeInstanceOf(sdk.DependencyError);
    }
  });

  it('quotes the peer ranges the package actually declares', () => {
    const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf-8')) as {
      peerDependencies: Record<string, string>;
      engines: { node: string };
    };

    for (const [dep, range] of Object.entries(pkg.peerDependencies)) {
      expect(MIGRATION, `MIGRATION omits the ${dep} range`).toContain(`\`${range}\``);
    }
    expect(MIGRATION).toContain(`\`${pkg.engines.node}\``);
  });
});
