import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, it, expect, vi } from 'vitest';
import { STANDARDS_FAMILY } from '../../../src/batch/families/standards.js';
import { QTC_FAMILY } from '../../../src/batch/families/qtc.js';
import { Provider } from '../../../src/batch/index.js';
import { Jurisdiction } from '../../../src/knowledge-graph/index.js';
import type { FamilyRow } from '../../../src/batch/families/family.js';
import {
  GradeLevelAppropriatenessEvaluator,
  SentenceStructureEvaluator,
  VocabularyComplexityEvaluator,
} from '../../../src/evaluators/index.js';

const MEMBER = 'academic_standards_alignment.mathematics.math_standards_alignment';

describe('STANDARDS_FAMILY.requiredKeys', () => {
  it('requires the Learning Commons key plus Anthropic by default', () => {
    expect(STANDARDS_FAMILY.requiredKeys([MEMBER])).toEqual([Provider.Anthropic, 'learning-commons']);
  });

  it('swaps in the override provider (Learning Commons key still required)', () => {
    expect(
      STANDARDS_FAMILY.requiredKeys([MEMBER], { provider: Provider.Google, model: 'gemini-x' }),
    ).toEqual([Provider.Google, 'learning-commons']);
  });
});

describe('QTC_FAMILY.requiredKeys — member selection', () => {
  it('demands both keys when every member runs', () => {
    expect(new Set(QTC_FAMILY.requiredKeys([]))).toEqual(new Set([Provider.Google, Provider.OpenAI]));
  });

  // Demanding a key the run never uses blocks an otherwise valid non-interactive run.
  it.each([
    [GradeLevelAppropriatenessEvaluator.metadata.id, [Provider.Google]],
    [SentenceStructureEvaluator.metadata.id, [Provider.OpenAI]],
    [VocabularyComplexityEvaluator.metadata.id, [Provider.Google, Provider.OpenAI]],
  ])('asks only for the keys %s actually uses', (memberId, expected) => {
    expect(new Set(QTC_FAMILY.requiredKeys([memberId]))).toEqual(new Set(expected));
  });

  it('unions the keys across a mixed selection', () => {
    expect(new Set(QTC_FAMILY.requiredKeys([GradeLevelAppropriatenessEvaluator.metadata.id, SentenceStructureEvaluator.metadata.id]))).toEqual(
      new Set([Provider.Google, Provider.OpenAI]),
    );
  });

  it('still collapses to the override provider alone', () => {
    expect(
      QTC_FAMILY.requiredKeys([VocabularyComplexityEvaluator.metadata.id], { provider: Provider.Anthropic, model: 'claude-x' }),
    ).toEqual([Provider.Anthropic]);
  });
});

describe('STANDARDS_FAMILY.createRunner — provider-key forwarding', () => {
  const base = { learningCommonsApiKey: 'p' };

  it('constructs with a Google model override when the Google key is forwarded', () => {
    expect(() =>
      STANDARDS_FAMILY.createRunner({
        ...base,
        googleApiKey: 'g',
        modelOverride: { provider: Provider.Google, model: 'gemini-x' },
      }),
    ).not.toThrow();
  });

  it('throws when the override provider key is absent — proving the key path is actually wired', () => {
    // If StandardsRunner failed to forward googleApiKey, this would throw regardless;
    // the paired test above (which forwards it and does NOT throw) is what makes this meaningful.
    expect(() =>
      STANDARDS_FAMILY.createRunner({
        ...base,
        modelOverride: { provider: Provider.Google, model: 'gemini-x' },
      }),
    ).toThrow(/google/i);
  });
});

