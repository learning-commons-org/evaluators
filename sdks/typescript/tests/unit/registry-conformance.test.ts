import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

import * as exported from '../../src/evaluators/index.js';
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
import { InputValidationError } from '../../src/errors.js';
import { readOutcome } from '../../src/schemas/outcome.js';
import type { EvaluationResult } from '../../src/schemas/index.js';
import { BackgroundKnowledgeDemandsOutputSchema } from '../../src/schemas/background-knowledge-demands.js';
import { GradeLevelAppropriatenessOutputSchema } from '../../src/schemas/grade-level-appropriateness.js';
import { MeaningDirectnessOutputSchema } from '../../src/schemas/meaning-directness.js';
import { OrganizationalStructureOutputSchema } from '../../src/schemas/organizational-structure.js';
import { PurposeClarityOutputSchema } from '../../src/schemas/purpose-clarity.js';
import { ReferenceKnowledgeDemandsOutputSchema } from '../../src/schemas/reference-knowledge-demands.js';
import { VocabularyComplexityOutputSchema } from '../../src/schemas/vocabulary-complexity.js';
import { ComplexityClassificationSchema } from '../../src/schemas/sentence-structure.js';

interface EvaluatorClass {
  metadata: {
    id: string;
    stableId: string;
    idHistory: readonly string[];
    name: string;
    description: string;
    supportedGrades: readonly string[];
    defaultProviders: readonly string[];
  };
}
import {
  formatAsHTML,
  getFamilies,
  type BatchOutput,
  type ReportMeta,
} from '../../src/batch/index.js';

/** Records every (provider, model) an evaluator asks for at construction. */
const constructed: Array<{ type: string; model: string }> = [];

/** Records the generation settings of every LLM call an evaluator makes. */
const llmCalls: Array<{ temperature?: number }> = [];

