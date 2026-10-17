/**
 * The median the Critical Thinking prompt asks the model to form.
 *
 * Odd count takes the middle rating. Even count takes the higher of the two middle
 * ratings. A missing indicator is not a rating.
 */
import { describe, expect, it } from 'vitest';

export const LEVELS = ['not_evident', 'exploring', 'analyzing', 'integrating', 'extending'] as const;

export function medianRating(ratings: readonly string[]): string {
  const ordered = [...ratings].sort(
    (left, right) =>
      LEVELS.indexOf(left as (typeof LEVELS)[number]) -
      LEVELS.indexOf(right as (typeof LEVELS)[number]),
  );
  return ordered[Math.floor(ordered.length / 2)];
}

export function presentRatings(
  indicators: Record<string, { rating: string } | undefined>,
): string[] {
  return Object.values(indicators).flatMap((indicator) => (indicator ? [indicator.rating] : []));
}

describe('critical thinking score', () => {
  it('takes the middle of five ratings', () => {
    expect(
      medianRating(['not_evident', 'exploring', 'analyzing', 'integrating', 'extending']),
    ).toBe('analyzing');
  });

  it('rounds four ratings up', () => {
    expect(medianRating(['exploring', 'exploring', 'analyzing', 'analyzing'])).toBe('analyzing');
  });

  it('leaves equal ratings unchanged', () => {
    expect(medianRating(['integrating', 'integrating', 'integrating', 'integrating'])).toBe(
      'integrating',
    );
  });

  it('skips an indicator the model left out', () => {
    const ratings = presentRatings({
      evidence_strength: { rating: 'exploring' },
      counterarguments: { rating: 'exploring' },
      facts_over_opinions: { rating: 'analyzing' },
      drawing_conclusions: { rating: 'analyzing' },
    });
    expect(ratings).toHaveLength(4);
    expect(medianRating(ratings)).toBe('analyzing');
  });
});
