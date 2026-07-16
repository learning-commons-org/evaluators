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

const app = express();
app.use(express.json());

app.get('/api/jurisdictions', (_req, res) => {
  res.json(Object.values(Jurisdiction));
});

app.get('/api/standards', async (req, res) => {
  const { grade, jurisdiction } = req.query;
  if (typeof grade !== 'string' || typeof jurisdiction !== 'string') {
    res.status(400).json({ error: 'grade and jurisdiction query params are required' });
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
    !Array.isArray(statementCodes) ||
    statementCodes.length === 0 ||
    !Object.values(Jurisdiction).includes(jurisdiction)
  ) {
    res.status(400).json({ error: 'question, statementCodes (non-empty array), and a valid jurisdiction are required' });
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
