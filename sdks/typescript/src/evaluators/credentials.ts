/**
 * Working out which credentials an evaluator needs, from what its contract declares.
 *
 * Two kinds, with different behaviour under a model override. LLM keys follow the
 * providers the evaluator's steps use, so an override replaces them — it changes which
 * model runs. Non-LLM credentials are declared per entry and an override never touches
 * them, because it does not change which services the evaluator calls.
 */

/** As much of a contract as credential derivation reads. */
export interface CredentialDeclaringConfig {
  // `id` is required only so this is not a weak type: an entry shape with nothing but
  // optional properties would reject a contract that declares no credentials at all.
  preprocessing?: ReadonlyArray<{ id: string; required_credentials?: readonly string[] }>;
  steps: ReadonlyArray<{
    id: string;
    optional?: boolean;
    required_credentials?: readonly string[];
  }>;
}

/**
 * The non-LLM credentials a contract declares, across every entry that can run.
 *
 * An optional step is excluded: it runs only when a caller opts in, so requiring its
 * credential at construction would demand a key for a call that never happens.
 */
export function declaredCredentials(config: CredentialDeclaringConfig): readonly string[] {
  const entries = [
    ...(config.preprocessing ?? []),
    ...config.steps.filter((step) => !step.optional),
  ];

  return [...new Set(entries.flatMap((entry) => entry.required_credentials ?? []))];
}

/**
 * The config field carrying a canonical credential, per §2.1's mechanical casing map.
 *
 * A formula rather than a lookup table: `openai_api_key` is `openaiApiKey`, and a
 * provider added later needs no entry anywhere.
 */
export function configFieldFor(canonicalKey: string): string {
  return canonicalKey.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}
