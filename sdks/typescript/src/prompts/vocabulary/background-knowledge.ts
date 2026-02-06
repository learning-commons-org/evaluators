import { loadPrompt } from '../../utils/prompts';

/**
 * Background knowledge prompt template
 * Loaded from: prompts/vocabulary/background-knowledge.txt
 */
const BACKGROUND_KNOWLEDGE_TEMPLATE = loadPrompt('vocabulary/background-knowledge.txt');

/**
 * Generate the background knowledge prompt for a given text and grade level
 */
export function getBackgroundKnowledgePrompt(text: string, grade: string): string {
  return BACKGROUND_KNOWLEDGE_TEMPLATE
    .replace('{grade}', grade)
    .replace('{text}', text);
}
