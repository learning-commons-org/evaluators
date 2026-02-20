import { defineConfig } from 'tsup';
import { cpSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  treeshake: true,
  minify: false,
  external: ['ai', '@ai-sdk/openai', '@ai-sdk/anthropic', '@ai-sdk/google'],
  async onSuccess() {
    // Copy all prompt .txt files from parent repo to dist/prompts
    const sourcePromptsDir = join(__dirname, '../../evals/prompts');
    const destPromptsDir = join(__dirname, 'dist/prompts');

    cpSync(sourcePromptsDir, destPromptsDir, {
      recursive: true,
      force: true,
      filter: (src) => {
        try {
          const isDirectory = statSync(src).isDirectory();
          if (isDirectory) return true;
          return src.endsWith('.txt');
        } catch {
          return false;
        }
      },
    });

    console.log('✓ Copied prompt files to dist/prompts');
  },
});
