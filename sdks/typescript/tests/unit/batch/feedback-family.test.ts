import { describe, it, expect, vi } from 'vitest';
import { FEEDBACK_FAMILY } from '../../../src/batch/families/feedback.js';
import { getFamilies, getFamily } from '../../../src/batch/families/registry.js';
import { validateRequiredColumns, normalizeRow } from '../../../src/batch/families/family.js';
import { renderOutputs } from '../../../src/batch/output.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { BatchOutput, BatchResult } from '../../../src/batch/types.js';
import type { LLMProvider, LLMResponse } from '../../../src/providers/base.js';

const STUDENT_TEXT = 'My dog is brown. He runs fast.';
const FEEDBACK_TEXT = 'Try adding a topic sentence.';

const RESPONSE: LLMResponse<{ quality_score: number; reasoning: string }> = {
  data: { quality_score: 1, reasoning: 'Names a concrete next step.' },
  model: 'gpt-5.4-2026-03-05',
  usage: { inputTokens: 9, outputTokens: 3 },
  latencyMs: 5,
};

function llmProvider(): LLMProvider {
  return {
    label: 'openai:gpt-5.4-2026-03-05',
    generateStructured: vi.fn().mockResolvedValue(RESPONSE),
    generateText: vi.fn(),
  };
}

describe('the feedback family is selectable', () => {
  it('is registered', () => {
    expect(getFamilies().map((f) => f.id)).toContain(FEEDBACK_FAMILY.id);
    expect(getFamily('feedback')).toBe(FEEDBACK_FAMILY);
  });

  it('has all seven criteria as members', () => {
    expect(FEEDBACK_FAMILY.members).toHaveLength(7);
    expect(FEEDBACK_FAMILY.members.map((m) => m.id).every((id) => id.startsWith('feedback.'))).toBe(
      true,
    );
  });

  it('requires the two text columns', () => {
    expect(FEEDBACK_FAMILY.columns.map((c) => c.name)).toEqual(['student_text', 'feedback_text']);
    // Both directions: each column is required, so neither can be quietly optional.
    expect(() => validateRequiredColumns(FEEDBACK_FAMILY, ['student_text'])).toThrow(
      /feedback_text/,
    );
    expect(() => validateRequiredColumns(FEEDBACK_FAMILY, ['feedback_text'])).toThrow(
      /student_text/,
    );
    expect(() =>
      validateRequiredColumns(FEEDBACK_FAMILY, ['student_text', 'feedback_text']),
    ).not.toThrow();
  });

  it('asks only for the key its members declare', () => {
    // Read off each evaluator's contract rather than restated here, so a contract that
    // moves to another vendor changes this without a code edit.
    expect(FEEDBACK_FAMILY.requiredKeys(FEEDBACK_FAMILY.members.map((m) => m.id))).toEqual([
      Provider.OpenAI,
    ]);
  });

  it('honours a model override for the key it needs', () => {
    const keys = FEEDBACK_FAMILY.requiredKeys([], {
      provider: Provider.Google,
      model: 'gemini-3-flash-preview',
    });

    expect(keys).toEqual([Provider.Google]);
  });
});

