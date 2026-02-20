import { defineConfig } from 'vitest/config';
import { resolve } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Vitest configuration for testing the built distribution
 *
 * This config is used in CI to test the actual package that will be published.
 * It remaps imports from src/ to dist/index.js since the build bundles everything.
 *
 * Usage: vitest run --config vitest.ci.config.ts
 */
export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/integration/**/*.test.ts'],
    testTimeout: 120000, // 2 minutes for integration tests with LLM calls
  },
  resolve: {
    alias: [
      // Remap all src/evaluators imports to the bundled dist/index.js
      // Example: ../../src/evaluators/vocabulary.js → ../../dist/index.js
      {
        find: /^.*\/src\/evaluators\/.*\.js$/,
        replacement: resolve(__dirname, './dist/index.js'),
      },
    ],
  },
});
