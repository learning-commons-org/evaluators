# Use Case: Differentiated Text Generation

## The Problem

EdTech platforms serving K-12 students need to deliver reading content that matches each student's reading level. A passage on the water cycle written for grade 6 is inaccessible to a grade 4 reader and unchallenging for a grade 8 reader. Platforms that want to support differentiated reading today have limited options:

1. **License separate content sets at each level** — expensive, hard to keep in sync, and different texts mean students can't engage with the same material together
2. **Build manual editorial workflows** — slow, requires reading specialists, doesn't scale to large content libraries
3. **Use a single LLM prompt to rewrite** — produces inconsistent results with no verification that the output actually lands at the target grade

None of these scale to the volume of content a modern adaptive learning platform requires.

---

## The Solution

This demo shows how an AI agent can take a single source passage and automatically produce three verified variants:

- **Below grade** (N-1): simplified vocabulary, shorter sentences, reduced background knowledge assumptions — same content, more accessible entry point
- **At grade** (N): calibrated to the target grade's academic vocabulary and sentence complexity norms
- **Above grade** (N+1): enriched with precise Tier 2/3 terminology, more complex sentence structures, higher conceptual density

All three variants preserve the same factual content, enabling platforms to serve differentiated reading experiences from a single piece of source content.

---

## Why This Is an Agentic Problem

Generating differentiated text is not a single prompt-response task. It requires:

1. **Assessment before generation** — the agent must first determine where the source text actually sits on the grade spectrum before deciding how to modify it. A text labeled "grade 6" may read at grade 9. Generating a "grade 5 version" from a grade 9 starting point requires multiple steps of simplification, not one.

2. **Iterative verification** — each generated variant must be independently evaluated against grade-level standards. A human editor would re-read and revise; the agent re-evaluates and revises.

3. **Multi-dimensional calibration** — vocabulary and sentence structure are scored independently. A text can have grade-appropriate vocabulary but overly complex sentence patterns, or vice versa. The agent must address both dimensions simultaneously.

4. **Non-linear paths** — when the source text is far from the target grade, the agent must incrementally climb or descend through intermediate grade levels, using each step as a checkpoint. Intermediate versions often become the below or above byproducts.

These properties — assessment, iteration, multi-step planning, and adaptive paths — make this a genuine use case for an agentic system rather than a single LLM call.

---

## How the Agent Works

```
Source text + target grade N
        │
        ▼
┌─────────────────────────────────┐
│  DISCOVERY                      │
│  • evaluate_text_complexity(N)  │  ← vocabulary + sentence scores
│  • evaluate_grade_level()       │  ← holistic grade band
└────────────────┬────────────────┘
                 │
        ┌────────▼────────┐
        │  GAP ANALYSIS   │
        │  Band = N?      │
        └────────┬────────┘
          ┌──────┴──────┐
       No gap        Gap exists
          │              │
          │    ┌─────────▼──────────┐
          │    │  INCREMENTAL STEPS │
          │    │  climb or descend  │
          │    │  one band at a time│
          │    └─────────┬──────────┘
          │              │
          └──────┬───────┘
                 ▼
┌─────────────────────────────────┐
│  VARIANT GENERATION             │
│  Draft below / at / above texts │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  VERIFICATION (per variant)     │
│  • evaluate_text_complexity     │  ← diagnostic signal
│  • evaluate_grade_level         │  ← pass/fail gate
│  Revise if GLA fails            │
└────────────────┬────────────────┘
                 │
                 ▼
        submit_variant ×3
```

The orchestrator is **Claude Opus 4.6** (Anthropic) with adaptive thinking. The evaluators run against **OpenAI GPT-4o** (sentence structure) and **Google Gemini** (vocabulary) — the same models used by the Learning Commons evaluator SDK.

---

## Integration Points for EdTech Developers

The `DifferentiationAgent` class exposes a single async method:

```typescript
const agent = new DifferentiationAgent();
const result = await agent.generate(sourceText, targetGrade);
// result.below, result.at, result.above — each with text + rationale
```

Developers can integrate this into:

- **Content ingestion pipelines** — run differentiation at upload time and store all three variants alongside the source
- **Adaptive reading engines** — generate variants on demand when a student's assessed reading level diverges from the content's target grade
- **Content authoring tools** — give curriculum authors an instant preview of how their passage reads at adjacent grade levels
- **Assessment scaffolding** — pair differentiated passages with grade-appropriate question sets generated from the same source

---

## Scope and Limitations

This demo is a proof of concept. It demonstrates the agentic pattern on a single passage with a single target grade. It does not yet handle:

- **Required vocabulary preservation** — platforms may need specific curriculum terms to appear in all variants
- **Subject-specific norms** — grade-level expectations differ between literary and informational text, and between subjects
- **Production scale** — latency and cost per run are not yet optimized for high-throughput content pipelines

See `docs/potential-improvements.md` for a full breakdown of known limitations and proposed next steps.
