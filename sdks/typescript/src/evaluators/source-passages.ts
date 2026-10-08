import type { DeclaredFieldSchema, DeclaredInputSchema } from './inputs.js';

/** One passage a caller passes. `title` and `author` are optional; `text` is not. */
export interface SourcePassageInput {
  title?: string;
  author?: string;
  text: string;
}

/** True when this caller field is an array of `SourcePassage`. */
export function isSourcePassageField(schema: DeclaredInputSchema, field: string): boolean {
  return isSourcePassageSpec(schema.properties[field]);
}

function isSourcePassageSpec(spec: DeclaredFieldSchema | undefined): boolean {
  return spec?.type === 'array' && spec.items?.$ref === '#/$defs/SourcePassage';
}

/**
 * The markdown `{sources}` already uses.
 *
 * List order is the source number. The first item is Source 1. Nothing here sorts or
 * renumbers. A passage with no title and no author still keeps its number, because a
 * student can cite it that way.
 */
export function renderSourcePassages(passages: readonly SourcePassageInput[]): string {
  return passages
    .map((passage, index) => `${heading(index + 1, passage)}\n\n${passage.text}`)
    .join('\n\n');
}

function heading(number: number, passage: SourcePassageInput): string {
  const title = passage.title;
  const author = passage.author;
  if (title && author) return `### Source ${number}: ${title} — by ${author}`;
  if (title) return `### Source ${number}: ${title}`;
  return `### Source ${number}`;
}
