export type VariantLevel = 'below' | 'at' | 'above';

export interface TextVariant {
  level: VariantLevel;
  grade: string;
  text: string;
  rationale: string;
}

export interface DifferentiatedSet {
  originalText: string;
  targetGrade: string;
  below: TextVariant;
  at: TextVariant;
  above: TextVariant;
}

export interface AgentConfig {
  /** Falls back to ANTHROPIC_API_KEY env var */
  anthropicApiKey?: string;
  /** Falls back to OPENAI_API_KEY env var */
  openaiApiKey?: string;
  /** Falls back to GOOGLE_API_KEY env var */
  googleApiKey?: string;
  /** Maximum agent turns before stopping (default: 40) */
  maxTurns?: number;
}
