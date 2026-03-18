export interface AlignmentIteration {
  text: string;
  glaBand: string;
  reasoning: string;
}

export interface AlignmentResult {
  originalText: string;
  targetGrade: string;
  originalGlaBand: string;
  finalGlaBand: string;
  alignedText: string;
  rationale: string;
  iterations: AlignmentIteration[];
}

const GRADE_BANDS: [number, number, string][] = [
  [0,  1,  'K-1'],
  [2,  3,  '2-3'],
  [4,  5,  '4-5'],
  [6,  8,  '6-8'],
  [9,  10, '9-10'],
  [11, 12, '11-CCR'],
];

export function gradeToBand(grade: number): string {
  for (const [lo, hi, band] of GRADE_BANDS) {
    if (grade >= lo && grade <= hi) return band;
  }
  return '11-CCR';
}

export interface AgentConfig {
  /** Falls back to ANTHROPIC_API_KEY env var */
  anthropicApiKey?: string;
  /** Falls back to OPENAI_API_KEY env var */
  openaiApiKey?: string;
  /** Falls back to GOOGLE_API_KEY env var */
  googleApiKey?: string;
  /** Model to use for orchestration (default: claude-opus-4-6) */
  model?: string;
  /** Maximum agent turns before stopping (default: 10) */
  maxTurns?: number;
}