describe('STANDARDS_FAMILY.runTask', () => {
  /** What `evaluate()` resolves to: the payload inside the shared envelope. */
  const ALIGNMENT = {
    evaluator: 'math-standards-alignment',
    result: {
      statementCode: '3.MD.C.7.d',
      learningComponents: [
        { identifier: 'lc-1', description: 'a', reasoning: 'r', aligned: true, feedback: '' },
        { identifier: 'lc-2', description: 'b', reasoning: 'r', aligned: false, feedback: 'revise' },
      ],
      alignedCount: 1,
      totalCount: 2,
    },
    metadata: {
      model: 'anthropic:claude-x',
      processingTimeMs: 1,
      tokenUsage: { inputTokens: 10, outputTokens: 20 },
    },
  };

  /** The runner builds a real evaluator; swap it for a stub so no network is needed. */
  function runnerWithStub(evaluate: ReturnType<typeof vi.fn>) {
    const runner = STANDARDS_FAMILY.createRunner({ learningCommonsApiKey: 'p', anthropicApiKey: 'a', telemetry: false });
    (runner as unknown as { evaluator: { evaluate: unknown } }).evaluator = { evaluate };
    return runner;
  }

  function row(columns: Record<string, string>): FamilyRow {
    return { rowIndex: 2, columns, originalRow: columns };
  }

  it('reports aligned/total as the score and carries the full verdict as payload', async () => {
    const evaluate = vi.fn().mockResolvedValue(ALIGNMENT);
    const outcome = await runnerWithStub(evaluate).runTask(
      row({ question: 'What is the area?', statementCode: '3.MD.C.7.d', jurisdiction: Jurisdiction.Utah }),
      MEMBER,
    );

    expect(evaluate).toHaveBeenCalledWith({
      question: 'What is the area?',
      statementCode: '3.MD.C.7.d',
      jurisdiction: Jurisdiction.Utah,
    });
    expect(outcome.score).toBe('1/2');
    expect(outcome.reasoning).toContain('1 of 2');
    expect(outcome.payload).toMatchObject({
      question: 'What is the area?',
      jurisdiction: Jurisdiction.Utah,
      alignedCount: 1,
      totalCount: 2,
    });
    // The payload is written verbatim to results.json, so spreading the envelope instead of
    // its `result` would add `evaluator`/`metadata` columns to a partner-facing artefact.
    expect(Object.keys(outcome.payload as object).sort()).toEqual([
      'alignedCount',
      'jurisdiction',
      'learningComponents',
      'question',
      'statementCode',
      'totalCount',
    ]);
  });

  it('defaults an absent jurisdiction to Multi-State', async () => {
    const evaluate = vi.fn().mockResolvedValue(ALIGNMENT);
    await runnerWithStub(evaluate).runTask(row({ question: 'q', statementCode: '3.MD.C.7.d' }), MEMBER);

    expect(evaluate).toHaveBeenCalledWith({
      question: 'q',
      statementCode: '3.MD.C.7.d',
      jurisdiction: Jurisdiction.MultiState,
    });
  });

  it('rejects an unrecognised jurisdiction instead of passing it to the Knowledge Graph', async () => {
    const evaluate = vi.fn();
    await expect(
      runnerWithStub(evaluate).runTask(row({ question: 'q', statementCode: 'x', jurisdiction: 'Utahh' }), MEMBER),
    ).rejects.toThrow(/Invalid jurisdiction "Utahh"/);
    expect(evaluate).not.toHaveBeenCalled();
  });
});

describe('the standards report reads the fields the formatter emits', () => {
  // The report filtered and displayed `it.grade`; the formatter emits `gradeLevel`. Since
  // `it.grade` was always undefined, selecting a grade filtered *everything* out rather
  // than filtering. Nothing failed because the filter is browser JS in a template, which
  // no test executes — so this asserts on the template text, as the ordering check does.
  const template = readFileSync(
    join(process.cwd(), 'src/batch/families/standards-report.html'),
    'utf-8',
  );

  it('never reads a bare `grade` off a row', () => {
    expect(template).not.toMatch(/\bit\.grade\b/);
  });

  it('reads gradeLevel, which is what standards-output.ts writes', () => {
    expect(template).toContain('it.gradeLevel');

    const formatter = readFileSync(
      join(process.cwd(), 'src/batch/families/standards-output.ts'),
      'utf-8',
    );
    expect(formatter, 'the formatter must still emit that field').toContain('gradeLevel:');
  });
});
