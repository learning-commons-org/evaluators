import { describe, it, expect, beforeAll } from 'vitest';
import * as path from 'path';
import { BatchEvaluator, getAvailableGroups, parseCSV } from '../../src/batch/index.js';
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

const SKIP_INTEGRATION = !RUN_INTEGRATION;
const describeIntegration = SKIP_INTEGRATION ? describe.skip : describe;

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

    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    console.log('\n' + '='.repeat(80));
    console.log('BATCH EVALUATOR - INTEGRATION TEST');
    console.log('='.repeat(80));
    console.log(`Group: ${group.name} (${group.evaluatorIds.join(', ')})`);
    console.log('='.repeat(80));
  });

  it(
    'should process sample CSV end-to-end',
    async () => {
      const csvPath = path.join(__dirname, '../fixtures/batch-test.csv');
      const inputs: BatchInput[] = parseCSV(csvPath);

      console.log(`\n📊 Processing ${inputs.length} rows...`);

      const startTime = Date.now();
      const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
      const output = await evaluator.evaluate(inputs, group.id, (result) => {
        console.log(`  ✓ Row ${result.rowIndex} [${result.evaluatorId}] - ${result.status}: ${result.score || result.error}`);
      });
      const duration = Date.now() - startTime;

      console.log(`\n⏱  Completed in ${Math.round(duration / 1000)}s\n`);

      // Verify results structure
      expect(output).toBeDefined();
      expect(output.results).toBeDefined();
      expect(output.summary).toBeDefined();

      // Should have 2 rows × 3 evaluators = 6 results
      expect(output.results).toHaveLength(inputs.length * group.evaluatorIds.length);

      // Verify each result has expected fields
      for (const result of output.results) {
        expect(result.rowIndex).toBeGreaterThan(0);
        expect(result.text).toBeTruthy();
        expect(result.grade).toBeTruthy();
        expect(group.evaluatorIds).toContain(result.evaluatorId);
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
      const expectedTasks = inputs.length * group.evaluatorIds.length;
      expect(output.summary.totalTasks).toBe(expectedTasks);
      expect(output.summary.successful + output.summary.failed).toBe(expectedTasks);
      expect(output.summary.durationMs).toBeGreaterThan(0);
      for (const id of group.evaluatorIds) {
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
      const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;

      // Single row — verify all group evaluators ran
      const inputs: BatchInput[] = [
        { text: 'The cat sat on the mat.', grade: '3', rowIndex: 1, originalRow: { text: 'The cat sat on the mat.', grade: '3' } },
      ];

      console.log(`\n📊 Processing 1 row with ${group.evaluatorIds.length} evaluators...`);

      const output = await evaluator.evaluate(inputs, group.id, (result) => {
        console.log(`  ✓ ${result.evaluatorId} - ${result.status}: ${result.score || result.error}`);
      });

      // Should have 1 result per evaluator in the group
      expect(output.results).toHaveLength(group.evaluatorIds.length);

      // Verify every evaluator in the group produced a result
      const ranEvaluatorIds = output.results.map((r) => r.evaluatorId);
      for (const id of group.evaluatorIds) {
        expect(ranEvaluatorIds).toContain(id);
      }

      console.log('\n✅ All group evaluators ran\n');
    },
    TEST_TIMEOUT_MS
  );
});
