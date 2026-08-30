// How stable is the SRS1 verdict? The fixture expects 0; a full run has seen both.
import { StudentResponseSpecificityEvaluator } from './src/evaluators/feedback/ela-writing/student-response-specificity.js';

const STUDENT =
  'Some people think AI-powered pets are a good alternative to real pets because AI powered pets can be helpfull for people with health issues.';
const FEEDBACK = 'How so? Can you give an example? Check your spelling of helpful.';

const evaluator = new StudentResponseSpecificityEvaluator({
  openaiApiKey: process.env.OPENAI_API_KEY!,
  telemetry: false,
});

const RUNS = 10;
const scores: number[] = [];

for (let i = 0; i < RUNS; i += 1) {
  const { result } = await evaluator.evaluate({
    student_text: STUDENT,
    feedback_text: FEEDBACK,
  });
  scores.push(result.quality_score as number);
}

const zeros = scores.filter((s) => s === 0).length;
console.log(`scores over ${RUNS} runs: ${scores.join(', ')}`);
console.log(`expected 0: ${zeros}/${RUNS}  (${((100 * zeros) / RUNS).toFixed(0)}%)`);
