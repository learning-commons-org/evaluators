import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import { existsSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import type { Plugin } from 'vite';

// Vite rewrites a resolved file to a module URL before load(): `/src/...` inside
// the project root, `/@fs/...` outside it. Read the file either URL points at.
function filePathFromModuleId(id: string): string {
  const clean = id.split('?')[0];
  if (clean.startsWith('/@fs/')) return clean.slice('/@fs'.length);
  if (existsSync(clean)) return clean;
  if (clean.startsWith('/')) return resolve(process.cwd(), clean.slice(1));
  return clean;
}

function textModule(id: string, extension: '.txt' | '.html'): string | undefined {
  const clean = id.split('?')[0];
  if (!clean.endsWith(extension)) return;
  const contents = readFileSync(filePathFromModuleId(clean), 'utf-8');
  return `export default ${JSON.stringify(contents)};`;
}

function txtPlugin(): Plugin {
  return {
    name: 'txt-loader',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!source.endsWith('.txt') || !importer) return;
      return resolve(dirname(importer), source);
    },
    load(id) {
      return textModule(id, '.txt');
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
      return textModule(id, '.html');
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
        'scripts/',
      ],
    },
  },
}));
