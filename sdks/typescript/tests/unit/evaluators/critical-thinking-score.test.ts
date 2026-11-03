/**
 * The median the Critical Thinking prompt asks the model to form.
 *
 * Odd count takes the middle rating. Even count takes the level halfway between the two
 * middle ratings, and the higher level when halfway falls between two. A missing
 * indicator is not a rating.
 */
import { describe, expect, it } from 'vitest';

export const LEVELS = ['not_evident', 'exploring', 'analyzing', 'integrating', 'extending'] as const;

export function medianRating(ratings: readonly string[]): string {
  const ordered = ratings
    .map((rating) => LEVELS.indexOf(rating as (typeof LEVELS)[number]))
    .sort((left, right) => left - right);
  const middle = Math.floor(ordered.length / 2);
  if (ordered.length % 2) return LEVELS[ordered[middle]];
  return LEVELS[Math.ceil((ordered[middle - 1] + ordered[middle]) / 2)];
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

  it('takes the midpoint of four ratings', () => {
    expect(medianRating(['exploring', 'exploring', 'integrating', 'integrating'])).toBe(
      'analyzing',
    );
    expect(medianRating(['not_evident', 'not_evident', 'extending', 'extending'])).toBe(
      'analyzing',
    );
  });

  it('rounds the midpoint of four ratings up', () => {
    expect(medianRating(['exploring', 'exploring', 'extending', 'extending'])).toBe('integrating');
    expect(medianRating(['not_evident', 'not_evident', 'integrating', 'integrating'])).toBe(
      'analyzing',
    );
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
