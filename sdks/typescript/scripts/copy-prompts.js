#!/usr/bin/env node
/**
 * Copy prompt text files from evals/prompts to src/prompts for local testing
 *
 * This script recursively copies entire prompt directories, so new prompts
 * are automatically included without updating this script.
 *
 * In production builds, prompts are copied to dist/ by tsup.config.ts
 */

import { cpSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const rootDir = join(__dirname, '..');
const sourcePromptsDir = join(rootDir, '../../evals/prompts');
const destPromptsDir = join(rootDir, 'src/prompts');

console.log('📋 Copying prompt files for testing...');

try {
  // Copy entire prompts directory recursively
  cpSync(
    sourcePromptsDir,
    destPromptsDir,
    {
      recursive: true,
      force: true, // Overwrite existing files
      filter: (src) => {
        // Allow directories for traversal, but only copy .txt files
        try {
          const isDirectory = statSync(src).isDirectory();
          if (isDirectory) return true;
          return src.endsWith('.txt');
        } catch {
          // If stat fails, skip the file
          return false;
        }
      }
    }
  );

  console.log('✓ Copied prompt files to src/prompts');
} catch (error) {
  console.error('❌ Failed to copy prompt files:', error);
  process.exit(1);
}
