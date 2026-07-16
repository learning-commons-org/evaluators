import 'dotenv/config';
import express from 'express';
import { MathStandardsAlignmentEvaluator, Jurisdiction } from '@learning-commons/evaluators';
import { listStandards } from './kg.js';

const { ANTHROPIC_API_KEY, PLATFORM_API_KEY } = process.env;
if (!ANTHROPIC_API_KEY || !PLATFORM_API_KEY) {
  console.error('Missing ANTHROPIC_API_KEY or PLATFORM_API_KEY — copy .env.example to .env and fill in both keys.');
  process.exit(1);
}

const evaluator = new MathStandardsAlignmentEvaluator({
  anthropicApiKey: ANTHROPIC_API_KEY,
  platformApiKey: PLATFORM_API_KEY,
});

const GRADES = new Set(['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);
const JURISDICTIONS = new Set<string>(Object.values(Jurisdiction));
const MAX_QUESTION_LENGTH = 10_000;

const app = express();
app.use(express.json());

app.get('/api/jurisdictions', (_req, res) => {
  res.json([...JURISDICTIONS]);
});

app.get('/api/standards', async (req, res) => {
  const { grade, jurisdiction } = req.query;
  if (typeof grade !== 'string' || !GRADES.has(grade)) {
    res.status(400).json({ error: 'grade must be one of K, 1–12' });
    return;
  }
  if (typeof jurisdiction !== 'string' || !JURISDICTIONS.has(jurisdiction)) {
    res.status(400).json({ error: 'jurisdiction must be a supported Jurisdiction value' });
    return;
  }
  try {
    res.json(await listStandards(grade, jurisdiction, PLATFORM_API_KEY));
  } catch (err) {
    res.status(500).json({ error: err instanceof Error ? err.message : String(err) });
  }
});

app.post('/api/evaluate', async (req, res) => {
  const { question, statementCodes, jurisdiction } = req.body ?? {};
  if (
    typeof question !== 'string' ||
    question.trim().length === 0 ||
    question.length > MAX_QUESTION_LENGTH ||
    !Array.isArray(statementCodes) ||
    statementCodes.length === 0 ||
    !statementCodes.every((c) => typeof c === 'string' && c.length > 0) ||
    !JURISDICTIONS.has(jurisdiction)
  ) {
    res.status(400).json({
      error: `question (non-empty, ≤${MAX_QUESTION_LENGTH} chars), statementCodes (non-empty array of strings), and a valid jurisdiction are required`,
    });
    return;
  }
  try {
    const results = await evaluator.evaluateItems(
      [{ question, statementCodes }],
      jurisdiction as Jurisdiction,
    );
    res.json(results);
  } catch (err) {
    res.status(500).json({ error: err instanceof Error ? err.message : String(err) });
  }
});

const PORT = 3001;
app.listen(PORT, () => {
  console.log(`API server listening on http://localhost:${PORT}`);
});
