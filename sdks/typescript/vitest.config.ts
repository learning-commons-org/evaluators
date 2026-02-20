import { defineConfig } from 'vitest/config';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import type { Plugin } from 'vite';

function txtPlugin(): Plugin {
  return {
    name: 'txt-loader',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!source.endsWith('.txt') || !importer) return;
      return resolve(dirname(importer), source);
    },
    load(id) {
      if (!id.endsWith('.txt')) return;
      return `export default ${JSON.stringify(readFileSync(id, 'utf-8'))};`;
    },
  };
}

export default defineConfig({
  plugins: [txtPlugin()],
  test: {
    globals: true,
    environment: 'node',
    passWithNoTests: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'dist/',
        'tests/',
        '**/*.config.ts',
        '**/*.d.ts',
      ],
    },
  },
});
