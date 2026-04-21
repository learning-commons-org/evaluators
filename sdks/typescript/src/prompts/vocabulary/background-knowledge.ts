import BACKGROUND_KNOWLEDGE_TEMPLATE from '../../../../../evals/literacy/qualitative-text-complexity/vocabulary/background-knowledge.txt';

/**
 * Generate the background knowledge prompt for a given text and grade level
 */
export function getBackgroundKnowledgePrompt(text: string, grade: string): string {
  return BACKGROUND_KNOWLEDGE_TEMPLATE
    .replaceAll('{grade}', grade)
    .replaceAll('{text}', text);
}
