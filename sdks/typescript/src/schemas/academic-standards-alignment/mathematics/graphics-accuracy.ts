// GENERATED — do not edit directly.
// Source: ../../evals/academic-standards-alignment/mathematics/graphics-accuracy/output_schema.json
//         ../../evals/academic-standards-alignment/mathematics/graphics-accuracy/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type GraphicsAccuracyInput = {
  /** Local file path or http(s) URL to the math visual under review. Supported: PNG, JPEG, WEBP (detected by file signature, not by extension). At most 10 MB. */
  "image": string;
  /** The specification the image is checked against. Either a claim about what the image shows ("The chart shows 12 apples.") or a question with its expected answer in the form `Question: "<question>" The answer is <answer>.` */
  "claim": string;
};

// prettier-ignore
export const GraphicsAccuracyOutputSchema = z.object({ "observed": z.string().describe("Describe only what is literally in the image. For every countable feature relevant to the specification (dots, bars, sides, vertices, tiles, segments, arrows, cubes, petals), enumerate them with explicit labels and commit to a single integer count."), "analysis": z.string().describe("Derive, from scratch, the value or result the image yields for the specification's question, using the counts and structure in observed together with any facts the question states in words. Do not fault the image for omitting facts the question supplies in text. Show the computation. No appeals to memorized knowledge. No hedging language (\"plausible\", \"appears to match\", \"consistent as a possibility\")."), "errors": z.array(z.string()).describe("Every way the image fails to show what the specification requires: what the image shows, and what was required instead. If the derivation could not be completed, what in the image could not be read or resolved. Empty when the image is correct."), "correction": z.string().describe("What the image actually shows — the value or result your derivation produced — independently of the specification. If derivation is incomplete, say \"derivation incomplete\"."), "basis": z.enum(["supported","contradicted","unverified"]).describe("supported: derivation completed and X equals Y. contradicted: derivation completed and X differs from Y. unverified: the derivation could not be completed from the image together with the question's stated facts, or hedging was needed; the image was not shown wrong, but not shown right either. Consistency alone is never \"supported\"."), "is_correct": z.boolean().describe("Set LAST, after writing the explicit \"The image yields X; the specification states Y; therefore is_correct = ___\" sentence in your analysis. True only when basis is \"supported\"; false for \"contradicted\" and \"unverified\".") }).strict();

export type GraphicsAccuracyResult = z.infer<typeof GraphicsAccuracyOutputSchema>;
