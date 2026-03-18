# Grade Aligner

Takes a text passage and a target grade, and rewrites the text until it reads at that grade level. Each rewrite is independently verified before being accepted — the process only advances when the evaluation confirms progress.

```
Source text (grade 10) + target grade 5  →  Aligned text (grade 5)
                                          →  HTML report showing each step
```

## How It Works

```
SOURCE TEXT + TARGET GRADE N
         │
         ▼
┌────────────────────────────────┐
│  ASSESS                        │
│  • Determine current grade     │
│  • Identify what's driving     │
│    the complexity               │
└───────────────┬────────────────┘
                │
       Already at target? → done
                │
                ▼
┌────────────────────────────────┐
│  ADAPT & VERIFY (iterates)     │
│  1. Rewrite toward target      │
│  2. Evaluate grade level       │
│  3. Moved in right direction?  │
│     YES → record, continue     │
│     NO  → try different approach│
└───────────────┬────────────────┘
                │  Target grade reached
                ▼
         Return aligned text
```

Step size adapts to the gap — large rewrites for a 3-band gap, targeted edits for a 1-band gap. Only verified steps are recorded in the output.

## Installation

```bash
npm install @learning-commons/grade-aligner
```

You will also need API keys for the underlying evaluators:

```bash
npm install ai @ai-sdk/openai @ai-sdk/google
```

## Usage

```typescript
import { GradeAlignerAgent, generateReport } from '@learning-commons/grade-aligner';

const agent = new GradeAlignerAgent({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await agent.align(text, '5');
```

### Working with the result

```typescript
// The aligned text — ready to use directly
console.log(result.alignedText);

// Where the text started and ended
console.log(result.originalGlaBand); // e.g. "11-CCR"
console.log(result.finalGlaBand);    // e.g. "4-5"

// Each verified step taken to get there
for (const step of result.iterations) {
  console.log(step.glaBand);   // grade band after this step
  console.log(step.text);      // text at this step
  console.log(step.reasoning); // what changed and why
}

// Already-aligned texts have zero iterations
const wasAlreadyAligned = result.iterations.length === 0;
```

### Generating a report

Write an HTML report to a specific path:

```typescript
import { generateReport } from '@learning-commons/grade-aligner';

const reportPath = generateReport(result, './output/alignment-report.html');
```

If no path is provided, the report is written to a `reports/` directory in the current working directory with a timestamp filename.

### Configuration

```typescript
const agent = new GradeAlignerAgent({
  anthropicApiKey: '...',  // falls back to ANTHROPIC_API_KEY env var
  openaiApiKey: '...',     // falls back to OPENAI_API_KEY env var
  googleApiKey: '...',     // falls back to GOOGLE_API_KEY env var
  model: 'claude-opus-4-6', // default
  maxTurns: 10,             // default
});
```

Supported grades: 3–12.

## Running the demo

```bash
cd demos/grade-aligner
cp .env.example .env   # fill in API keys
npm install
npm run dev
```

To change the source text or target grade, edit `SOURCE_TEXT` and `TARGET_GRADE` at the top of `src/index.ts`.

Output:
- **Console** — aligned text + summary
- **`logs/`** — full run log with reasoning and evaluation results
- **`reports/`** — HTML report showing the original, each verified step, and the final aligned text

## See Also

- [`../differentiated-text-generator`](../differentiated-text-generator) — related demo that generates below/at/above variants from a single source
