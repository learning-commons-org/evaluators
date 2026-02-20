import { describe, it, expect, afterEach } from 'vitest';
import { mkdirSync, writeFileSync, existsSync, rmSync, readFileSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import { randomUUID } from 'crypto';

describe('copy-prompts script', () => {
  const testFolderName = `__test-${randomUUID()}__`;
  const testEvalDir = join(process.cwd(), '../../evals/prompts', testFolderName);
  const testSrcDir = join(process.cwd(), 'src/prompts', testFolderName);
  const testFile = 'test-prompt.txt';
  const testContent = 'Test prompt content';

  afterEach(() => {
    // Cleanup: Remove test directories from both locations
    if (existsSync(testEvalDir)) rmSync(testEvalDir, { recursive: true, force: true });
    if (existsSync(testSrcDir)) rmSync(testSrcDir, { recursive: true, force: true });
  });

  it('should automatically copy new prompt directories and files', () => {
    // 1. Create test folder and file in evals/prompts
    mkdirSync(testEvalDir, { recursive: true });
    writeFileSync(join(testEvalDir, testFile), testContent);

    // 2. Run copy-prompts script
    execSync('npm run copy-prompts', { stdio: 'pipe' });

    // 3. Verify folder and file were copied to src/prompts
    expect(existsSync(testSrcDir)).toBe(true);
    expect(existsSync(join(testSrcDir, testFile))).toBe(true);

    // 4. Verify content matches
    const copiedContent = readFileSync(join(testSrcDir, testFile), 'utf-8');
    expect(copiedContent).toBe(testContent);
  });

  it('should only copy .txt files and skip other file types', () => {
    // 1. Create test folder with multiple file types
    mkdirSync(testEvalDir, { recursive: true });
    writeFileSync(join(testEvalDir, 'prompt.txt'), 'Valid prompt');
    writeFileSync(join(testEvalDir, '__pycache__.pyc'), 'Python cache');
    writeFileSync(join(testEvalDir, '.DS_Store'), 'Mac metadata');
    writeFileSync(join(testEvalDir, 'README.md'), 'Documentation');

    // 2. Run copy-prompts script
    execSync('npm run copy-prompts', { stdio: 'pipe' });

    // 3. Verify only .txt file was copied
    expect(existsSync(join(testSrcDir, 'prompt.txt'))).toBe(true);
    expect(existsSync(join(testSrcDir, '__pycache__.pyc'))).toBe(false);
    expect(existsSync(join(testSrcDir, '.DS_Store'))).toBe(false);
    expect(existsSync(join(testSrcDir, 'README.md'))).toBe(false);
  });
});
