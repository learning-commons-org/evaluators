import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  clean: true,
  sourcemap: true,
  // The data tables are string literals in generated modules rather than files read at
  // runtime, so the package works under any bundler and in the browser without fs.
  splitting: false,
  treeshake: true,
});
