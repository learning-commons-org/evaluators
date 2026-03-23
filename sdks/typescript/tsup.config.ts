import { defineConfig, type Options } from 'tsup';

const sharedConfig: Partial<Options> = {
  format: ['esm', 'cjs'],
  splitting: false,
  sourcemap: true,
  treeshake: true,
  minify: false,
  external: ['ai', '@ai-sdk/openai', '@ai-sdk/anthropic', '@ai-sdk/google'],
  loader: {
    '.txt': 'text',  // Inline prompt .txt files as strings at build time
    '.html': 'text', // Inline HTML report templates as strings at build time
  },
};

export default defineConfig([
  {
    ...sharedConfig,
    entry: ['src/index.ts', 'src/batch/index.ts'],
    dts: true,
    clean: true,
  },
  {
    ...sharedConfig,
    entry: { 'batch/cli': 'src/batch/cli.ts' },
    format: ['esm'],
    dts: false,
    clean: false, // Don't wipe library output
    banner: { js: '#!/usr/bin/env node' },
  },
]);
