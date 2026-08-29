// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/vocabulary-complexity/output_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

// prettier-ignore
export const VocabularyComplexityOutputSchema = z.object({ "tier_2_words": z.string().describe("List of Tier 2 words: words commonly used in academic settings, more complex than colloquial or everyday language, often with multiple meanings."), "tier_3_words": z.string().describe("List of Tier 3 words: overly academic or domain-specific words."), "archaic_words": z.string().describe("List of archaic words, or common words used in an archaic way, not commonly used in modern conversational language."), "other_complex_words": z.string().describe("All other words that can increase complexity of the text (e.g., idioms, unfamiliar proper nouns that function as vocabulary)."), "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The vocabulary complexity level of the text."), "reasoning": z.string().describe("A detailed explanation of the rating. Grades 3-4 reference density and cumulative effect, contextual scaffolding, abstract vs. concrete vocabulary, conceptual load, and the provided student background knowledge; other grades reference the annotation guide and rubric.") }).strict();

export type VocabularyComplexityResult = z.infer<typeof VocabularyComplexityOutputSchema>;
