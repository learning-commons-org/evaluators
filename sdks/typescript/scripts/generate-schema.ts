#!/usr/bin/env tsx
/**
 * Generates Zod schemas from evaluator config.json + output_schema.json files.
 *
 * Each evaluator's config.json declares `output_schema.$ref` pointing to a JSON Schema.
 * This script resolves internal $refs, converts to Zod, and writes a typed TypeScript
 * file to src/schemas/{domain}/{skill}/{evaluator}.ts, derived from the evaluator id.
 *
 * Usage:
 *   tsx scripts/generate-schema.ts <config.json> [<config.json> ...]
 *   tsx scripts/generate-schema.ts --check <config.json> [<config.json> ...]
 *
 * The --check flag exits 1 if any generated file is out of sync (for CI).
 */

import { parseSchema } from 'json-schema-to-zod';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SDK_ROOT = resolve(__dirname, '..');
const SRC_SCHEMAS = join(SDK_ROOT, 'src', 'schemas');

type JsonValue = string | number | boolean | null | JsonValue[] | JsonObject;
type JsonObject = { [key: string]: JsonValue };

interface EvaluatorConfig {
  evaluator: { id: string };
  output_schema: { $ref: string };
}

interface GeneratedSchema {
  slug: string;
  outPath: string;
  content: string;
}

/**
 * Recursively resolves all internal $ref nodes using the schema's $defs map.
 * Strips $defs from the output — the resolved schema is self-contained.
 *
 * Keys sitting beside a `$ref` override the definition's own. That is what carries the
 * per-field meaning: several contracts point two or more fields at one definition and
 * distinguish them by a sibling `description`, which reaches the model as the field's
 * `.describe()`. Returning the bare definition makes those fields say the same thing.
 */
export function resolveRefs(node: JsonValue, defs: Record<string, JsonObject>): JsonValue {
  if (typeof node !== 'object' || node === null) return node;
  if (Array.isArray(node)) return node.map((item) => resolveRefs(item, defs));

  if ('$ref' in node && typeof node['$ref'] === 'string') {
    const key = node['$ref'].replace('#/$defs/', '');
    const def = defs[key];
    if (!def) throw new Error(`Cannot resolve $ref "${node['$ref']}": key "${key}" not found in $defs`);
    const siblings = Object.fromEntries(
      Object.entries(node).filter(([name]) => name !== '$ref'),
    );
    return resolveRefs({ ...def, ...siblings }, defs);
  }

  const result: JsonObject = {};
  for (const [k, v] of Object.entries(node)) {
    if (k === '$defs') continue;
    result[k] = resolveRefs(v, defs);
  }
  return result;
}

/**
 * Converts a kebab-case or snake_case string to PascalCase.
 * e.g. "purpose" → "Purpose", "grade-level" → "GradeLevel"
 */
export function toPascalCase(str: string): string {
  return str
    .split(/[-_]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('');
}

/**
 * Generates the content of a Zod schema TypeScript file from a config.json path.
 * Returns slug, output path, and file content.
 */
export function generateSchemaFile(configPath: string): GeneratedSchema {
  const absConfigPath = resolve(configPath);
  const configDir = dirname(absConfigPath);

  const config = JSON.parse(readFileSync(absConfigPath, 'utf-8')) as EvaluatorConfig;

  if (!config.evaluator?.id) throw new Error(`config.json missing evaluator.id: ${configPath}`);
  if (!config.output_schema?.$ref) throw new Error(`config.json missing output_schema.$ref: ${configPath}`);

  // The path comes from the whole id, matching where the evaluator's own module lives,
  // so two evaluators sharing a last segment cannot overwrite each other. The exported
  // names come from the last segment alone, which is what reads well at a call site.
  const segments = config.evaluator.id.split('.').map((part) => part.replace(/_/g, '-'));
  const slug = segments[segments.length - 1];
  const className = toPascalCase(slug);

  const schemaPath = resolve(configDir, config.output_schema.$ref);
  const rawSchema = JSON.parse(readFileSync(schemaPath, 'utf-8')) as JsonObject;

  const defs = (rawSchema['$defs'] ?? {}) as Record<string, JsonObject>;
  const resolved = resolveRefs(rawSchema, defs) as JsonObject;

  // A root `description` describes the contract, not a field the model fills in, and
  // several are notes to maintainers. Per-field descriptions are kept.
  delete resolved['description'];

  const zodCode = parseSchema(resolved);

  const relSchemaPath = relative(SDK_ROOT, schemaPath);

  const content = [
    `// GENERATED — do not edit directly.`,
    `// Source: ${relSchemaPath}`,
    `// Regenerate: npm run generate:schemas`,
    ``,
    `import { z } from 'zod';`,
    ``,
    `// prettier-ignore`,
    `export const ${className}OutputSchema = ${zodCode};`,
    ``,
    `export type ${className}Internal = z.infer<typeof ${className}OutputSchema>;`,
    ``,
  ].join('\n');

  return {
    slug,
    outPath: join(SRC_SCHEMAS, ...segments) + '.ts',
    content,
  };
}

function main(): void {
  const args = process.argv.slice(2);
  const checkMode = args.includes('--check');
  const configPaths = args.filter((a) => a !== '--check');

  if (configPaths.length === 0) {
    console.error('Usage: generate-schema.ts [--check] <config.json> [<config.json> ...]');
    process.exit(1);
  }

  let hasErrors = false;

  for (const configPath of configPaths) {
    try {
      const { slug, outPath, content } = generateSchemaFile(configPath);

      if (checkMode) {
        if (!existsSync(outPath)) {
          console.error(`✗  ${slug}: ${outPath} does not exist. Run: npm run generate:schemas`);
          hasErrors = true;
          continue;
        }
        const existing = readFileSync(outPath, 'utf-8');
        if (existing !== content) {
          console.error(`✗  ${slug}: ${outPath} is out of sync. Run: npm run generate:schemas`);
          hasErrors = true;
        } else {
          console.log(`✓  ${slug}: up to date`);
        }
      } else {
        mkdirSync(dirname(outPath), { recursive: true });
        writeFileSync(outPath, content, 'utf-8');
        console.log(`Generated ${outPath}`);
      }
    } catch (err) {
      console.error(`Error processing ${configPath}: ${err instanceof Error ? err.message : err}`);
      hasErrors = true;
    }
  }

  if (hasErrors) process.exit(1);
}

// Only run when executed directly, not when imported by tests.
if (fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
