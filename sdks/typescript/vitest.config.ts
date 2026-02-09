import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
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

function htmlPlugin(): Plugin {
  return {
    name: 'html-loader',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!source.endsWith('.html') || !importer) return;
      return resolve(dirname(importer), source);
    },
    load(id) {
      if (!id.endsWith('.html')) return;
      return `export default ${JSON.stringify(readFileSync(id, 'utf-8'))};`;
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [txtPlugin(), htmlPlugin()],
  test: {
    globals: true,
    environment: 'node',
    passWithNoTests: true,
    env: loadEnv(mode, process.cwd(), ''),
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
}));
