import { describe, it, expect } from 'vitest';
import { MathStandardsAlignmentEvaluator } from '../../src/evaluators/math/standards-alignment.js';
import { KnowledgeGraphApiRepository } from '../../src/knowledge-graph/repository.js';

const RUN = process.env['RUN_INTEGRATION_TESTS'] === 'true';
const OPENAI_KEY = process.env['OPENAI_API_KEY'];
const PLATFORM_KEY = process.env['PLATFORM_API_KEY'];

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

// Instrumented evaluator that wraps the KG repo to count calls.
function makeInstrumentedEvaluator() {
  const counters = { uuidFetches: 0, lcFetches: 0, llmCalls: 0 };
  const baseRepo = new KnowledgeGraphApiRepository(PLATFORM_KEY!);

  const repo = {
    async getStandardInfo(code: string) {
      counters.uuidFetches++;
      return baseRepo.getStandardInfo(code);
    },
    async getLearningComponents(uuid: string) {
      counters.lcFetches++;
      return baseRepo.getLearningComponents(uuid);
    },
    async getStandardsByGrade(grade: string, opts?: { excludeMP?: boolean }) {
      return baseRepo.getStandardsByGrade(grade, opts);
    },
  };

  const evaluator = new MathStandardsAlignmentEvaluator({
    openaiApiKey: OPENAI_KEY!,
    platformApiKey: PLATFORM_KEY!,
    knowledgeGraphRepository: repo,
  });

  for (const providerKey of ['detailProvider', 'coarseProvider'] as const) {
    const p = (evaluator as any)[providerKey];
    const orig = p.generateStructured.bind(p);
    p.generateStructured = async (req: any) => { counters.llmCalls++; return orig(req); };
  }

  return { evaluator, counters };
}

