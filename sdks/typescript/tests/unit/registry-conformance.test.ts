import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

import {
  GradeLevelAppropriatenessEvaluator,
  BackgroundKnowledgeDemandsEvaluator,
  MeaningDirectnessEvaluator,
  OrganizationalStructureEvaluator,
  PurposeClarityEvaluator,
  ReferenceKnowledgeDemandsEvaluator,
  SentenceStructureEvaluator,
  VocabularyComplexityEvaluator,
  MathStandardsAlignmentEvaluator,
} from '../../src/evaluators/index.js';
import { VALIDATION_LIMITS } from '../../src/evaluators/base.js';
import { readOutcome } from '../../src/schemas/outcome.js';
import type { EvaluationResult } from '../../src/schemas/index.js';
import {
  formatAsHTML,
  getFamilies,
  type BatchOutput,
  type ReportMeta,
} from '../../src/batch/index.js';

/** Records every (provider, model) an evaluator asks for at construction. */
const constructed: Array<{ type: string; model: string }> = [];

vi.mock('../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => {
      constructed.push({ type: config.type, model: config.model });
      return {
        label: `${config.type}:${config.model}`,
        generateStructured: vi.fn(),
        generateText: vi.fn(),
      };
    }),
  };
});

/**
 * Asserts each evaluator against the contract it claims to implement.
 *
 * Nearly every defect this suite exists to catch has the same shape: a registry fact
 * was copied into SDK code, the registry moved, and the copy silently kept working
 * with the old value. Reading the contract at test time is the only way to notice.
 *
 * The contract directory is derived from `metadata.id`, never listed: dots become path
 * separators and underscores become hyphens. So an evaluator added later is covered the
 * moment it appears in EVALUATORS below.
 */

const EVALUATORS = [
  GradeLevelAppropriatenessEvaluator,
  BackgroundKnowledgeDemandsEvaluator,
  MeaningDirectnessEvaluator,
  OrganizationalStructureEvaluator,
  PurposeClarityEvaluator,
  ReferenceKnowledgeDemandsEvaluator,
  SentenceStructureEvaluator,
  VocabularyComplexityEvaluator,
  MathStandardsAlignmentEvaluator,
];

// ---------------------------------------------------------------------------
// Known gaps
//
// Each entry is a divergence that exists today and is scheduled to be closed —
// a record of work outstanding, never a decision that the divergence is correct.
//
// Entries are self-cleaning: for an allowlisted evaluator the assertion is inverted,
// so closing the gap fails the test until the entry is deleted. An allowlist that
// silently outlives its gap is how this class of bug survives in the first place.
// ---------------------------------------------------------------------------

const GLA_ID = GradeLevelAppropriatenessEvaluator.metadata.id;
const MATH_ID = MathStandardsAlignmentEvaluator.metadata.id;
const BKD_ID = BackgroundKnowledgeDemandsEvaluator.metadata.id;
const MD_ID = MeaningDirectnessEvaluator.metadata.id;
const SENTENCE_ID = SentenceStructureEvaluator.metadata.id;

/** Evaluators whose constructed models or temperatures differ from their contract. */
const MODEL_GAPS = new Set<string>([
  // Ships gemini-2.5-pro @ 0.25; the contract declares gemini-3.6-flash @ 1.
  GLA_ID,
]);

/** Evaluators whose `supportedGrades` does not describe their declared inputs. */
const GRADE_GAPS = new Set<string>([
  // `supported_grades` here describes what `evaluateByGradeLevel` accepts — a bulk
  // capability outside the one-to-one contract, whose shape is still open (Q-12).
  // `evaluate()` itself takes no grade, and the input schema correctly declares none.
  MATH_ID,
]);

/**
 * `evaluatorId::field` pairs whose declared bounds the SDK does not enforce.
 *
 * §4.1 requires each text input to be validated against its own registry-declared
 * limits; the SDK applies one global pair to every input, so a contract asking for
 * anything narrower is silently ignored.
 */
