/** Structural subset of an evaluator config.json needed to render prompts. */
interface PromptConfig {
  evaluator: { id: string };
  steps: Array<{ id: string; prompt: { placeholders: Record<string, unknown> } }>;
}

export interface PromptRenderers {
  getSystemPrompt(inputs: Record<string, string>): string;
  getUserPrompt(inputs: Record<string, string>): string;
}

/**
 * Build prompt renderers for a single-step evaluator. The placeholder set is
 * driven by config.json, not hardcoded: only keys declared in the step's
 * `prompt.placeholders` are substituted (as `{key}`) into the templates.
 */
export function createPromptRenderers(
  systemTemplate: string,
  userTemplate: string,
  config: PromptConfig,
): PromptRenderers {
  // Step ID convention: "evaluate_{slug}" where slug is the last segment of evaluator.id.
  const stepId = `evaluate_${config.evaluator.id.split('.').pop()}`;
  const step = config.steps.find(s => s.id === stepId);
  if (!step) throw new Error(`Step "${stepId}" not found in ${config.evaluator.id} config.json`);
  const placeholderKeys = Object.keys(step.prompt.placeholders);

  const applyPlaceholders = (template: string, inputs: Record<string, string>): string =>
    placeholderKeys.reduce(
      (text, key) => key in inputs ? text.replaceAll(`{${key}}`, inputs[key]) : text,
      template,
    );

  return {
    getSystemPrompt: (inputs) => applyPlaceholders(systemTemplate, inputs),
    getUserPrompt: (inputs) => applyPlaceholders(userTemplate, inputs),
  };
}
