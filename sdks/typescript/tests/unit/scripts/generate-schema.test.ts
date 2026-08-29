import { describe, it, expect } from 'vitest';
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveRefs, toPascalCase, generateSchemaFile } from '../../../scripts/generate-schema.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SDK_ROOT = resolve(__dirname, '../../..');
const PURPOSE_CONFIG = resolve(__dirname, '../../../../../evals/student-facing-text/ela-reading/purpose-clarity/config.json');
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

  it('lets keys beside a $ref override the definition', () => {
    // Several contracts point two fields at one definition and tell them apart with a
    // sibling `description`, which becomes that field's `.describe()`. Returning the bare
    // definition made those fields say the same thing to the model.
    const defs = { Band: { type: 'string', description: 'shared' } };

    const result = resolveRefs({ $ref: '#/$defs/Band', description: 'this field only' }, defs);

    expect(result).toEqual({ type: 'string', description: 'this field only' });
  });

  it('keeps definition keys the sibling does not override', () => {
    const defs = { Band: { type: 'string', enum: ['a', 'b'], description: 'shared' } };

    const result = resolveRefs({ $ref: '#/$defs/Band', description: 'mine' }, defs);

    expect(result).toEqual({ type: 'string', enum: ['a', 'b'], description: 'mine' });
  });

  it('throws on an unknown $ref key, naming the ref', () => {
    expect(() => resolveRefs({ $ref: '#/$defs/Missing' }, {})).toThrow('#/$defs/Missing');
  });

  it('leaves a non-string $ref alone rather than resolving it', () => {
    const node = { $ref: 42, type: 'string' };

    expect(resolveRefs(node, {})).toEqual(node);
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
  it('derives slug as the last id segment, in the file naming convention', () => {
    const { slug } = generateSchemaFile(PURPOSE_CONFIG);
    expect(slug).toBe('purpose-clarity');
  });

  it('writes output under the SDK src/schemas root, at the derived path', () => {
    const { outPath } = generateSchemaFile(PURPOSE_CONFIG);

    expect(outPath).toBe(
      join(SDK_ROOT, 'src/schemas/student-facing-text/ela-reading/purpose-clarity.ts'),
    );
  });

  it('generates a file identical to the committed one', () => {
    // The whole file, not a substring: the header, the blank lines and the
    // `// prettier-ignore` that keeps lint off the one long generated line all matter,
    // and this is the assertion CI's --check makes.
    const { outPath, content } = generateSchemaFile(PURPOSE_CONFIG);

    expect(content).toBe(readFileSync(outPath, 'utf-8'));
  });

  it('includes the GENERATED header', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    expect(content).toContain('GENERATED — do not edit directly.');
    expect(content).toContain('output_schema.json');
    expect(content).toContain('npm run generate:schemas');
  });

  it('exports PurposeClarityOutputSchema and PurposeClarityInternal', () => {
    const { content } = generateSchemaFile(PURPOSE_CONFIG);
    expect(content).toContain('export const PurposeClarityOutputSchema');
    expect(content).toContain('export type PurposeClarityInternal');
    expect(content).not.toContain('export type PurposeClarityComplexityLevel');
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

  it.each([
    ['evaluator.id', { output_schema: { $ref: 'output_schema.json' } }],
    ['output_schema.$ref', { evaluator: { id: 'a.b.c' } }],
  ])('names %s when the config omits it', (missing, config) => {
    const path = join(tmpdir(), `generate-schema-${missing}.json`);
    writeFileSync(path, JSON.stringify(config), 'utf-8');

    expect(() => generateSchemaFile(path)).toThrow(missing);
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

  it('--check exits 0 when the committed file matches the contract', () => {
    const result = spawnSync(TSX_BIN, [SCRIPT_PATH, '--check', PURPOSE_CONFIG], {
      encoding: 'utf-8',
    });
    expect(result.status).toBe(0);
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

// --- against the real contracts ---
//
// Each defect below was invisible in synthetic fixtures: the generated schema stayed
// structurally valid and simply said less to the model.

describe('generateSchemaFile against real contracts', () => {
  const contract = (dir: string) => resolve(SDK_ROOT, '..', '..', 'evals', dir, 'config.json');

  it('keeps each grade band field distinguishable', () => {
    // Both fields $ref one GradeBand definition. With the siblings dropped they reach
    // the model with identical text, and they are the whole output.
    const { content } = generateSchemaFile(
      contract('student-facing-text/ela-reading/grade-level-appropriateness'),
    );

    expect(content).toContain('Target grade band for the text at independent reading.');
    expect(content).toContain('A second grade band that could read and comprehend the text');
  });

  it('keeps every per-feature rubric line in a feedback contract', () => {
    // Each key_features property $refs one KeyFeatureAssessment and carries its own
    // criterion; dropping siblings replaces all of them with the shared sentence.
    const { content } = generateSchemaFile(contract('feedback/ela-writing/tone-appropriateness'));

    expect(content).toContain('Whether the language is neutral and professional');
    expect(content).toContain('Whether the feedback targets the work');
    expect(content).toContain('Whether any praise matches the actual quality of the work');
  });

  it('does not send the contract-level description to the model', () => {
    const { content } = generateSchemaFile(
      contract('student-facing-text/ela-reading/vocabulary-complexity'),
    );

    expect(content).not.toContain('Final evaluator output for');
  });

  it('derives the path from the whole id, not the last segment', () => {
    const { outPath } = generateSchemaFile(
      contract('academic-standards-alignment/mathematics/math-standards-alignment'),
    );

    expect(outPath).toContain(
      'schemas/academic-standards-alignment/mathematics/math-standards-alignment.ts',
    );
  });

  it('names the export from the last segment, which is what a call site reads', () => {
    const { content } = generateSchemaFile(
      contract('student-facing-text/ela-reading/purpose-clarity'),
    );

    expect(content).toContain('export const PurposeClarityOutputSchema');
  });
});
