import 'dotenv/config';
import { GradeAlignerAgent } from './agent/index.js';
import { generateReport } from './report.js';

// ─── Example passage ──────────────────────────────────────────────────────────
// Source: grade 10 biology — the human immune system
// Target: grade 5 (requires descending from 9-10 band to 4-5 band)
const SOURCE_TEXT = `
The human immune system constitutes a sophisticated network of biological mechanisms that
defends the organism against pathogenic microorganisms, including bacteria, viruses, and
parasites. Central to this defense are white blood cells, or leukocytes, which circulate
through the bloodstream and lymphatic vessels, continuously surveilling for foreign antigens.
Upon detecting a pathogen, specific lymphocytes known as B-cells synthesize immunoglobulins —
proteins commonly referred to as antibodies — that bind with precision to antigenic epitopes,
neutralizing the invader and marking it for destruction by phagocytic cells. This adaptive
immune response also generates immunological memory through long-lived plasma cells and
memory B-cells, enabling the organism to mount a more rapid and robust response upon
subsequent exposure to the same pathogen — the biological principle underlying vaccination.
`.trim();

const TARGET_GRADE = '5';

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const agent = new GradeAlignerAgent();

  console.log('Source text:');
  console.log(SOURCE_TEXT);
  console.log(`\nTarget grade: ${TARGET_GRADE}\n`);

  const result = await agent.align(SOURCE_TEXT, TARGET_GRADE);

  console.log('\n\n' + '═'.repeat(60));
  console.log('  ALIGNMENT COMPLETE');
  console.log('═'.repeat(60));
  console.log(`Original band:  ${result.originalGlaBand}`);
  console.log(`Target grade:   ${result.targetGrade}`);
  console.log(`Steps taken:    ${result.iterations.length === 0 ? 'none (already aligned)' : result.iterations.length}`);
  console.log('\nAligned text:\n');
  console.log(result.alignedText);
  console.log(`\nRationale: ${result.rationale}`);

  const reportPath = generateReport(result);
  console.log(`\nFull run log:    ${agent.logPath}`);
  console.log(`HTML report:     ${reportPath}`);
}

main().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
