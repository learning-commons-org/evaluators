import { describe, it, expect } from 'vitest';
import { MathStandardsAlignmentEvaluator, Jurisdiction } from '../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';
import { KnowledgeGraphClient } from '../../src/knowledge-graph/client.js';

const RUN = process.env['RUN_INTEGRATION_TESTS'] === 'true';
const ANTHROPIC_KEY = process.env['ANTHROPIC_API_KEY'];
const LEARNING_COMMONS_KEY = process.env['LEARNING_COMMONS_API_KEY'];

// A missing key when integration tests were explicitly requested is a misconfiguration,
// not a reason to quietly pass — matches batch/model-override.
if (RUN) {
  if (!ANTHROPIC_KEY) throw new Error('ANTHROPIC_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  if (!LEARNING_COMMONS_KEY) {
    throw new Error('LEARNING_COMMONS_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  }
}

const itIf = (cond: boolean) => (cond ? it : it.skip);

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

// From the original Python notebook — ground-truth case.
const AREA_QUESTION =
  'A playground is shaped like an L. One part is a rectangle that is 8 feet long and 3 feet wide. ' +
  'Attached to it is another rectangle that is 4 feet long and 2 feet wide, with no overlap. ' +
  'What is the total area of the playground in square feet?';

const UNRELATED_QUESTION = 'What is 12 + 7?';

// The full 3.MD.C.7 standard family: parent + all four sub-standards.
const MD_C_7_FAMILY = ['3.MD.C.7', '3.MD.C.7.a', '3.MD.C.7.b', '3.MD.C.7.c', '3.MD.C.7.d'];

// Instrumented evaluator wraps KnowledgeGraphClient methods to count calls.
function makeInstrumentedEvaluator() {
  const counters = { uuidFetches: 0, lcFetches: 0, llmCalls: 0 };
  const baseClient = new KnowledgeGraphClient(LEARNING_COMMONS_KEY!);

  // Wrap individual methods to count KG API calls
  const origInfo = baseClient.getStandardInfo.bind(baseClient);
  baseClient.getStandardInfo = async (code, opts) => { counters.uuidFetches++; return origInfo(code, opts); };
  const origLc = baseClient.getLearningComponents.bind(baseClient);
  baseClient.getLearningComponents = async (uuid: string) => { counters.lcFetches++; return origLc(uuid); };

  const evaluator = new MathStandardsAlignmentEvaluator({
    anthropicApiKey: ANTHROPIC_KEY!,
    learningCommonsApiKey: LEARNING_COMMONS_KEY!,
    _kgClient: baseClient,
  });

  for (const providerKey of ['detailProvider', 'coarseProvider'] as const) {
    const p = (evaluator as unknown as Record<string, { generateStructured: (...args: unknown[]) => Promise<unknown> }>)[providerKey];
    const orig = p.generateStructured.bind(p);
    p.generateStructured = async (...args: unknown[]) => { counters.llmCalls++; return orig(...args); };
  }

  return { evaluator, counters };
}

// ---------------------------------------------------------------------------
// Consolidated integration test
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - integration', { timeout: 300_000 }, () => {
  itIf(RUN)(
    '3.MD.C.7 family: area L-shape question vs parent + all sub-standards',
    async () => {
      const questionItems = [
        { question: AREA_QUESTION, statement_codes: MD_C_7_FAMILY },
        { question: UNRELATED_QUESTION, statement_codes: MD_C_7_FAMILY },
      ];

      // ── Phase 1: ground truth (no coarse filter) ──────────────────────────
      const { evaluator: ev1, counters: c1 } = makeInstrumentedEvaluator();
      const groundTruth = await ev1.evaluateItems(questionItems, Jurisdiction.MultiState, {
        useCoarseFilter: false,
      });

      // ── Phase 2: with coarse filter (explicitly opt in) ───────────────────
      const { evaluator: ev2, counters: c2 } = makeInstrumentedEvaluator();
      const filtered = await ev2.evaluateItems(questionItems, Jurisdiction.MultiState, { useCoarseFilter: true });

      // ── Log results ───────────────────────────────────────────────────────
      console.log('\n════ GROUND TRUTH (no coarse filter) ════');
      console.log(`KG calls: ${c1.uuidFetches} UUID, ${c1.lcFetches} LC | LLM calls: ${c1.llmCalls}`);
      for (const qr of groundTruth) {
        console.log(`\n  Q: "${qr.question.slice(0, 70)}…"`);
        for (const s of qr.standards) {
          const tag = s.aligned_count > 0 ? `ALIGNED ${s.aligned_count}/${s.total_count}` : `not aligned 0/${s.total_count}`;
          console.log(`    ${s.statement_code.padEnd(12)} [${tag}]`);
          for (const lc of s.learning_components) {
            console.log(`      ${lc.aligned ? '✓' : '✗'} ${lc.description.slice(0, 80)}`);
          }
        }
      }

      console.log('\n════ WITH COARSE FILTER ════');
      console.log(`KG calls: ${c2.uuidFetches} UUID, ${c2.lcFetches} LC | LLM calls: ${c2.llmCalls}`);
      for (const qr of filtered) {
        console.log(`\n  Q: "${qr.question.slice(0, 70)}…"`);
        for (const s of qr.standards) {
          if (s.coarse_filtered) {
            console.log(`    ${s.statement_code.padEnd(12)} [COARSE FILTERED]`);
          } else {
            const tag = s.aligned_count > 0 ? `ALIGNED ${s.aligned_count}/${s.total_count}` : `not aligned 0/${s.total_count}`;
            console.log(`    ${s.statement_code.padEnd(12)} [${tag}]`);
          }
        }
      }

      console.log('\n════ COARSE FILTER ANALYSIS ════');
      const areaGT = groundTruth.find((q) => q.question === AREA_QUESTION)!;
      const areaFiltered = filtered.find((q) => q.question === AREA_QUESTION)!;

      let falseNegatives = 0;
      for (const gtStd of areaGT.standards) {
        const filteredStd = areaFiltered.standards.find((s) => s.statement_code === gtStd.statement_code)!;
        const wasAligned = gtStd.aligned_count > 0;
        const wasFiltered = filteredStd.coarse_filtered === true;
        const status = wasFiltered && wasAligned ? '❌ FALSE NEGATIVE' :
                       wasFiltered ? '○ filtered (correctly — not aligned)' :
                       wasAligned ? '✓ passed through (correctly — aligned)' :
                       '✓ passed through (not aligned, detail eval confirmed)';
        console.log(`  ${gtStd.statement_code.padEnd(12)} aligned=${wasAligned} filtered=${wasFiltered}  ${status}`);
        if (wasFiltered && wasAligned) falseNegatives++;
      }
      console.log(`\nFalse negatives: ${falseNegatives}/${MD_C_7_FAMILY.length}`);

      // ── Ground truth assertions ────────────────────────────────────────────

      const find = (code: string) => areaGT.standards.find((s) => s.statement_code === code)!;

      // Alignment per learning component is a model judgement and it moves between runs
      // even at temperature 0 — for 3.MD.C.7.d runs have produced 1, 2 and 3 of 3. So the
      // direction is asserted (does it align at all?) and never the count.
      //
      // 3.MD.C.7 — parent standard: "use multiplication and addition to find area"
      //   Area L-shape requires adding two rectangles → aligned
      const s7 = find('3.MD.C.7');
      expect(s7.total_count).toBeGreaterThan(0);
      expect(s7.aligned_count, '3.MD.C.7 should align').toBeGreaterThan(0);

      // 3.MD.C.7.a — "tiling" and "same result as multiplying side lengths"
      //   L-shape question does not ask students to tile or reason about tiling
      const s7a = find('3.MD.C.7.a');
      expect(s7a.total_count).toBeGreaterThan(0);
      expect(s7a.aligned_count, '3.MD.C.7.a should not align (about tiling, not decomposition)').toBe(0);

      // 3.MD.C.7.b — "multiply side lengths to find area of rectangles"
      //   Computing 8×3 and 4×2 is multiplication of side lengths → aligned
      const s7b = find('3.MD.C.7.b');
      expect(s7b.total_count).toBeGreaterThan(0);
      expect(s7b.aligned_count, '3.MD.C.7.b should align (multiplication of sides present)').toBeGreaterThan(0);

      // 3.MD.C.7.c — "distributive property / a(b+c)"
      //   L-shape uses decomposition and addition but does not explicitly model a(b+c)
      const s7c = find('3.MD.C.7.c');
      expect(s7c.total_count).toBeGreaterThan(0);
      expect(s7c.aligned_count, '3.MD.C.7.c should not align (about distributive property, not rectilinear area)').toBe(0);

      // 3.MD.C.7.d — "area additive / decompose rectilinear figures" — canonical match
      //   L-shape is the textbook example of rectilinear decomposition
      const s7d = find('3.MD.C.7.d');
      expect(s7d.total_count).toBeGreaterThan(0);
      expect(s7d.aligned_count, '3.MD.C.7.d should align').toBeGreaterThan(0);

      // Unrelated question must not align to any standard
      const unrelatedGT = groundTruth.find((q) => q.question === UNRELATED_QUESTION)!;
      for (const s of unrelatedGT.standards) {
        expect(s.aligned_count, `"12 + 7" should not align to ${s.statement_code}`).toBe(0);
      }

      // Coarse filter must not produce false negatives on the area question
      expect(falseNegatives, 'Coarse filter must not discard any aligned standard').toBe(0);
    },
  );
});