describe('the feedback family runs a row', () => {
  const columns = { student_text: STUDENT_TEXT, feedback_text: FEEDBACK_TEXT };
  const row = normalizeRow({ rowIndex: 0, columns, originalRow: columns }, FEEDBACK_FAMILY);

  it('passes both texts to the evaluator and reports the verdict', async () => {
    const provider = llmProvider();
    const runner = FEEDBACK_FAMILY.createRunner({ llmProvider: provider, telemetry: false });
    const memberId = FEEDBACK_FAMILY.members[0].id;

    const outcome = await runner.runTask(row, memberId);

    const prompts = vi
      .mocked(provider.generateStructured)
      .mock.calls.flatMap((c) => c[0].messages.map((m) => m.content))
      .join('\n');
    expect(prompts).toContain(STUDENT_TEXT);
    expect(prompts).toContain(FEEDBACK_TEXT);

    // readOutcome stringifies, so the integer verdict arrives as '1'.
    expect(outcome).toEqual({ score: '1', reasoning: 'Names a concrete next step.' });
  });

  it('reports a zero verdict rather than treating it as absent', async () => {
    const provider = llmProvider();
    vi.mocked(provider.generateStructured).mockResolvedValue({
      ...RESPONSE,
      data: { quality_score: 0, reasoning: 'No next step given.' },
    });
    const runner = FEEDBACK_FAMILY.createRunner({ llmProvider: provider, telemetry: false });

    const outcome = await runner.runTask(row, FEEDBACK_FAMILY.members[0].id);

    // '0' is a verdict. Rendering it blank would read as "not evaluated".
    expect(outcome.score).toBe('0');
  });

  it('names an unknown member rather than failing obscurely', () => {
    const runner = FEEDBACK_FAMILY.createRunner({ llmProvider: llmProvider(), telemetry: false });

    expect(runner.runTask(row, 'feedback.ela_writing.not_a_member')).rejects.toThrow(
      /Unknown feedback evaluator/,
    );
  });

  it('builds one evaluator per member, not one per row', async () => {
    // Each construction validates credentials and builds a provider adapter, so a runner
    // that rebuilt per row would pay that on every row of a 50-row batch.
    const provider = llmProvider();
    const runner = FEEDBACK_FAMILY.createRunner({ llmProvider: provider, telemetry: false });
    const memberId = FEEDBACK_FAMILY.members[0].id;

    const secondRow = normalizeRow(
      { rowIndex: 1, columns, originalRow: columns },
      FEEDBACK_FAMILY,
    );
    await runner.runTask(row, memberId);
    await runner.runTask(secondRow, memberId);

    const instances = (runner as unknown as { instances: Map<string, unknown> }).instances;
    expect(instances.size).toBe(1);
  });

  it('runs only the members selected', () => {
    const [first] = FEEDBACK_FAMILY.members;
    const runner = FEEDBACK_FAMILY.createRunner(
      { llmProvider: llmProvider(), telemetry: false },
      [first.id],
    );

    expect(runner.members.map((m) => m.id)).toEqual([first.id]);
  });
});

describe('a family without a report of its own emits no HTML', () => {
  // A report is designed around what a family's verdict means, so a family without one
  // gets CSV and JSON — which are family-agnostic — rather than a report built for other
  // data. Feedback scores 0/1 with no grade, and the text-complexity report averages a
  // four-point scale and charts grade bands.
  function bundleFor(familyId: string) {
    const result: BatchResult = {
      rowIndex: 0,
      text: STUDENT_TEXT,
      gradeLevel: '',
      evaluatorId: FEEDBACK_FAMILY.members[0].id,
      status: 'success',
      score: '1',
      reasoning: 'ok',
      processingTimeMs: 1,
      columns: { student_text: STUDENT_TEXT, feedback_text: FEEDBACK_TEXT },
      originalRow: { student_text: STUDENT_TEXT, feedback_text: FEEDBACK_TEXT },
    };
    const output: BatchOutput = {
      results: [result],
      summary: {
        totalTasks: 1,
        successful: 1,
        failed: 0,
        durationMs: 1,
        resultsPerEvaluator: {},
      },
    };
    return renderOutputs(familyId, output, {
      csvPath: 'in.csv',
      groupId: familyId,
      reportId: 'r1',
      generatedAt: new Date('2026-08-29T00:00:00Z'),
      totalInputRows: 1,
    });
  }

  it('gives the feedback family csv and json but no html', () => {
    const bundle = bundleFor(FEEDBACK_FAMILY.id);

    expect(bundle.html).toBeUndefined();
    expect(bundle.csv).not.toBe('');
    expect(JSON.parse(bundle.json).results).toHaveLength(1);
  });

  it('still carries both texts and the verdict in the csv', () => {
    const csv = bundleFor(FEEDBACK_FAMILY.id).csv;

    expect(csv).toContain(STUDENT_TEXT);
    expect(csv).toContain(FEEDBACK_TEXT);
    expect(csv.split('\n')[0]).toContain('student_text');
  });

  it('still gives the text-complexity family its report', () => {
    expect(bundleFor('text-complexity').html).toBeTypeOf('string');
  });
});
