import { describe, it, expect } from 'vitest';
import { calculateFleschKincaidGrade } from '../../../src/features/readability.js';

describe('calculateFleschKincaidGrade', () => {
  it('should calculate FK grade for simple text', () => {
    const text = 'The cat sat on the mat. The dog ran away.';
    const grade = calculateFleschKincaidGrade(text);

    expect(grade).toBeLessThan(5);
    expect(typeof grade).toBe('number');
  });

  it('should handle empty text', () => {
    const grade = calculateFleschKincaidGrade('');
    expect(grade).toBe(0);
  });

  it('should calculate higher grade for complex text', () => {
    const simpleText = 'The cat sat.';
    const complexText = 'The mitochondria, known as the powerhouse of cellular respiration, facilitates biochemical processes.';

    const simpleGrade = calculateFleschKincaidGrade(simpleText);
    const complexGrade = calculateFleschKincaidGrade(complexText);

    expect(complexGrade).toBeGreaterThan(simpleGrade);
  });
});
