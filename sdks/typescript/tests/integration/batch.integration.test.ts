import { describe, it, expect, beforeAll } from 'vitest';
import * as path from 'path';
import { BatchEvaluator, getFamily, parseCSV } from '../../src/batch/index.js';
import type { BatchInput } from '../../src/batch/index.js';

/**
 * Batch Evaluator Integration Tests
 *
 * Runs the full text-complexity group (all evaluators) against a sample CSV.
 * Verifies end-to-end batch flow with real API calls.
 *
 * To run:
 * ```bash
 * RUN_INTEGRATION_TESTS=true npm run test:integration
 * ```
 */

// If integration tests are explicitly requested, missing keys should be a hard failure
// so CI/CD misconfiguration is caught immediately rather than silently skipping.
const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';

if (RUN_INTEGRATION) {
  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  if (!process.env.GOOGLE_API_KEY) throw new Error('GOOGLE_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}

const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

// Test timeout: 2 minutes (generous for API calls)
const TEST_TIMEOUT_MS = 2 * 60 * 1000;

describeIntegration('Batch Evaluator - Integration', () => {
  let evaluator: BatchEvaluator;

  beforeAll(() => {
    evaluator = new BatchEvaluator({
      googleApiKey: process.env.GOOGLE_API_KEY!,
      openaiApiKey: process.env.OPENAI_API_KEY!,
      concurrency: 3,
      maxRetries: 2,
      telemetry: false,
    });

    const family = getFamily('text-complexity');
    console.log('\n' + '='.repeat(80));
    console.log('BATCH EVALUATOR - INTEGRATION TEST');
    console.log('='.repeat(80));
    console.log(`Group: ${family.name} (${family.members.map((m) => m.id).join(', ')})`);
    console.log('='.repeat(80));
  });

  it(
    'should process sample CSV end-to-end',
    async () => {
      const csvPath = path.join(__dirname, '../fixtures/batch-test.csv');
      const inputs: BatchInput[] = parseCSV(csvPath);

      console.log(`\n📊 Processing ${inputs.length} rows...`);

      const startTime = Date.now();
      const family = getFamily('text-complexity');
      const output = await evaluator.evaluate(inputs, family.id, {
        onProgress: (result) => {
          console.log(`  ✓ Row ${result.rowIndex} [${result.evaluatorId}] - ${result.status}: ${result.score || result.error}`);
        },
      });
      const duration = Date.now() - startTime;

      console.log(`\n⏱  Completed in ${Math.round(duration / 1000)}s\n`);

      // Verify results structure
      expect(output).toBeDefined();
      expect(output.results).toBeDefined();
      expect(output.summary).toBeDefined();

      // Should have 2 rows × 3 evaluators = 6 results
      expect(output.results).toHaveLength(inputs.length * family.members.map((m) => m.id).length);

      // Verify each result has expected fields
      for (const result of output.results) {
        expect(result.rowIndex).toBeGreaterThan(0);
        expect(result.text).toBeTruthy();
        expect(result.gradeLevel).toBeTruthy();
        expect(family.members.map((m) => m.id)).toContain(result.evaluatorId);
        expect(result.status).toMatch(/success|error/);
        expect(result.processingTimeMs).toBeGreaterThan(0);

        if (result.status === 'success') {
          expect(result.score).toBeTruthy();
          expect(result.reasoning).toBeTruthy();
        } else {
          expect(result.error).toBeTruthy();
        }
      }

      // Verify summary — 2 rows × 3 evaluators = 6 tasks
      const expectedTasks = inputs.length * family.members.map((m) => m.id).length;
      expect(output.summary.totalTasks).toBe(expectedTasks);
      expect(output.summary.successful + output.summary.failed).toBe(expectedTasks);
      expect(output.summary.durationMs).toBeGreaterThan(0);
      for (const id of family.members.map((m) => m.id)) {
        expect(output.summary.resultsPerEvaluator).toHaveProperty(id);
      }

      // Log summary
      console.log('📊 Summary:');
      console.log(`  Total: ${output.summary.totalTasks}`);
      console.log(`  Successful: ${output.summary.successful} ✓`);
      console.log(`  Failed: ${output.summary.failed} ✗`);
      console.log(`  Duration: ${Math.round(output.summary.durationMs / 1000)}s`);

      // At least 1 should succeed (allow for occasional API issues)
      expect(output.summary.successful).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS
  );

  it(
    'should run all evaluators in the group and include each in results',
    async () => {
      const family = getFamily('text-complexity');

      // Single row — verify all group evaluators ran
      const inputs: BatchInput[] = [
        { rowIndex: 1, columns: { text: 'The cat sat on the mat.', grade_level: '3' }, originalRow: { text: 'The cat sat on the mat.', grade_level: '3' } },
      ];

      console.log(`\n📊 Processing 1 row with ${family.members.map((m) => m.id).length} evaluators...`);

      const output = await evaluator.evaluate(inputs, family.id, {
        onProgress: (result) => {
          console.log(`  ✓ ${result.evaluatorId} - ${result.status}: ${result.score || result.error}`);
        },
      });

      // Should have 1 result per evaluator in the group
      expect(output.results).toHaveLength(family.members.map((m) => m.id).length);

      // Verify every evaluator in the group produced a result
      const ranEvaluatorIds = output.results.map((r) => r.evaluatorId);
      for (const id of family.members.map((m) => m.id)) {
        expect(ranEvaluatorIds).toContain(id);
      }

      console.log('\n✅ All group evaluators ran\n');
    },
    TEST_TIMEOUT_MS
  );
});
