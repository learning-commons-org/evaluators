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
import { RevisionAccuracyEvaluator } from '../../src/evaluators/feedback/ela-writing/revision-accuracy.js';
import { RevisionActionabilityEvaluator } from '../../src/evaluators/feedback/ela-writing/revision-actionability.js';
import { RevisionManageabilityEvaluator } from '../../src/evaluators/feedback/ela-writing/revision-manageability.js';
import { StrengthAcknowledgmentEvaluator } from '../../src/evaluators/feedback/ela-writing/strength-acknowledgment.js';
import { StudentResponseSpecificityEvaluator } from '../../src/evaluators/feedback/ela-writing/student-response-specificity.js';
import { ToneAppropriatenessEvaluator } from '../../src/evaluators/feedback/ela-writing/tone-appropriateness.js';
import { WithholdingAnswersEvaluator } from '../../src/evaluators/feedback/ela-writing/withholding-answers.js';
import { RevisionAccuracyOutputSchema } from '../../src/schemas/feedback/ela-writing/revision-accuracy.js';
import { RevisionActionabilityOutputSchema } from '../../src/schemas/feedback/ela-writing/revision-actionability.js';
import { RevisionManageabilityOutputSchema } from '../../src/schemas/feedback/ela-writing/revision-manageability.js';
import { StrengthAcknowledgmentOutputSchema } from '../../src/schemas/feedback/ela-writing/strength-acknowledgment.js';
import { StudentResponseSpecificityOutputSchema } from '../../src/schemas/feedback/ela-writing/student-response-specificity.js';
import { ToneAppropriatenessOutputSchema } from '../../src/schemas/feedback/ela-writing/tone-appropriateness.js';
import { WithholdingAnswersOutputSchema } from '../../src/schemas/feedback/ela-writing/withholding-answers.js';
import { InputValidationError } from '../../src/errors.js';
import { readOutcome } from '../../src/schemas/outcome.js';
import { runPreprocessingStep } from '../../src/features/preprocessing.js';
import type { EvaluationResult } from '../../src/schemas/index.js';
import { BackgroundKnowledgeDemandsOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/background-knowledge-demands.js';
import { GradeLevelAppropriatenessOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/grade-level-appropriateness.js';
import { MeaningDirectnessOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/meaning-directness.js';
import { OrganizationalStructureOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/organizational-structure.js';
import { PurposeClarityOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/purpose-clarity.js';
import { ReferenceKnowledgeDemandsOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/reference-knowledge-demands.js';
import { VocabularyComplexityOutputSchema } from '../../src/schemas/student-facing-text/ela-reading/vocabulary-complexity.js';
import { ComplexityClassificationSchema } from '../../src/schemas/student-facing-text/ela-reading/sentence-structure.js';

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
const llmCalls: Array<{ temperature?: number; messages?: Array<{ role: string; content: string }> }> = [];

vi.mock('../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => {
      constructed.push({ type: config.type, model: config.model });
      return {
        label: `${config.type}:${config.model}`,
        generateStructured: vi.fn(async (request: { temperature?: number; messages?: Array<{ role: string; content: string }> }) => {
          llmCalls.push({ temperature: request.temperature, messages: request.messages });
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
  // Every contract now has an implementation. A new contract lands here until its
  // evaluator does, and the assertion below fails once it is implemented, so the entry
  // cannot outlive its reason.
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
  // Empty: every evaluator constructs the model its contract declares.
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
  // Empty: the report recognises every band the contracts declare.
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
  // Empty: every evaluator sends the temperature its contract declares.
]);

/**
 * Evaluators whose schema module does not export `<Evaluator>OutputSchema`, and so has no
 * `<Evaluator>Result` for a caller to name the payload with.
 */
const RESULT_NAME_GAPS = new Set<string>([
  // Exports its two step schemas instead: SentenceAnalysisSchema, ComplexityClassificationSchema.
  SENTENCE_ID,
  // Assembles its payload from per-component results, so there is no single schema.
  MATH_ID,
]);

/**
 * Evaluators whose schema offers different values than the contract declares.
 */
const ENUM_VALUE_GAPS = new Set<string>([
  // Sends the shared Title Case TextComplexityLevel ('Slightly complex') where the
  // contract declares 'slightly_complex'. Same divergence as FIXTURE_VALUE_GAPS.
  SENTENCE_ID,
]);

/**
 * Evaluators that do not compute a declared preprocessing step the way the contract says.
 */
const PREPROCESSING_GAPS = new Set<string>([
  // Both call the hand-rolled compromise+syllable `calculateFleschKincaidGrade` instead of
  // the declared `text-readability.fleschKincaidGrade`. The two disagree — on the fixture
  // corpus the declared library is the less accurate of the two against Python's textstat
  // (mean error 1.394 vs 0.273), so which one the contract should declare is still open.
  BKD_ID,
  MD_ID,
  VocabularyComplexityEvaluator.metadata.id,
]);

/**
 * Evaluators whose schema rejects the values its own contract fixtures record.
 */
const FIXTURE_VALUE_GAPS = new Set<string>([
  // Still sends the shared Title Case TextComplexityLevel ('Slightly complex') where the
  // contract, and so its fixtures, say 'slightly_complex'.
  SENTENCE_ID,
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
  [RevisionAccuracyEvaluator.metadata.id]: RevisionAccuracyOutputSchema,
  [RevisionActionabilityEvaluator.metadata.id]: RevisionActionabilityOutputSchema,
  [RevisionManageabilityEvaluator.metadata.id]: RevisionManageabilityOutputSchema,
  [StrengthAcknowledgmentEvaluator.metadata.id]: StrengthAcknowledgmentOutputSchema,
  [StudentResponseSpecificityEvaluator.metadata.id]: StudentResponseSpecificityOutputSchema,
  [ToneAppropriatenessEvaluator.metadata.id]: ToneAppropriatenessOutputSchema,
  [WithholdingAnswersEvaluator.metadata.id]: WithholdingAnswersOutputSchema,
  [BackgroundKnowledgeDemandsEvaluator.metadata.id]: BackgroundKnowledgeDemandsOutputSchema,
  [GradeLevelAppropriatenessEvaluator.metadata.id]: GradeLevelAppropriatenessOutputSchema,
  [MeaningDirectnessEvaluator.metadata.id]: MeaningDirectnessOutputSchema,
  [OrganizationalStructureEvaluator.metadata.id]: OrganizationalStructureOutputSchema,
  [PurposeClarityEvaluator.metadata.id]: PurposeClarityOutputSchema,
  [ReferenceKnowledgeDemandsEvaluator.metadata.id]: ReferenceKnowledgeDemandsOutputSchema,
  [VocabularyComplexityEvaluator.metadata.id]: VocabularyComplexityOutputSchema,
  [SentenceStructureEvaluator.metadata.id]: ComplexityClassificationSchema,
};


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
    preprocessing?: Array<{
      id: string;
      implementation?: {
        typescript?: {
          library: string;
          function: string;
          post_transform?: { type: string; precision?: number };
        };
      };
    }>;
    outcome?: { score: string; reasoning: string };
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
/** Stands in for the teacher comment the feedback family judges. */
const FEEDBACK_TEXT = 'Try adding a topic sentence so the reader knows your argument.';

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
  [RevisionAccuracyEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
  [RevisionActionabilityEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
  [RevisionManageabilityEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
  [StrengthAcknowledgmentEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
  [StudentResponseSpecificityEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
  [ToneAppropriatenessEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
  [WithholdingAnswersEvaluator.metadata.id]: (E, text) =>
    construct(E).evaluate({ student_text: text, feedback_text: FEEDBACK_TEXT }),
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

describe('evaluator and schema modules sit at the derived path', () => {
  // The module's location is derived from its id by the same rule as its contract's, so
  // a contract that moves takes its module with it and neither can drift from the other.
  // It also removes a collision: two evaluators can share a last id segment.
  //
  // Not covered by the compiler: a module moved *with* its imports fixed typechecks
  // cleanly, and only this notices.
  it.each(cases)('$name', ({ E }) => {
    const relative = E.metadata.id.split('.').map((s) => s.replace(/_/g, '-'));

    for (const kind of ['evaluators', 'schemas']) {
      const module = join(process.cwd(), 'src', kind, ...relative) + '.ts';

      expect(existsSync(module), `no ${kind} module at ${module}`).toBe(true);
    }
  });
});

describe('the payload type is named after the evaluator', () => {
  // A caller reads the payload out of EvaluationResult<T>, so T is public API and needs a
  // name they can import. Deriving it from the evaluator's own name is what makes that
  // predictable, and it is the name the generator emits.
  //
  // Type names are erased at runtime, so this checks the schema export they come from.
  it.each(cases)('$name', ({ E }) => {
    const relative = E.metadata.id.split('.').map((s) => s.replace(/_/g, '-'));
    const module = join(process.cwd(), 'src', 'schemas', ...relative) + '.ts';
    const source = readFileSync(module, 'utf-8');

    const className = relative[relative.length - 1]
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join('');

    const declaresSchema = source.includes(`export const ${className}OutputSchema`);
    const declaresResult = source.includes(`export type ${className}Result`);

    if (RESULT_NAME_GAPS.has(E.metadata.id)) {
      expect(
        declaresSchema && declaresResult,
        `${E.metadata.name} now names its payload after itself — drop it from RESULT_NAME_GAPS`,
      ).toBe(false);
      return;
    }

    expect(declaresSchema, `${module} does not export ${className}OutputSchema`).toBe(true);
    expect(declaresResult, `${module} does not export ${className}Result`).toBe(true);
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
    const { inputSchema } = contractFor(E.metadata.id);

    // `supported_grades` states what the evaluator is built for; the accepted set is
    // the grade input's own enum. Comparing against the enum is the whole point -- an
    // evaluator taking no grade accepts none, and asserting that by hardcoding `[]`
    // would just restate the assumption.
    const accepted = (inputSchema.properties.grade_level?.enum as string[]) ?? [];

    expectAgainstContract(
      GRADE_GAPS.has(E.metadata.id),
      [...E.metadata.supportedGrades],
      accepted,
      `${E.metadata.name} supportedGrades vs the grades its input schema accepts`,
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

    expect(sentFields, `${E.metadata.name} sent payload fields`).toEqual(declared);
  });

  // Field names are only half of it: a field can carry the right name and offer the model
  // the wrong choices. `11-CCR` for a contract declaring `11-12` passed the check above.
  it.each(withSchema)('$name enum values', ({ E }) => {
    const { outputSchema } = contractFor(E.metadata.id);
    const defs = (outputSchema.$defs ?? {}) as Record<string, { enum?: unknown[] }>;
    const shape = SDK_OUTPUT_SCHEMAS[E.metadata.id].shape as Record<string, unknown>;

    const mismatched = Object.entries(outputSchema.properties).flatMap(([field, spec]) => {
      const ref = typeof spec.$ref === 'string' ? spec.$ref.replace('#/$defs/', '') : undefined;
      const declared = (ref ? defs[ref]?.enum : (spec as { enum?: unknown[] }).enum) as
        | unknown[]
        | undefined;
      if (!declared) return [];

      const options = (shape[field] as { options?: unknown[] } | undefined)?.options;
      if (!options) {
        return [`${field}: schema offers no choices, contract declares ${declared.length}`];
      }

      // A string enum becomes z.enum, whose options are the values. An integer enum
      // cannot — Zod enums are strings — so it becomes a union of z.literal, whose
      // options are the literal schemas. Both have to compare against the contract.
      const sent = options.map((option) =>
        option !== null && typeof option === 'object'
          ? (option as { value: unknown }).value
          : option,
      );

      const same = sent.length === declared.length && sent.every((v, i) => v === declared[i]);
      return same
        ? []
        : [`${field}: sent ${JSON.stringify(sent)}, declared ${JSON.stringify(declared)}`];
    });

    if (ENUM_VALUE_GAPS.has(E.metadata.id)) {
      expect(
        mismatched,
        `${E.metadata.name} now offers the declared values — drop it from ENUM_VALUE_GAPS`,
      ).not.toEqual([]);
      return;
    }

    expect(mismatched, `${E.metadata.name} offers values its contract does not declare`).toEqual(
      [],
    );
  });
});

describe('the schema accepts the values the contract fixtures record', () => {
  // The comparison above matches field *names*. This checks the values: a fixture's
  // `expected` is what the model returned for a real input, so a schema that rejects it
  // is a schema the model cannot satisfy.
  //
  // Unit tests cannot catch this — they mock the provider, so the payload is passed
  // through without ever meeting the schema.
  const withSchema = cases.filter(({ E }) => SDK_OUTPUT_SCHEMAS[E.metadata.id]);

  it.each(withSchema)('$name', ({ E }) => {
    const { dir } = contractFor(E.metadata.id);
    const fixtures = JSON.parse(readFileSync(join(dir, 'fixtures.json'), 'utf-8')) as Array<{
      id: string;
      expected: Record<string, unknown>;
    }>;
    const shape = SDK_OUTPUT_SCHEMAS[E.metadata.id].shape as Record<
      string,
      { safeParse(value: unknown): { success: boolean } }
    >;

    // A field the schema does not have is a failure, not something to skip: the contract
    // recorded the model returning it. Whole-object parsing is not an option here — every
    // `expected` is a partial assertion, missing between one and five required fields.
    const rejected = fixtures.flatMap(({ id, expected }) =>
      Object.entries(expected).flatMap(([field, value]) => {
        const fieldSchema = shape[field];
        if (!fieldSchema) return [`${id}: ${field} is absent from the schema`];
        if (!fieldSchema.safeParse(value).success) {
          return [`${id}: ${field}=${JSON.stringify(value)}`];
        }
        return [];
      }),
    );

    if (FIXTURE_VALUE_GAPS.has(E.metadata.id)) {
      expect(
        rejected,
        `${E.metadata.name} now accepts its fixtures — drop it from FIXTURE_VALUE_GAPS`,
      ).not.toEqual([]);
      return;
    }

    expect(rejected, `${E.metadata.name} rejects its own contract fixtures`).toEqual([]);
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

    // Read from the contract, not from metadata: this asserts the declaration and the
    // payload agree, which is exactly what would drift.
    const { outcome } = contractFor(E.metadata.id).config;

    expect(
      readOutcome(envelope, outcome).score,
      `${E.metadata.name}: the payload the SDK returns has no ${outcome?.score ?? 'declared verdict'}`,
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

    if (contractIds.includes(id)) {
      expect(
        UNIMPLEMENTED.has(id),
        `"${id}" is implemented — drop it from UNIMPLEMENTED`,
      ).toBe(false);
      return;
    }

    expect(
      UNIMPLEMENTED.has(id),
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

describe('the reported model matches the contract steps that apply', () => {
  // A step can be conditional on an input, so which model runs depends on that input and
  // the reported model has to follow. Every other invocation in this suite passes
  // grade_level '5', which is why a conditional branch reporting the wrong model survived.
  //
  // Derived from the contract, so an evaluator that gains a conditional step is covered
  // without touching this test.
  const perGrade = cases.flatMap(({ name, E }) => {
    if (!INVOKE[E.metadata.id]) return [];
    const { config } = contractFor(E.metadata.id);
    const grades = [
      ...new Set(config.steps.flatMap((step) => (step.condition?.in ?? []).map(String))),
    ];
    return grades.map((grade) => ({ name, E, grade }));
  });

  it('finds at least one conditional step to exercise', () => {
    // If this fails the suite below is vacuous — either the contracts lost their
    // conditions or the derivation above stopped matching them.
    expect(perGrade.length).toBeGreaterThan(0);
  });

  it.each(perGrade)('$name at grade $grade', async ({ E, grade }) => {
    const { config } = contractFor(E.metadata.id);
    const applies = (step: (typeof config.steps)[number]) =>
      !step.condition ||
      (step.condition.input === 'grade_level' && step.condition.in.map(String).includes(grade));

    const expected = config.steps
      .filter(applies)
      .map((step) => `${step.model.provider}:${step.model.name}`)
      .join('+');

    const result = (await construct(E).evaluate({
      text: 'The storm gathered offshore and the harbour emptied before dusk.',
      grade_level: grade,
    })) as { metadata: { model: string } };

    expect(result.metadata.model, `${E.metadata.name} at grade ${grade}`).toBe(expected);
  });
});

describe('every declared preprocessing value reaches the prompt', () => {
  // Preprocessing feeds a number into a sha256-pinned prompt, so a step that silently
  // stops running, or runs a different implementation, changes what the model is asked
  // without changing anything a schema or a hash would notice.
  const withPreprocessing = cases.filter(({ E }) => {
    if (!INVOKE[E.metadata.id]) return false;
    // Sentence Structure's first stage reads array fields off the model response, and the
    // shared mock returns `data: {}`, so it throws before any prompt is built. Its
    // preprocessing declares libraries the registry does not have either — see
    // PREPROCESSING_GAPS for the same divergence in the evaluators that can be driven.
    if (E.metadata.id === SENTENCE_ID) return false;
    return (contractFor(E.metadata.id).config.preprocessing ?? []).length > 0;
  });

  it('finds evaluators with declared preprocessing', () => {
    expect(withPreprocessing.length).toBeGreaterThan(0);
  });

  const TEXT =
    'A thousand years ago boys and girls did not learn to read. Books were scarce and ' +
    'precious, and only a few men could read them. Each book was written by hand.';

  it.each(withPreprocessing)('$name', async ({ E }) => {
    const { config } = contractFor(E.metadata.id);
    llmCalls.length = 0;

    await INVOKE[E.metadata.id](E, TEXT);

    const prompts = llmCalls.flatMap((c) => (c.messages ?? []).map((m) => m.content)).join('\n');

    const missing = (config.preprocessing ?? [])
      .flatMap((step) => {
        const impl = step.implementation?.typescript;
        if (!impl) return [];
        const value = String(runPreprocessingStep(TEXT, impl));
        return prompts.includes(value) ? [] : [step];
      })
      .map((step) => step.id);

    if (PREPROCESSING_GAPS.has(E.metadata.id)) {
      expect(
        missing,
        `${E.metadata.name} now matches its declared preprocessing — drop it from PREPROCESSING_GAPS`,
      ).not.toEqual([]);
      return;
    }

    expect(missing, `${E.metadata.name}: declared preprocessing absent from the prompt`).toEqual([]);
    // A placeholder left in the prompt means substitution silently did not happen.
    expect(prompts, `${E.metadata.name}: unsubstituted placeholder`).not.toMatch(/\{[a-z_]+\}/);
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
