#!/usr/bin/env tsx
// Separate from generate-schema.ts so that module can be imported without running. A
// run-when-executed-directly guard compares paths, and any mismatch (a symlink, say) skips
// main() and exits 0, which turns --check into a pass that checked nothing.
import { main } from './generate-schema.js';

main(process.argv.slice(2));
