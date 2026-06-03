# Math Standards Alignment — Demo

This demo shows how to use the `MathStandardsAlignmentEvaluator` from the Learning Commons TypeScript SDK to check whether an assessment question aligns to a CCSS math standard.

## What it does

The evaluator:
1. Looks up the standard's **learning components** from the Learning Commons Knowledge Graph
2. Asks an LLM to judge whether the question directly assesses each component
3. Returns a per-component breakdown with reasoning and feedback

## Setup

### 1. Prerequisites

- Node.js 20 or later — check with `node --version`
- Access to an OpenAI API key
- A Learning Commons platform API key

### 2. Install dependencies

```bash
cd demos/math-standards-alignment
npm install
```

> This installs the SDK from the local `sdks/typescript` folder in this repository, along with the OpenAI provider.

### 3. Add your API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set:

```
OPENAI_API_KEY=sk-...         # your OpenAI key
PLATFORM_API_KEY=sk_prod_...  # your LC platform key
```

### 4. Run the demo

```bash
npm run demo
```

## What you'll see

The demo runs three examples against the standard **3.MD.C.7.d** ("Recognize area as additive. Find areas of rectilinear figures by decomposing them into non-overlapping rectangles"):

| Case | Question | Expected |
|---|---|---|
| 1 | L-shaped playground area problem | ✅ Strongly aligned |
| 2 | Simple rectangular garden area | ⚠️ Partially aligned |
| 3 | "What is 12 + 7?" | ❌ Not aligned |

For each case you'll see:
- Whether each learning component is covered
- The model's reasoning
- Feedback on how to revise the question if it doesn't align

## Trying your own examples

Open `src/demo.ts` and edit the `cases` array. You need:

- **question** — the assessment question text
- **grade** — the grade level (`"K"` through `"12"`)
- **standard** — the CCSS standard code (e.g. `"3.MD.C.7.d"`, `"5.NBT.A.1"`)

The standard code must match the grade — `"3.MD.C.7.d"` is a grade 3 standard, so `grade` must be `"3"`.

## API at a glance

```typescript
import { MathStandardsAlignmentEvaluator } from '@learning-commons/evaluators';

const evaluator = new MathStandardsAlignmentEvaluator({
  openaiApiKey: process.env.OPENAI_API_KEY,
  platformApiKey: process.env.PLATFORM_API_KEY,
});

// Evaluate one question against one standard
const result = await evaluator.evaluate(question, grade, statementCode);

console.log(result.statementCode);       // e.g. "3.MD.C.7.d"
console.log(result.alignedCount);        // number of learning components covered
console.log(result.totalCount);          // total learning components for this standard
console.log(result.learningComponents);  // per-LC: description, reasoning, aligned, feedback
```

For evaluating multiple questions against multiple standards, see the full SDK documentation.
