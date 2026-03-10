# Potential Improvements

This document captures known design limitations and proposed improvements identified through real-world analysis of the differentiated text generator agent.

---

## 1. GLA Band Granularity Is Too Coarse (High Priority)

**Problem**

The Grade Level Appropriateness evaluator returns bands (`K-1`, `2-3`, `4-5`, `6-8`, `9-10`, `11-CCR`), not specific grades. The `6-8` band spans three grade levels, meaning the `at` (grade 6) and `above` (grade 7) variants can both return `6-8` and be indistinguishable at the gate level. Similarly, the `below` variant for a grade 6 target may land in `4-5` rather than the intended grade 5 — the current prompt accepts "one band lower" which is too permissive for classroom use.

**Proposed Fix**

Use TextComplexity scores as a within-band differentiator rather than treating them as non-gates entirely. Specifically:
- GLA confirms the correct band (coarse filter)
- TextComplexity vocabulary and sentence scores confirm the variant is positioned at the right end of the band (fine-grained signal)

Example: both `at` (grade 6) and `above` (grade 7) land in `6-8`, but the `above` variant should score higher on vocabulary complexity at grade 7 than the `at` variant scores at grade 6.

---

## 2. No Programmatic Enforcement of Evaluation Before Submit (High Priority)

**Problem**

The `submit_variant` tool has no code-level check that `evaluate_text_complexity` and `evaluate_grade_level` were actually called for the submitted text. The system prompt instructs the model to evaluate first, but this is advisory — a future model version or a model under latency pressure could skip evaluations and submit directly.

**Proposed Fix**

Track evaluation state in the `executeTool` handler. Before accepting a `submit_variant` call, verify that both evaluators were called for the same text (e.g., by hashing the text and checking a per-run evaluation registry).

```typescript
// Pseudocode
const evaluated = new Map<string, { complexity: boolean; gradeLevel: boolean }>();

case 'evaluate_text_complexity':
  const hash = hashText(input.text);
  evaluated.get(hash)?.complexity = true;

case 'submit_variant':
  const hash = hashText(input.text);
  if (!evaluated.get(hash)?.complexity || !evaluated.get(hash)?.gradeLevel) {
    return JSON.stringify({ accepted: false, reason: 'Both evaluations must pass before submitting.' });
  }
```

---

## 3. Incremental Stepping Strategy Is Untested (Medium Priority)

**Problem**

The system prompt describes a multi-step climb/descend strategy for texts that are far from the target grade (e.g., an 11-CCR passage being differentiated for grade 4). This path has never been exercised — all testing has used passages already within or adjacent to the target band. The incremental logic exists only as prompt instructions with no integration tests.

**Proposed Fix**

Add integration test cases covering large grade gaps:
- A grade 11 passage targeted at grade 4 (descend across 4 bands)
- A grade 2 passage targeted at grade 9 (climb across 3 bands)
- Assert that intermediate texts are captured as byproducts and that the final variants land in the correct bands

---

## 4. Verification Phase Drafts All Variants Before Seeing Feedback (Medium Priority)

**Problem**

In turn 2, the agent drafts all three variants and submits 6 tool calls (3 texts × 2 evals) in a single parallel batch. This is efficient but means all drafts are committed before any evaluation feedback is received. If a variant fails, the agent spends an extra round-trip revising it — but by then the other variants have already been locked in, meaning a revision to one might diverge from the others in style or register.

**Proposed Fix**

Evaluate the `at` variant first, then use its confirmed vocabulary and sentence profile as an anchor for drafting `below` and `above`. This produces more coherent variants relative to each other and reduces the chance of needing revision loops.

---

## 5. No Semantic Drift Detection (Medium Priority)

**Problem**

When simplifying or elevating a text, the agent may drop key terms or concepts. In the current demo, simplification for grade 5 removed "transpiration," "geological timescales," and "terrestrial ecosystems" entirely. A science teacher may consider some of these non-negotiable vocabulary targets for their curriculum. Nothing checks that factual content or required terminology was preserved.

**Proposed Fix**

Two options:

1. **Input constraint**: Allow callers to pass a list of required terms that must appear in all variants. Enforce this in the `submit_variant` tool before accepting.

2. **Semantic similarity check**: After submission, run a lightweight similarity comparison between the source text and each variant to flag significant content drift. This could be a simple keyword overlap check rather than a full LLM call.

---

## 6. Cost and Latency Are Not Production-Ready (Medium Priority)

**Problem**

A single run involves multiple expensive calls:
- Claude Opus 4.6 with adaptive thinking (orchestration) — the most expensive model
- OpenAI GPT-4o (sentence structure evaluator) — called per evaluation
- Google Gemini (vocabulary evaluator) — called per evaluation

A typical run makes 6–10 evaluator calls across 2–4 turns. At classroom scale (30 passages per class, multiple classes per week), the cost and 30–90 second latency per run are prohibitive.

**Proposed Fix**

- **Cache evaluator results** by text hash — the same text evaluated twice at the same grade should return the cached result
- **Use cheaper models for evaluators** during iteration, reserving the full models for final verification
- **Batch generation**: run multiple source texts through the agent concurrently rather than sequentially
- **Async/webhook pattern**: for production, run the agent asynchronously and notify the caller when results are ready rather than holding an open connection

---

## 7. Failure Modes Are Abrupt (Low Priority)

**Problem**

Three failure modes produce hard errors with no partial results:
1. The agent hits `maxTurns` (40) without completing all three variants — throws `Error: Agent did not produce all variants. Missing: below`
2. An evaluator API call fails (rate limit, timeout) — the entire agent run fails with no retry
3. A level is submitted twice — the second silently overwrites the first with no warning

**Proposed Fix**

- Return partial results when `maxTurns` is reached, indicating which variants were completed
- Add retry logic with exponential backoff for evaluator API calls (the `@anthropic-ai/sdk` handles this for the Anthropic client automatically, but the OpenAI/Google evaluators do not)
- Add a duplicate-submission guard in `executeTool`: return a warning result if a level has already been submitted rather than silently overwriting
