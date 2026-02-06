import { defineConfig } from 'tsup';
import { copyFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: false, // Temporarily disable to test runtime
  splitting: false,
  sourcemap: true,
  clean: true,
  treeshake: true,
  minify: false,
  external: ['ai', '@ai-sdk/openai', '@ai-sdk/anthropic', '@ai-sdk/google'],
  async onSuccess() {
    // Copy prompt txt files from parent repo to dist/prompts
    const sourcePromptsDir = join(__dirname, '../../evals/prompts');
    const destPromptsDir = join(__dirname, 'dist/prompts');

    // Create directory structure
    mkdirSync(join(destPromptsDir, 'vocabulary'), { recursive: true });
    mkdirSync(join(destPromptsDir, 'sentence-structure'), { recursive: true });
    mkdirSync(join(destPromptsDir, 'grade-level-appropriateness'), { recursive: true });

    // Copy vocabulary prompts
    const vocabFiles = [
      'background-knowledge.txt',
      'grades-3-4-system.txt',
      'grades-3-4-user.txt',
      'other-grades-system.txt',
      'other-grades-user.txt',
    ];
    for (const file of vocabFiles) {
      copyFileSync(
        join(sourcePromptsDir, 'vocabulary', file),
        join(destPromptsDir, 'vocabulary', file)
      );
    }

    // Copy sentence structure prompts
    const sentStructFiles = [
      'analysis-system.txt',
      'analysis-user.txt',
      'complexity-system.txt',
      'complexity-user.txt',
      'rubric-grade-3.txt',
      'rubric-grade-4.txt',
      'rubric-grades-5-12.txt',
    ];
    for (const file of sentStructFiles) {
      copyFileSync(
        join(sourcePromptsDir, 'sentence-structure', file),
        join(destPromptsDir, 'sentence-structure', file)
      );
    }

    // Copy GLA prompts
    const glaFiles = ['system.txt', 'user.txt'];
    for (const file of glaFiles) {
      copyFileSync(
        join(sourcePromptsDir, 'grade-level-appropriateness', file),
        join(destPromptsDir, 'grade-level-appropriateness', file)
      );
    }

    console.log('✓ Copied prompt files to dist/prompts');
  },
});