const LIMIT_GAPS = new Set<string>([
  // Declare `text.minLength: 10`; the SDK enforces 1, so it accepts input these
  // contracts reject. The other four ela-reading evaluators declare 1 and agree.
  `${GLA_ID}::text`,
  `${BKD_ID}::text`,
  `${MD_ID}::text`,
  `${SENTENCE_ID}::text`,
]);

/**
 * Inputs the shared text-validation path does not govern, so the check below cannot
 * speak for them.
 *
 * `statementCode` is an identifier with its own declared bound rather than prose, and
 * nothing enforces it — a real gap, but not one this comparison can observe: it
 * measures the declared bounds against the SDK's single global pair, which would keep
 * differing even after per-field enforcement landed, so an entry here could never
 * self-clean. Enforcement is verified by calling the evaluator, which becomes uniform
 * once inputs are named.
 *
 * The underlying gap is in the contract schema: nothing distinguishes a prose input
 * from an identifier, so this set cannot be derived.
 */
const NON_PROSE_INPUTS = new Set<string>([`${MATH_ID}::statementCode`]);

/** Evaluators where a contract-shaped payload yields no verdict. */
const VERDICT_GAPS = new Set<string>([
  // The live trap: readOutcome's override names `grade`, the contract declares
  // `grade_band`. Regenerating this schema from its contract silently blanks every
  // GLA verdict in every report until the override is updated in the same change.
  GLA_ID,
  // No `*_score` and no `reasoning` — alignment counts instead. Math reports through
  // its own output path and never goes through readOutcome.
  MATH_ID,
]);

/**
 * Grade bands the report's own band list does not contain.
 *
 * An unresolved band is reported as the verdict "Off Target", not as an error, so a
 * schema regenerated from its contract would silently mislabel every text in that band.
 */
const BAND_GAPS = new Set<string>([
  // The contract declares `11-12`; the SDK schema and the report both say `11-CCR`.
  '11-12',
]);

/**
 * Family members absent from the report's `EVALUATOR_ORDER`.
 *
 * An absent member sorts to index 999, so its column appears in arbitrary order rather
 * than failing.
 */
const ORDER_GAPS = new Set<string>([
  PurposeClarityEvaluator.metadata.id,
  OrganizationalStructureEvaluator.metadata.id,
  ReferenceKnowledgeDemandsEvaluator.metadata.id,
  // The standards family has its own report, which does not use this ordering.
  MathStandardsAlignmentEvaluator.metadata.id,
]);

// ---------------------------------------------------------------------------
// Contract loading
// ---------------------------------------------------------------------------

const REPO_ROOT = join(process.cwd(), '..', '..');

interface Contract {
  dir: string;
  config: {
    evaluator: {
      id: string;
      stable_id: string;
      id_history: string[];
      name: string;
      description: string;
      supported_grades: string[];
    };
    steps: Array<{
      id: string;
      condition?: { input: string; in: (string | number)[] };
      model: { provider: string; name: string };
      generation?: { temperature?: number };
      optional?: boolean;
    }>;
  };
  inputSchema: { properties: Record<string, Record<string, unknown>>; required?: string[] };
  outputSchema: {
    properties: Record<string, Record<string, unknown>>;
    required: string[];
    $defs?: Record<string, Record<string, unknown>>;
  };
}

function contractFor(id: string): Contract {
  const dir = join(REPO_ROOT, 'evals', ...id.split('.').map((s) => s.replace(/_/g, '-')));
  const read = (name: string) => JSON.parse(readFileSync(join(dir, name), 'utf-8'));
  return {
    dir,
    config: read('config.json'),
    inputSchema: read('input_schema.json'),
    outputSchema: read('output_schema.json'),
  };
}

/** Inverted for a known gap, so a fix cannot pass without the entry being removed. */
function expectAgainstContract(
  isKnownGap: boolean,
  actual: unknown,
  expected: unknown,
  what: string,
): void {
  if (isKnownGap) {
    expect(
      actual,
      `${what}: this is on the known-gap allowlist but now matches the contract — delete its entry`,
    ).not.toEqual(expected);
  } else {
    expect(actual, what).toEqual(expected);
  }
}

const cases = EVALUATORS.map((E) => ({ name: E.metadata.name, E }));