vi.mock('../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => {
      constructed.push({ type: config.type, model: config.model });
      return {
        label: `${config.type}:${config.model}`,
        generateStructured: vi.fn(async (request: { temperature?: number }) => {
          llmCalls.push({ temperature: request.temperature });
          return {
            data: {},
            model: config.model,
            usage: { inputTokens: 1, outputTokens: 1 },
            latencyMs: 1,
          };
        }),
        generateText: vi.fn(async () => ({
          text: '{}',
          model: config.model,
          usage: { inputTokens: 1, outputTokens: 1 },
          latencyMs: 1,
        })),
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

/**
 * Every evaluator the SDK exports, discovered rather than listed: anything with a
 * static `metadata.id` is an evaluator. A hand-maintained array silently gives an
 * omitted evaluator zero coverage, which is the failure this suite exists to prevent.
 */
const EVALUATORS = (Object.values(exported) as unknown[])
  .filter(
    (v): v is EvaluatorClass =>
      typeof v === 'function' && typeof (v as unknown as EvaluatorClass).metadata?.id === 'string',
  )
  .sort((a, b) => a.metadata.id.localeCompare(b.metadata.id));

/**
 * Contracts with no TypeScript implementation yet.
 *
 * Listing them here is what keeps them visible: the test below asserts that every
 * contract on disk is either implemented or named here, so a new contract cannot sit
 * unimplemented and unmentioned.
 */
const UNIMPLEMENTED = new Set<string>([
  'feedback.ela_writing.revision_accuracy',
  'feedback.ela_writing.revision_actionability',
  'feedback.ela_writing.revision_manageability',
  'feedback.ela_writing.strength_acknowledgment',
  'feedback.ela_writing.student_response_specificity',
  'feedback.ela_writing.tone_appropriateness',
  'feedback.ela_writing.withholding_answers',
]);

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

/**
 * Evaluators sending a temperature their contract does not declare.
 */
const TEMPERATURE_GAPS = new Set<string>([
  // Sends 0.25; the contract declares 1.
  GLA_ID,
]);

/**
 * The Zod schema each evaluator actually sends to the model.
 *
 * This is the side of the comparison the suite was missing: the contract says what the
 * payload should be, and only this says what it is.
 *
 * Math Standards Alignment is absent deliberately — its payload is assembled from
 * per-component results rather than being one model output, so there is no single
 * schema to compare.
 */
const SDK_OUTPUT_SCHEMAS: Record<string, { shape: Record<string, unknown> }> = {
  [BackgroundKnowledgeDemandsEvaluator.metadata.id]: BackgroundKnowledgeDemandsOutputSchema,
  [GradeLevelAppropriatenessEvaluator.metadata.id]: GradeLevelAppropriatenessOutputSchema,
  [MeaningDirectnessEvaluator.metadata.id]: MeaningDirectnessOutputSchema,
  [OrganizationalStructureEvaluator.metadata.id]: OrganizationalStructureOutputSchema,
  [PurposeClarityEvaluator.metadata.id]: PurposeClarityOutputSchema,
  [ReferenceKnowledgeDemandsEvaluator.metadata.id]: ReferenceKnowledgeDemandsOutputSchema,
  [VocabularyComplexityEvaluator.metadata.id]: VocabularyComplexityOutputSchema,
  [SentenceStructureEvaluator.metadata.id]: ComplexityClassificationSchema,
};

/** Evaluators whose sent schema does not match their contract's declared payload. */
const SCHEMA_GAPS = new Set<string>([
  // Sends `grade` / `alternative_grade`; the contract declares `grade_band` /
  // `alternative_grade_band`, and its enum says `11-12` where the SDK says `11-CCR`.
  GLA_ID,
  // Sends `answer`; the contract declares `complexity_score`.
  SENTENCE_ID,
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

/**
 * How to run each text-taking evaluator with inputs its contract accepts.
 *
 * Math is absent: its inputs are a question and a standard code, and it calls the
 * Knowledge Graph before any model. Naming inputs will make this map derivable.
 */
const INVOKE: Record<string, (E: EvaluatorClass, text: string) => Promise<unknown>> = {
  [GLA_ID]: (E, text) => construct(E).evaluate({ text }),
  [BKD_ID]: (E, text) => construct(E).evaluate({ text, grade_level: '5' }),
  [MD_ID]: (E, text) => construct(E).evaluate({ text, grade_level: '5' }),
  [OrganizationalStructureEvaluator.metadata.id]: (E, text) => construct(E).evaluate({ text, grade_level: '5' }),
  [PurposeClarityEvaluator.metadata.id]: (E, text) => construct(E).evaluate({ text, grade_level: '5' }),
  [ReferenceKnowledgeDemandsEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ text, grade_level: '5' }),
  [SENTENCE_ID]: (E, text) => construct(E).evaluate({ text, grade_level: '5' }),
  [VocabularyComplexityEvaluator.metadata.id]: (E, text) => construct(E).evaluate({ text, grade_level: '5' }),
};

/**
 * Evaluators with more than one step.
 *
 * The temperature check needs each step's own response stubbed to its own shape, so it
 * skips these. The minimum-length check does not: validation runs before any LLM call.
 */
const MULTI_STEP = new Set<string>([SENTENCE_ID, VocabularyComplexityEvaluator.metadata.id]);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function construct(E: EvaluatorClass): any {
  return new (E as unknown as new (c: Record<string, unknown>) => unknown)({
    googleApiKey: 'k',
    openaiApiKey: 'k',
    anthropicApiKey: 'k',
    learningCommonsApiKey: 'k',
    telemetry: false,
  });
}

const invocableCases = cases.filter(({ E }) => INVOKE[E.metadata.id]);
const singleStepCases = invocableCases.filter(({ E }) => !MULTI_STEP.has(E.metadata.id));

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

describe('the schema the SDK sends matches the contract', () => {
  const withSchema = cases.filter(({ E }) => SDK_OUTPUT_SCHEMAS[E.metadata.id]);

  it('covers every evaluator that sends a single schema', () => {
    // Guards the map above from silently falling behind the evaluator list.
    expect(withSchema.length).toBe(EVALUATORS.length - 1);
  });

  it.each(withSchema)('$name', ({ E }) => {
    const { outputSchema } = contractFor(E.metadata.id);
    const sentFields = Object.keys(SDK_OUTPUT_SCHEMAS[E.metadata.id].shape).sort();
    const declared = Object.keys(outputSchema.properties).sort();

    expectAgainstContract(
      SCHEMA_GAPS.has(E.metadata.id),
      sentFields,
      declared,
      `${E.metadata.name} sent payload fields`,
    );
  });
});

describe('readOutcome finds a verdict in the payload the SDK actually returns', () => {
  const withSchema = cases.filter(({ E }) => SDK_OUTPUT_SCHEMAS[E.metadata.id]);

  it.each(withSchema)('$name', ({ E }) => {
    // Built from the SDK's own schema, so an override that stops matching what the SDK
    // sends fails here. Building it from the contract instead hid exactly that.
    const shape = SDK_OUTPUT_SCHEMAS[E.metadata.id].shape;
    const payload: Record<string, unknown> = {};
    for (const [field, spec] of Object.entries(shape)) {
      const options = (spec as { options?: unknown[] }).options;
      payload[field] = options ? options[0] : `stub ${field}`;
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

    expect(
      readOutcome(envelope).score,
      `${E.metadata.name}: readOutcome found no verdict in the payload the SDK returns`,
    ).toBeDefined();
  });
});

describe('every contract is implemented or explicitly listed as not', () => {
  const contractIds = EVALUATORS.map((E) => E.metadata.id);

  it.each(
    readdirSync(join(REPO_ROOT, 'evals'), { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith('_'))
      .flatMap((domain) =>
        readdirSync(join(REPO_ROOT, 'evals', domain.name), { withFileTypes: true })
          .filter((d) => d.isDirectory())
          .flatMap((skill) =>
            readdirSync(join(REPO_ROOT, 'evals', domain.name, skill.name), {
              withFileTypes: true,
            })
              .filter((d) => d.isDirectory())
              .map((ev) => ({
                dir: join(REPO_ROOT, 'evals', domain.name, skill.name, ev.name),
                label: `${domain.name}/${skill.name}/${ev.name}`,
              })),
          ),
      )
      .filter(({ dir }) => existsSync(join(dir, 'config.json'))),
  )('$label', ({ dir }) => {
    const id = JSON.parse(readFileSync(join(dir, 'config.json'), 'utf-8')).evaluator.id;

    expect(
      contractIds.includes(id) || UNIMPLEMENTED.has(id),
      `"${id}" has a contract but no implementation and is not in UNIMPLEMENTED`,
    ).toBe(true);
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

    // A deduped set, so this cannot see which step got which model. Swapping the two
    // grade-conditioned models in vocabulary-complexity would pass here — the
    // temperature check below is per-call but skips multi-step evaluators, so that
    // binding is only covered once the runner drives steps from the contract.
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

describe('the temperature sent matches the contract', () => {
  beforeEach(() => {
    llmCalls.length = 0;
  });

  it.each(singleStepCases)('$name', async ({ E }) => {
    const { config } = contractFor(E.metadata.id);
    await INVOKE[E.metadata.id](E, 'A sentence long enough to pass validation.');

    expect(llmCalls, `${E.metadata.name} made no LLM call`).toHaveLength(1);

    expectAgainstContract(
      TEMPERATURE_GAPS.has(E.metadata.id),
      llmCalls[0].temperature,
      config.steps[0].generation?.temperature,
      `${E.metadata.name} temperature`,
    );
  });
});

describe('a declared minimum length is enforced', () => {
  const withMinimum = invocableCases
    .map(({ name, E }) => {
      const { inputSchema } = contractFor(E.metadata.id);
      const min = inputSchema.properties.text?.minLength as number | undefined;
      return { name, E, min };
    })
    .filter((c): c is { name: string; E: EvaluatorClass; min: number } => (c.min ?? 0) > 1);

  it.each(withMinimum)('$name', async ({ E, min }) => {
    // One character short of what the contract declares. Asserting on rejection rather
    // than on the numbers is what lets this self-clean: comparing declared bounds to
    // the SDK's global pair would keep differing however the SDK behaved.
    const tooShort = 'a'.repeat(min - 1);
    const failure = await INVOKE[E.metadata.id](E, tooShort).then(
      () => undefined,
      (error: unknown) => error,
    );
    const rejectedForLength = failure instanceof InputValidationError;

    // Asserting on the error type, not on whether the call resolved: a stubbed provider
    // can fail an evaluation for reasons that have nothing to do with validation.
    expect(
      rejectedForLength,
      `${E.metadata.name} accepts text shorter than the minLength ${min} its contract declares`,
    ).toBe(true);
  });
});