// ---------------------------------------------------------------------------
// Consolidated integration test
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - integration', { timeout: 300_000 }, () => {
  itIf(RUN && !!OPENAI_KEY && !!PLATFORM_KEY)(
    '3.MD.C.7 family: area L-shape question vs parent + all sub-standards',
    async () => {
      const questionItems = [
        { question: AREA_QUESTION, grade: '3' },
        { question: UNRELATED_QUESTION, grade: '3' },
      ];

      // ── Phase 1: ground truth (no coarse filter) ──────────────────────────
      const { evaluator: ev1, counters: c1 } = makeInstrumentedEvaluator();
      const groundTruth = await ev1.evaluateQuestionBank(questionItems, MD_C_7_FAMILY, {
        skipCoarseFilter: true,
      });

      // ── Phase 2: with coarse filter ───────────────────────────────────────
      const { evaluator: ev2, counters: c2 } = makeInstrumentedEvaluator();
      const filtered = await ev2.evaluateQuestionBank(questionItems, MD_C_7_FAMILY);

      // ── Log results ───────────────────────────────────────────────────────
      console.log('\n════ GROUND TRUTH (no coarse filter) ════');
      console.log(`KG calls: ${c1.uuidFetches} UUID, ${c1.lcFetches} LC | LLM calls: ${c1.llmCalls}`);
      for (const qr of groundTruth.byQuestion) {
        console.log(`\n  Q: "${qr.question.slice(0, 70)}…"`);
        for (const s of qr.standards) {
          const tag = s.alignedCount > 0 ? `ALIGNED ${s.alignedCount}/${s.totalCount}` : `not aligned 0/${s.totalCount}`;
          console.log(`    ${s.statementCode.padEnd(12)} [${tag}]`);
          for (const lc of s.learningComponents) {
            console.log(`      ${lc.aligned ? '✓' : '✗'} ${lc.description.slice(0, 80)}`);
          }
        }
      }

      console.log('\n════ WITH COARSE FILTER ════');
      console.log(`KG calls: ${c2.uuidFetches} UUID, ${c2.lcFetches} LC | LLM calls: ${c2.llmCalls}`);
      for (const qr of filtered.byQuestion) {
        console.log(`\n  Q: "${qr.question.slice(0, 70)}…"`);
        for (const s of qr.standards) {
          if (s.coarseFiltered) {
            console.log(`    ${s.statementCode.padEnd(12)} [COARSE FILTERED]`);
          } else {
            const tag = s.alignedCount > 0 ? `ALIGNED ${s.alignedCount}/${s.totalCount}` : `not aligned 0/${s.totalCount}`;
            console.log(`    ${s.statementCode.padEnd(12)} [${tag}]`);
          }
        }
      }

      console.log('\n════ COARSE FILTER ANALYSIS ════');
      const areaGT = groundTruth.byQuestion.find((q) => q.question === AREA_QUESTION)!;
      const areaFiltered = filtered.byQuestion.find((q) => q.question === AREA_QUESTION)!;

      let falseNegatives = 0;
      for (const gtStd of areaGT.standards) {
        const filteredStd = areaFiltered.standards.find((s) => s.statementCode === gtStd.statementCode)!;
        const wasAligned = gtStd.alignedCount > 0;
        const wasFiltered = filteredStd.coarseFiltered === true;
        const status = wasFiltered && wasAligned ? '❌ FALSE NEGATIVE' :
                       wasFiltered ? '○ filtered (correctly — not aligned)' :
                       wasAligned ? '✓ passed through (correctly — aligned)' :
                       '✓ passed through (not aligned, detail eval confirmed)';
        console.log(`  ${gtStd.statementCode.padEnd(12)} aligned=${wasAligned} filtered=${wasFiltered}  ${status}`);
        if (wasFiltered && wasAligned) falseNegatives++;
      }
      console.log(`\nFalse negatives: ${falseNegatives}/${MD_C_7_FAMILY.length}`);

      // ── Ground truth assertions ────────────────────────────────────────────

      const find = (code: string) => areaGT.standards.find((s) => s.statementCode === code)!;

      // 3.MD.C.7 — parent standard: "use multiplication and addition to find area"
      //   Area L-shape requires adding two rectangles → strongly aligned
      const s7 = find('3.MD.C.7');
      expect(s7.totalCount).toBeGreaterThan(0);
      expect(s7.alignedCount, '3.MD.C.7 should align strongly (all LCs)').toBe(s7.totalCount);

      // 3.MD.C.7.a — "tiling" and "same result as multiplying side lengths"
      //   L-shape question does not ask students to tile or reason about tiling
      const s7a = find('3.MD.C.7.a');
      expect(s7a.totalCount).toBeGreaterThan(0);
      expect(s7a.alignedCount, '3.MD.C.7.a should not align (about tiling, not decomposition)').toBe(0);

      // 3.MD.C.7.b — "multiply side lengths to find area of rectangles"
      //   Computing 8×3 and 4×2 is multiplication of side lengths → partially aligned
      const s7b = find('3.MD.C.7.b');
      expect(s7b.totalCount).toBeGreaterThan(0);
      expect(s7b.alignedCount, '3.MD.C.7.b should partially align (multiplication of sides present)').toBeGreaterThan(0);
      expect(s7b.alignedCount, '3.MD.C.7.b should not be fully aligned (distributive property LC not directly assessed)').toBeLessThan(s7b.totalCount);

      // 3.MD.C.7.c — "distributive property / a(b+c)"
      //   L-shape uses decomposition and addition but does not explicitly model a(b+c)
      const s7c = find('3.MD.C.7.c');
      expect(s7c.totalCount).toBeGreaterThan(0);
      expect(s7c.alignedCount, '3.MD.C.7.c should not align (about distributive property, not rectilinear area)').toBe(0);

      // 3.MD.C.7.d — "area additive / decompose rectilinear figures" — canonical match
      //   L-shape is the textbook example of rectilinear decomposition
      const s7d = find('3.MD.C.7.d');
      expect(s7d.totalCount).toBeGreaterThan(0);
      expect(s7d.alignedCount, '3.MD.C.7.d should align strongly (all LCs)').toBe(s7d.totalCount);

      // Unrelated question must not align to any standard
      const unrelatedGT = groundTruth.byQuestion.find((q) => q.question === UNRELATED_QUESTION)!;
      for (const s of unrelatedGT.standards) {
        expect(s.alignedCount, `"12 + 7" should not align to ${s.statementCode}`).toBe(0);
      }

      // Coarse filter must not produce false negatives on the area question
      expect(falseNegatives, 'Coarse filter must not discard any aligned standard').toBe(0);
    },
  );
});
