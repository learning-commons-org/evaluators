export interface PromptRenderers {
  getSystemPrompt(inputs: Record<string, string>): string;
  getUserPrompt(inputs: Record<string, string>): string;
}

/**
 * Build prompt renderers over a fixed set of placeholder names.
 *
 * Only declared placeholders are substituted, so an undeclared `{token}` in a template is
 * left alone rather than silently filled from whatever the caller happened to pass. The
 * names come from the contract; resolving which step declares them is the caller's job.
 */
export function createPromptRenderers(
  systemTemplate: string,
  userTemplate: string,
  placeholderKeys: readonly string[],
): PromptRenderers {
  const applyPlaceholders = (template: string, inputs: Record<string, string>): string =>
    placeholderKeys.reduce(
      (text, key) => (key in inputs ? text.replaceAll(`{${key}}`, inputs[key]) : text),
      template,
    );

  return {
    getSystemPrompt: (inputs) => applyPlaceholders(systemTemplate, inputs),
    getUserPrompt: (inputs) => applyPlaceholders(userTemplate, inputs),
  };
}
