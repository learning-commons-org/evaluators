import type { EvaluatorFamily } from './family.js';
import { QTC_FAMILY } from './qtc.js';
import { STANDARDS_FAMILY } from './standards.js';

const FAMILIES: EvaluatorFamily[] = [QTC_FAMILY, STANDARDS_FAMILY];

/** All evaluator families available to the batch tool. */
export function getFamilies(): EvaluatorFamily[] {
  return [...FAMILIES];
}

/** Look up a family by id, or throw with the list of valid ids. */
export function getFamily(id: string): EvaluatorFamily {
  const family = FAMILIES.find((f) => f.id === id);
  if (!family) {
    throw new Error(
      `Unknown evaluator family: "${id}". Available: ${FAMILIES.map((f) => f.id).join(', ')}`,
    );
  }
  return family;
}
