# Differentiated Text Generator

An agentic system that takes a text passage and a target grade, then produces three verified variants — below, at, and above grade level — using the Learning Commons evaluators as feedback tools.

## Why an agent?

A single LLM call cannot verify its own output against an independent rubric. This system uses three evaluators as ground truth:

- **VocabularyEvaluator** — scores lexical complexity relative to a grade (slightly → exceedingly complex)
- **SentenceStructureEvaluator** — scores syntactic complexity relative to a grade
- **GradeLevelAppropriatenessEvaluator** — independently determines the grade band of a text (no grade parameter — purely observational)

The agent modifies text, checks all three signals, and iterates until they agree. No single LLM call can do this.

## Process

```
INPUT: text + target grade N
          │
          ▼
┌─────────────────────────────────────┐
│           DISCOVERY PHASE           │
│                                     │
│  Run in parallel:                   │
│  • TextComplexity at grade N        │
│  • TextComplexity at grade N-1      │
│  • TextComplexity at grade N+1      │
│  • GradeLevelAppropriateness        │
│                                     │
│  → Determine actual grade band      │
│  → Compute gap: actual vs target    │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
  Gap = 0           Gap > 0
(text already      (text needs
 at grade N)        adjustment)
       │                │
       │                ▼
       │    ┌───────────────────────┐
       │    │   INCREMENTAL CLIMB   │
       │    │                       │
       │    │  grade K → K+1 → ...  │
       │    │  → N (if below)       │
       │    │                       │
       │    │  or                   │
       │    │                       │
       │    │  grade K → K-1 → ...  │
       │    │  → N (if above)       │
       │    │                       │
       │    │  Each step:           │
       │    │  1. Modify text       │
       │    │  2. Evaluate (vocab   │
       │    │     + sentence)       │
       │    │  3. Validate (GLA)    │
       │    │  4. Use reasoning     │
       │    │     to guide next     │
       │    │                       │
       │    │  Intermediate steps   │
       │    │  = natural byproducts │
       │    └───────────┬───────────┘
       │                │
       └───────┬────────┘
               │
               ▼
     "AT" variant confirmed
     (N-1 variant already in hand
      as byproduct of the climb)
               │
               ▼
┌─────────────────────────────────────┐
│         ABOVE VARIANT               │
│                                     │
│  Discovery at N+1 already ran.      │
│  Modify → Evaluate → GLA → iterate  │
└──────────────┬──────────────────────┘
               │
               ▼
OUTPUT: below (N-1) · at (N) · above (N+1)
        each with scores + reasoning
```

## TODO — Improvements

### Robustness

- **Semantic drift guard** — After multiple incremental steps, re-check factual fidelity against the original. Long modification chains can silently change meaning.
- **Convergence detection** — If two consecutive iterations produce the same scores, the agent is stuck. Trigger a strategy reset rather than retrying the same modification.
- **Overshoot handling** — Detect when a modification jumps past the target grade (e.g. 5→7 when targeting 6) and pull back rather than continuing forward.

### Performance

- **Adaptive step size** — Try jumping the full grade gap first. If it lands, done. If it overshoots, bisect. Binary search over grade levels reduces API calls significantly for large gaps.
- **Dimension-specific iteration** — If vocabulary passes but sentence structure doesn't, subsequent iterations should target only the failing dimension to avoid breaking what already works.
- **Parallel discovery** — N-1 and N+1 evaluations always run in parallel regardless of path length. Already in the design; must be enforced in implementation.

### Power

- **Reasoning accumulation** — Each step's evaluation reasoning is appended to the next modification prompt. The agent builds a growing, specific understanding of what is and isn't working in the text.
- **Modification diff log** — Track what changed at each step and why. Expose this as part of the output so the system is interpretable, not just functional.
- **Confidence signal** — Instead of binary pass/fail, report how many of the three dimensions passed. Gives the agent (and the user) a clearer picture of how close each iteration is to the target.