describe('every evaluator has a contract at the derived path', () => {
  it.each(cases)('$name', ({ E }) => {
    const dir = join(
      REPO_ROOT,
      'evals',
      ...E.metadata.id.split('.').map((s) => s.replace(/_/g, '-')),
    );

    expect(existsSync(join(dir, 'config.json')), `no contract at ${dir}`).toBe(true);
  });
});

describe('identity matches the contract', () => {
  it.each(cases)('$name', ({ E }) => {
    const { config } = contractFor(E.metadata.id);

    expect(E.metadata.id).toBe(config.evaluator.id);
    expect(E.metadata.stableId).toBe(config.evaluator.stable_id);
    expect(E.metadata.idHistory).toEqual(config.evaluator.id_history);
    expect(E.metadata.name).toBe(config.evaluator.name);
    expect(E.metadata.description).toBe(config.evaluator.description);
  });
});

describe('supported grades match the contract', () => {
  it.each(cases)('$name', ({ E }) => {
    const { config, inputSchema } = contractFor(E.metadata.id);

    // A grade-free evaluator declares no `grade_level` input; its contract's
    // supported_grades then describes output bands, not accepted input.
    const takesGrade = 'grade_level' in inputSchema.properties;
    const declared = takesGrade
      ? ((inputSchema.properties.grade_level.enum as string[]) ??
         config.evaluator.supported_grades)
      : [];

    expectAgainstContract(
      GRADE_GAPS.has(E.metadata.id),
      [...E.metadata.supportedGrades],
      declared,
      `${E.metadata.name} supportedGrades`,
    );
  });
});

describe('declared providers match the contract steps', () => {
  it.each(cases)('$name', ({ E }) => {
    const { config } = contractFor(E.metadata.id);
    const declared = new Set(
      config.steps.filter((s) => !s.optional).map((s) => s.model.provider),
    );

    for (const provider of E.metadata.defaultProviders) {
      expect(
        declared.has(provider),
        `${E.metadata.name} declares defaultProvider "${provider}" that no non-optional step uses`,
      ).toBe(true);
    }
  });
});

describe('text limits honour the contract', () => {
  it.each(cases)('$name', ({ E }) => {
    const { inputSchema } = contractFor(E.metadata.id);
    const textInputs = Object.entries(inputSchema.properties).filter(
      ([field, spec]) =>
        spec.type === 'string' &&
        spec.maxLength !== undefined &&
        !NON_PROSE_INPUTS.has(`${E.metadata.id}::${field}`),
    );
    if (textInputs.length === 0) return;

    for (const [field, spec] of textInputs) {
      const declared = [spec.minLength, spec.maxLength];
      const enforced = [VALIDATION_LIMITS.MIN_TEXT_LENGTH, VALIDATION_LIMITS.MAX_TEXT_LENGTH];

      expectAgainstContract(
        LIMIT_GAPS.has(`${E.metadata.id}::${field}`),
        declared,
        enforced,
        `${E.metadata.name}.${field} bounds`,
      );
    }
  });
});

describe('readOutcome finds a verdict in a contract-shaped payload', () => {
  it.each(cases)('$name', ({ E }) => {
    const { outputSchema } = contractFor(E.metadata.id);

    // Build the smallest payload the contract permits: every required property, with
    // an enum's first value where one is declared.
    const payload: Record<string, unknown> = {};
    for (const field of outputSchema.required) {
      const spec = outputSchema.properties[field] ?? {};
      const ref = spec.$ref as string | undefined;
      const resolved = ref
        ? (outputSchema.$defs?.[ref.split('/').pop()!] ?? {})
        : spec;
      const values = resolved.enum as unknown[] | undefined;
      payload[field] = values ? values[0] : `stub ${field}`;
    }

    const envelope = {
      evaluator: E.metadata.id,
      result: payload,
      metadata: {
        model: 'stub:model',
        processingTimeMs: 0,
        tokenUsage: { inputTokens: 0, outputTokens: 0 },
      },
    } as EvaluationResult;

    expectAgainstContract(
      VERDICT_GAPS.has(E.metadata.id),
      readOutcome(envelope).score !== undefined,
      true,
      `${E.metadata.name} readOutcome`,
    );
  });
});

