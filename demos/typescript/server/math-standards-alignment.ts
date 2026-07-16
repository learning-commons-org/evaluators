import type { Express, Request, Response } from 'express';
import { MathStandardsAlignmentEvaluator, Jurisdiction } from '@learning-commons/evaluators';
import { listStandards } from './kg.js';

const GRADES = new Set(['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);
const JURISDICTIONS = new Set<string>(Object.values(Jurisdiction));
const MAX_QUESTION_LENGTH = 10_000;

// Registers the Math Standards Alignment API routes. If the required keys are
// missing the routes still mount but return 503, so the rest of the demo
// (home page, other evaluators) runs without them.
export function registerMathStandardsAlignment(app: Express): void {
  const { ANTHROPIC_API_KEY, PLATFORM_API_KEY } = process.env;

  if (!ANTHROPIC_API_KEY || !PLATFORM_API_KEY) {
    const message =
      'Math Standards Alignment is disabled: set ANTHROPIC_API_KEY and PLATFORM_API_KEY in .env';
    console.warn(`⚠︎  ${message}`);
    const unavailable = (_req: Request, res: Response) => res.status(503).json({ error: message });
    app.get('/api/jurisdictions', unavailable);
    app.get('/api/standards', unavailable);
    app.post('/api/evaluate', unavailable);
    return;
  }

  const evaluator = new MathStandardsAlignmentEvaluator({
    anthropicApiKey: ANTHROPIC_API_KEY,
    platformApiKey: PLATFORM_API_KEY,
  });

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
}
