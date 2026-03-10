import 'dotenv/config';
import { DifferentiationAgent } from './agent/index.js';
import type { DifferentiatedSet, TextVariant } from './agent/types.js';

// ─── Example passage ─────────────────────────────────────────────────────────
// Source: grade 6 science — how the water cycle works
const SOURCE_TEXT = `
The water cycle, also known as the hydrological cycle, describes the continuous movement
of water through Earth's systems. Solar energy drives evaporation, converting liquid water
from oceans, lakes, and rivers into water vapor that rises into the atmosphere. As this
vapor ascends to higher altitudes, it cools and undergoes condensation, forming tiny water
droplets that cluster around microscopic particles of dust and pollen to create clouds.
When sufficient droplets accumulate, precipitation occurs in the form of rain, snow, sleet,
or hail, depending on atmospheric temperature. Water that reaches Earth's surface either
flows across the land as surface runoff, infiltrates the soil to replenish groundwater
reserves, or is absorbed by plant roots and later released through transpiration. This
intricate cycling of water sustains all terrestrial ecosystems and regulates global climate
patterns over geological timescales.
`.trim();

const TARGET_GRADE = '6';

// ─── Output formatter ─────────────────────────────────────────────────────────

function printVariant(variant: TextVariant): void {
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`  ${variant.level.toUpperCase()} GRADE VARIANT  (grade ${variant.grade})`);
  console.log(`${'═'.repeat(60)}`);
  console.log(`\n${variant.text}\n`);
  console.log(`Rationale: ${variant.rationale}`);
}

function printSummary(result: DifferentiatedSet): void {
  console.log(`\n\n${'═'.repeat(60)}`);
  console.log('  DIFFERENTIATED SET — COMPLETE');
  console.log(`${'═'.repeat(60)}`);
  console.log(`Original grade target: ${result.targetGrade}`);
  console.log(`Original length: ${result.originalText.length} chars\n`);

  for (const variant of [result.below, result.at, result.above]) {
    printVariant(variant);
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const agent = new DifferentiationAgent();

  console.log('Source text:');
  console.log(SOURCE_TEXT);
  console.log(`\nTarget grade: ${TARGET_GRADE}\n`);

  const result = await agent.generate(SOURCE_TEXT, TARGET_GRADE);
  printSummary(result);

  console.log(`\nFull run log: ${agent.logPath}`);
}

main().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