describe('constructed models match the contract', () => {
  beforeEach(() => {
    constructed.length = 0;
  });

  it.each(cases)('$name', ({ E }) => {
    const { config } = contractFor(E.metadata.id);

    // Every key, so no evaluator fails construction for an unrelated reason.
    new (E as unknown as new (c: Record<string, unknown>) => unknown)({
      googleApiKey: 'k',
      openaiApiKey: 'k',
      anthropicApiKey: 'k',
      learningCommonsApiKey: 'k',
      telemetry: false,
    });

    const asked = [...new Set(constructed.map((c) => `${c.type}:${c.model}`))].sort();
    const declared = [
      ...new Set(config.steps.map((s) => `${s.model.provider}:${s.model.name}`)),
    ].sort();

    expectAgainstContract(
      MODEL_GAPS.has(E.metadata.id),
      asked,
      declared,
      `${E.metadata.name} models`,
    );
  });
});

describe('the report recognises every grade band the contract declares', () => {
  const glaContract = contractFor(GLA_ID);
  const bands = ((glaContract.outputSchema.$defs?.GradeBand as { enum?: string[] })?.enum ??
    []) as string[];

  it.each(bands.map((band) => ({ band })))('%s', ({ band }) => {
    const output = {
      results: [
        {
          rowIndex: 1,
          text: 'Sample text.',
          gradeLevel: band.split('-')[0],
          evaluatorId: GLA_ID,
          status: 'success',
          score: band,
          reasoning: 'r',
          processingTimeMs: 1,
          originalRow: { text: 'Sample text.', grade_level: band.split('-')[0] },
        },
      ],
      summary: {
        totalTasks: 1,
        successful: 1,
        failed: 0,
        durationMs: 1,
        resultsPerEvaluator: {},
      },
    } as unknown as BatchOutput;

    const meta = {
      reportId: 'r',
      generatedAt: 'now',
      csvPath: '/tmp/in.csv',
      totalInputRows: 1,
      groupId: 'text-complexity',
      evaluatorIds: [GLA_ID],
      evaluatorNames: ['GLA'],
    } as unknown as ReportMeta;

    const html = formatAsHTML(output, meta);
    const marker = 'var REPORT_DATA = ';
    const start = html.indexOf(marker) + marker.length;
    const line = html.slice(start, html.indexOf('\n', start));
    const data = JSON.parse(line.endsWith(';') ? line.slice(0, -1) : line);

    // A grade inside the band must read as on-band. An unresolved band indexes to -1,
    // which the report renders as the verdict "Off Target" — a plausible-looking answer.
    expectAgainstContract(
      BAND_GAPS.has(band),
      data.fullResults.rows[0].__gla_status,
      'On Band',
      `GLA band "${band}" resolved by the report`,
    );
  });
});

describe('the report can order every family member', () => {
  // EVALUATOR_ORDER lives in the report template as a plain JS literal, so nothing
  // typechecks it against the families. A member missing from it sorts to index 999
  // and lands in arbitrary order — visible only to someone reading the report.
  const template = readFileSync(join(process.cwd(), 'src/batch/report-template.html'), 'utf-8');
  const marker = 'const EVALUATOR_ORDER = [';
  const at = template.indexOf(marker);

  it('finds the ordering array in the template', () => {
    // Without this, a moved or reformatted marker would surface as "every member is
    // absent" and send the reader looking in the wrong place.
    expect(at, `"${marker}" not found in report-template.html`).toBeGreaterThan(-1);
  });

  const declared = at === -1 ? '' : template.slice(at, template.indexOf(']', at));

  const members = getFamilies().flatMap((f) => f.members.map((m) => ({ family: f.id, id: m.id })));

  it.each(members)('$family / $id', ({ id }) => {
    expectAgainstContract(
      ORDER_GAPS.has(id),
      declared.includes(`'${id}'`),
      true,
      `"${id}" is absent from the report's EVALUATOR_ORDER`,
    );
  });
});
