import 'dotenv/config';
// Suppress noisy AI SDK warnings (temperature not supported on reasoning models, system message placement)
process.env['AI_SDK_LOG_WARNINGS'] = 'false';
import pLimit from 'p-limit';
import { MathStandardsAlignmentEvaluator, type StandardAlignmentResult } from '@learning-commons/evaluators';
import { parseGradeFromStandard } from '@learning-commons/evaluators';

// ============================================================
// ✏️  EDIT HERE — put your question and standard below
// ============================================================

const QUESTION = `
A playground is shaped like an L. One part is a rectangle that is 8 feet
long and 3 feet wide. Attached to it is another rectangle that is 4 feet
long and 2 feet wide, with no overlap. What is the total area of the
playground in square feet?
`.trim();

const STATEMENT_CODE = '3.MD.C.7.d';

const RUNS = 20;        // how many times to run the evaluation
const CONCURRENCY = 5;  // how many calls to run at the same time

// ============================================================

const question = QUESTION;
const statementCode = STATEMENT_CODE;

// Derive grade from the standard code
let grade: string;
try {
  grade = parseGradeFromStandard(statementCode);
} catch {
  console.error(`Cannot parse grade from "${statementCode}". For non-standard codes, check the format.`);
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const evaluator = new MathStandardsAlignmentEvaluator({
  openaiApiKey: process.env.OPENAI_API_KEY!,
  platformApiKey: process.env.PLATFORM_API_KEY!,
});

const limit = pLimit(CONCURRENCY);

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

function hr(char = '─', width = 72) { return char.repeat(width); }

console.log('\n' + hr('═'));
console.log(' Consistency Check');
console.log(hr('═'));
console.log(` Question : "${question.length > 80 ? question.slice(0, 77) + '…' : question}"`);
console.log(` Standard : ${statementCode} (grade ${grade})`);
console.log(` Runs     : ${RUNS}  |  Concurrency: ${CONCURRENCY}`);
console.log(hr('═') + '\n');

let completed = 0;
const results: StandardAlignmentResult[] = [];

const renderProgress = () => {
  const filled = Math.round((completed / RUNS) * 30);
  const bar = '█'.repeat(filled) + '░'.repeat(30 - filled);
  process.stdout.write(`\r  [${bar}] ${completed}/${RUNS}`);
};

console.log('Running evaluations...');
renderProgress();

const tasks = Array.from({ length: RUNS }, (_, i) =>
  limit(async () => {
    const result = await evaluator.evaluate(question, grade, statementCode);
    completed++;
    renderProgress();
    return result;
  })
);

const settled = await Promise.allSettled(tasks);
console.log('\n');

const errors = settled.filter((s): s is PromiseRejectedResult => s.status === 'rejected');
if (errors.length > 0) {
  console.warn(`⚠  ${errors.length} run(s) failed and were excluded from analysis.`);
  if (errors.length === RUNS) {
    console.error('All runs failed. Check your API keys and network.');
    process.exit(1);
  }
}

const successful = settled
  .filter((s): s is PromiseFulfilledResult<StandardAlignmentResult> => s.status === 'fulfilled')
  .map((s) => s.value);

const totalRuns = successful.length;
const totalCount = successful[0]?.totalCount ?? 0;

// ---------------------------------------------------------------------------
// Aggregate per-LC
// ---------------------------------------------------------------------------

// alignedCounts[lcIndex] = how many runs said aligned=true
const alignedCounts: number[] = Array(totalCount).fill(0);
const descriptions: string[] = [];

for (const result of successful) {
  for (let i = 0; i < result.learningComponents.length; i++) {
    if (i === 0 && !descriptions[i]) descriptions[i] = result.learningComponents[i].description;
    else if (!descriptions[i]) descriptions[i] = result.learningComponents[i].description;
    if (result.learningComponents[i].aligned) alignedCounts[i]++;
  }
}

// Collect one sample reasoning for each LC (from a run where its aligned value matches the majority)
const sampleReasoning: { aligned: string; notAligned: string }[] = Array(totalCount)
  .fill(null)
  .map(() => ({ aligned: '', notAligned: '' }));

for (const result of successful) {
  for (let i = 0; i < result.learningComponents.length; i++) {
    const lc = result.learningComponents[i];
    if (lc.aligned && !sampleReasoning[i].aligned) sampleReasoning[i].aligned = lc.reasoning;
    if (!lc.aligned && !sampleReasoning[i].notAligned) sampleReasoning[i].notAligned = lc.reasoning;
  }
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

const ALWAYS = (n: number) => n === totalRuns;
const NEVER  = (n: number) => n === 0;
const label  = (n: number) => ALWAYS(n) ? '✅ ALWAYS aligned' : NEVER(n) ? '❌ NEVER aligned' : '⚠️  INCONSISTENT';
const pct    = (n: number) => `${n}/${totalRuns} (${Math.round(n / totalRuns * 100)}%)`;

console.log(hr('═'));
console.log(` Standard : ${statementCode}  |  Total runs analysed: ${totalRuns}`);
console.log(hr('═'));

let inconsistentCount = 0;
for (let i = 0; i < totalCount; i++) {
  const count = alignedCounts[i];
  const isInconsistent = !ALWAYS(count) && !NEVER(count);
  if (isInconsistent) inconsistentCount++;

  console.log(`\nLC ${i + 1}. ${descriptions[i]}`);
  console.log(`       Aligned : ${pct(count)}  ${label(count)}`);

  if (isInconsistent) {
    if (sampleReasoning[i].aligned) {
      console.log(`\n       Sample reasoning (aligned):`);
      console.log(`         "${sampleReasoning[i].aligned.slice(0, 200)}${sampleReasoning[i].aligned.length > 200 ? '…' : ''}"`);
    }
    if (sampleReasoning[i].notAligned) {
      console.log(`\n       Sample reasoning (not aligned):`);
      console.log(`         "${sampleReasoning[i].notAligned.slice(0, 200)}${sampleReasoning[i].notAligned.length > 200 ? '…' : ''}"`);
    }
  }
}

console.log('\n' + hr());
const consistentCount = totalCount - inconsistentCount;
console.log(` Summary: ${consistentCount}/${totalCount} LCs consistent across ${totalRuns} runs | ${inconsistentCount} inconsistent`);
if (inconsistentCount > 0) {
  console.log(` Tip: inconsistent LCs are where the question is borderline for that skill.`);
  console.log(`      Consider revising the question or treating those LCs as ambiguous.`);
}
console.log(hr() + '\n');
