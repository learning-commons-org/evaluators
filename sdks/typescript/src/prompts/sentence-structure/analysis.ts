import SYSTEM_PROMPT_ANALYSIS_TEMPLATE from '../../../../../evals/student-facing-text/ela-reading/sentence-structure/analysis-system.txt';
import USER_PROMPT_ANALYSIS_TEMPLATE from '../../../../../evals/student-facing-text/ela-reading/sentence-structure/analysis-user.txt';

/**
 * Get the system prompt for sentence grammatical analysis
 * @returns The system prompt
 */
export function getSystemPromptAnalysis(): string {
  return SYSTEM_PROMPT_ANALYSIS_TEMPLATE;
}

/**
 * Generate the user prompt for sentence analysis
 * @param text - The text to analyze
 * @param groundTruthCounts - Ground truth counts from readability metrics
 * @returns The formatted user prompt
 */
export function getUserPromptAnalysis(text: string, groundTruthCounts: string): string {
  return USER_PROMPT_ANALYSIS_TEMPLATE
    .replaceAll('{text}', text)
    .replaceAll('{ground_truth_counts}', groundTruthCounts);
}
