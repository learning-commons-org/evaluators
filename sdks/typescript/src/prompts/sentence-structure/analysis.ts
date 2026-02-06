import { loadPrompt } from '../../utils/prompts';

/**
 * System prompt for sentence grammatical analysis
 * Loaded from: prompts/sentence-structure/analysis-system.txt
 */
const SYSTEM_PROMPT_ANALYSIS_TEMPLATE = loadPrompt('sentence-structure/analysis-system.txt');

/**
 * Get the system prompt for sentence grammatical analysis
 * @returns The system prompt
 */
export function getSystemPromptAnalysis(): string {
  return SYSTEM_PROMPT_ANALYSIS_TEMPLATE;
}

/**
 * User prompt template for sentence grammatical analysis
 * Loaded from: prompts/sentence-structure/analysis-user.txt
 */
const USER_PROMPT_ANALYSIS_TEMPLATE = loadPrompt('sentence-structure/analysis-user.txt');

/**
 * Generate the user prompt for sentence analysis
 * @param text - The text to analyze
 * @param groundTruthCounts - Ground truth counts from readability metrics
 * @returns The formatted user prompt
 */
export function getUserPromptAnalysis(text: string, groundTruthCounts: string): string {
  return USER_PROMPT_ANALYSIS_TEMPLATE
    .replace('{text}', text)
    .replace('{ground_truth_counts}', groundTruthCounts);
}
