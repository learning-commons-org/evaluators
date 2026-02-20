import { defineConfig } from 'vitest/config';
import type { Plugin } from 'vite';

function txtPlugin(): Plugin {
  return {
    name: 'txt-loader',
    transform(code, id) {
      if (!id.endsWith('.txt')) return;
      return {
        code: `export default ${JSON.stringify(code)};`,
        map: null,
      };
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
