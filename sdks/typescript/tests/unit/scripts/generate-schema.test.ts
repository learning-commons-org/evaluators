import { describe, it, expect } from 'vitest';
import { spawnSync } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveRefs, toPascalCase, generateSchemaFile } from '../../../scripts/generate-schema.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SDK_ROOT = resolve(__dirname, '../../..');
const PURPOSE_CONFIG = resolve(__dirname, '../../../../../evals/prompts/purpose/config.json');
const SCRIPT_PATH = resolve(SDK_ROOT, 'scripts/generate-schema.ts');
const TSX_BIN = resolve(SDK_ROOT, 'node_modules/.bin/tsx');

// --- resolveRefs ---

describe('resolveRefs', () => {
  it('returns primitives unchanged', () => {
    expect(resolveRefs('hello', {})).toBe('hello');
    expect(resolveRefs(42, {})).toBe(42);
    expect(resolveRefs(null, {})).toBe(null);
  });

  it('inlines a simple $ref', () => {
    const defs = { Foo: { type: 'string' } };
    expect(resolveRefs({ $ref: '#/$defs/Foo' }, defs)).toEqual({ type: 'string' });
  });

  it('resolves nested $refs recursively', () => {
    const defs = {
      Item: { type: 'object', properties: { value: { type: 'string' } } },
    };
    const result = resolveRefs({ type: 'array', items: { $ref: '#/$defs/Item' } }, defs);
    expect(result).toEqual({
      type: 'array',
      items: { type: 'object', properties: { value: { type: 'string' } } },
    });
  });

  it('strips $defs from resolved output', () => {
    const schema = {
      type: 'object',
      properties: { name: { type: 'string' } },
      $defs: { Foo: { type: 'string' } },
    };
    const result = resolveRefs(schema, schema.$defs as Record<string, { type: string }>);
    expect(result).not.toHaveProperty('$defs');
    expect(result).toHaveProperty('properties');
  });

  it('resolves arrays element-wise', () => {
    const defs = { Str: { type: 'string' } };
    const result = resolveRefs([{ $ref: '#/$defs/Str' }, { type: 'number' }], defs);
    expect(result).toEqual([{ type: 'string' }, { type: 'number' }]);
  });

  it('throws on an unknown $ref key', () => {
    expect(() => resolveRefs({ $ref: '#/$defs/Missing' }, {})).toThrow(/Missing/);
  });
});

// --- toPascalCase ---

describe('toPascalCase', () => {
  it('capitalises a single word', () => {
    expect(toPascalCase('purpose')).toBe('Purpose');
  });

  it('converts kebab-case', () => {
    expect(toPascalCase('grade-level')).toBe('GradeLevel');
  });

  it('converts snake_case', () => {
    expect(toPascalCase('sentence_structure')).toBe('SentenceStructure');
  });

  it('handles already-capitalised input', () => {
    expect(toPascalCase('Purpose')).toBe('Purpose');
  });
});

// --- generateSchemaFile ---

describe('generateSchemaFile', () => {
  it('derives slug as the last dot-segment of evaluator.id', () => {
    const { slug } = generateSchemaFile(PURPOSE_CONFIG);
    expect(slug).toBe('purpose');
  });

  it('writes output to src/schemas/purpose.ts', () => {
    const { outPath } = generateSchemaFile(PURPOSE_CONFIG);
    expect(outPath).toMatch(/src\/schemas\/purpose\.ts$/);
  });

  it('includes the GENERATED header', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    expect(content).toContain('GENERATED — do not edit directly.');
    expect(content).toContain('output_schema.json');
    expect(content).toContain('npm run generate:schemas');
  });

  it('exports PurposeOutputSchema and PurposeInternal', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    expect(content).toContain('export const PurposeOutputSchema');
    expect(content).toContain('export type PurposeInternal');
    expect(content).not.toContain('export type PurposeComplexityLevel');
  });

  it('generates all 5 Purpose complexity levels', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    for (const level of [
      'slightly_complex',
      'moderately_complex',
      'very_complex',
      'exceedingly_complex',
      'more_context_needed',
    ]) {
      expect(content).toContain(level);
    }
  });

  it('generates details sub-fields from output_schema.json $defs', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    expect(content).toContain('detailed_summary');
    expect(content).toContain('adjustment_and_scaffolding');
    expect(content).toContain('recommended_use_cases');
    // $refs should be resolved — z.any() would mean $ref resolution failed
    expect(content).not.toContain('z.any()');
  });

  it('generates .strict() for objects with additionalProperties: false', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    expect(content).toContain('.strict()');
  });

  it('throws on a non-existent config path', () => {
    expect(() => generateSchemaFile('/nonexistent/config.json')).toThrow();
  });

  it('output is deterministic across multiple calls', () => {
    const first = generateSchemaFile(PURPOSE_CONFIG).content;
    const second = generateSchemaFile(PURPOSE_CONFIG).content;
    expect(first).toBe(second);
  });
});

// --- main() CLI behavior ---

describe('main() CLI', () => {
  it('exits 1 with usage message when no args given', () => {
    const result = spawnSync(TSX_BIN, [SCRIPT_PATH], { encoding: 'utf-8' });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain('Usage');
  });

  it('--check exits 0 and prints ✓ when schema is up to date', () => {
    const result = spawnSync(TSX_BIN, [SCRIPT_PATH, '--check', PURPOSE_CONFIG], {
      encoding: 'utf-8',
    });
    expect(result.status).toBe(0);
    expect(result.stdout).toContain('✓  purpose: up to date');
  });

  it('--check exits 1 when schema file does not exist', () => {
    const result = spawnSync(
      TSX_BIN,
      [SCRIPT_PATH, '--check', '/nonexistent/config.json'],
      { encoding: 'utf-8' },
    );
    expect(result.status).toBe(1);
  });
});
