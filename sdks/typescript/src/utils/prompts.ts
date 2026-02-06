import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Path to prompts directory
// When in src/utils/, go up one level. When bundled in dist/, stay in current dir.
const PROMPTS_DIR = __dirname.endsWith('utils')
  ? join(dirname(__dirname), 'prompts')
  : join(__dirname, 'prompts');

/**
 * Load a prompt file from the prompts directory
 * @param relativePath - Path relative to prompts directory (e.g., 'vocabulary/grades-3-4-system.txt')
 * @returns The prompt file contents as a string
 */
export function loadPrompt(relativePath: string): string {
  return readFileSync(join(PROMPTS_DIR, relativePath), 'utf-8');
}
