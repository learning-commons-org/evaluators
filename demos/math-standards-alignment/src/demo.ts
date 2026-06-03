import 'dotenv/config';
import { MathStandardsAlignmentEvaluator } from '@learning-commons/evaluators';

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const evaluator = new MathStandardsAlignmentEvaluator({
  openaiApiKey: process.env.OPENAI_API_KEY!,
  platformApiKey: process.env.PLATFORM_API_KEY!,
});

// ---------------------------------------------------------------------------
// Demo cases
// ---------------------------------------------------------------------------

// These three examples show the same standard (3.MD.C.7.d) evaluated against
// questions with different levels of alignment. 3.MD.C.7.d is the standard
// "Recognize area as additive. Find areas of rectilinear figures by
// decomposing them into non-overlapping rectangles."

const cases = [
  {
    label: 'Case 1 — Strong alignment',
    question:
      'A playground is shaped like an L. One part is a rectangle that is 8 feet ' +
      'long and 3 feet wide. Attached to it is another rectangle that is 4 feet ' +
      'long and 2 feet wide, with no overlap. What is the total area of the ' +
      'playground in square feet?',
    grade: '3',
    standard: '3.MD.C.7.d',
    why:
      'This question requires students to decompose an L-shape into two ' +
      'rectangles, compute each area, and add them — exactly what 3.MD.C.7.d asks for.',
  },
  {
    label: 'Case 2 — Partial alignment',
    question:
      'A rectangular garden is 6 meters long and 4 meters wide. What is the area?',
    grade: '3',
    standard: '3.MD.C.7.d',
    why:
      'This question uses area and multiplication but does not require ' +
      'decomposing a rectilinear figure — 3.MD.C.7.d only partially applies.',
  },
  {
    label: 'Case 3 — No alignment',
    question: 'What is 12 + 7?',
    grade: '3',
    standard: '3.MD.C.7.d',
    why:
      'This is a simple addition problem with no connection to area, rectangles, ' +
      'or rectilinear decomposition.',
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function hr(char = '─', width = 70) {
  console.log(char.repeat(width));
}

function printResult(label: string, why: string, result: Awaited<ReturnType<typeof evaluator.evaluate>>) {
  const pct = result.totalCount > 0
    ? Math.round((result.alignedCount / result.totalCount) * 100)
    : 0;
  const verdict =
    pct === 100 ? '✅ Strongly aligned' :
    pct > 0     ? '⚠️  Partially aligned' :
                  '❌ Not aligned';

  hr();
  console.log(`\n${label}`);
  console.log(`Why we expect this result: ${why}\n`);
  console.log(`Standard : ${result.statementCode} (grade ${result.grade})`);
  console.log(`Result   : ${verdict} — ${result.alignedCount} of ${result.totalCount} learning components covered\n`);

  for (const lc of result.learningComponents) {
    const icon = lc.aligned ? '  ✓' : '  ✗';
    console.log(`${icon} ${lc.description}`);
    console.log(`     Reasoning : ${lc.reasoning}`);
    if (!lc.aligned) {
      console.log(`     Feedback  : ${lc.feedback}`);
    }
    console.log();
  }
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

console.log('\n');
hr('═');
console.log(' Math Standards Alignment Evaluator — Demo');
console.log(' Evaluates whether an assessment question aligns to a CCSS math standard');
hr('═');
console.log('\nEach evaluation fetches the standard\'s learning components from the');
console.log('Learning Commons Knowledge Graph, then asks the model to judge whether');
console.log('the question directly assesses each component.\n');

for (const { label, question, grade, standard, why } of cases) {
  console.log(`\nRunning: ${label} ...`);
  const result = await evaluator.evaluate(question, grade, standard);
  printResult(label, why, result);
}

hr('═');
console.log(' Done. See src/demo.ts to try your own questions and standards.');
hr('═');
console.log();
