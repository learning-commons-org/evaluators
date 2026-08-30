import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  validateOutputDir,
  KEY_CONFIG,
  resolveKeySource,
  isEntryPoint,
} from '../../../src/batch/cli.js';
import { Provider } from '../../../src/batch/index.js';

/**
 * The CLI's decisions, exercised without running the CLI.
 *
 * `cli.ts` exported nothing and called `process.exit()` inline, so none of it could be
 * imported — 415 lines of the thing partners actually run, with no coverage. These cover the
 * parts that decide something: whether output can be written, and where a credential comes
 * from. The prompting and the exiting stay in `main`, which is the part a test should not
 * reach into.
 */

let workspace: string;

beforeEach(() => {
  workspace = mkdtempSync(join(tmpdir(), 'lc-cli-test-'));
});

afterEach(() => {
  // Restore write permission first, or the cleanup itself fails on the read-only case.
  try {
    chmodSync(workspace, 0o755);
  } catch {
    // Already gone or never restricted.
  }
  rmSync(workspace, { recursive: true, force: true });
});

describe('validateOutputDir', () => {
  it('accepts a directory that exists and is writable', () => {
    expect(validateOutputDir(workspace)).toBe(true);
  });

  it('accepts a directory that does not exist yet if its parent is writable', () => {
    // The CLI creates the directory itself, so a missing leaf is fine.
    expect(validateOutputDir(join(workspace, 'results'))).toBe(true);
  });

  it('rejects an empty or whitespace-only path', () => {
    expect(validateOutputDir('')).toBe('Output directory cannot be empty');
    expect(validateOutputDir('   ')).toBe('Output directory cannot be empty');
  });

  it('rejects a path that exists but is a file', () => {
    const file = join(workspace, 'notadir.txt');
    writeFileSync(file, '');

    expect(validateOutputDir(file)).toMatch(/exists but is not a directory/);
  });

  it('rejects a path whose parent does not exist', () => {
    // Two levels missing: the CLI creates one, not a chain.
    expect(validateOutputDir(join(workspace, 'missing', 'deeper'))).toMatch(
      /Parent directory does not exist/,
    );
  });

  it('rejects a directory it cannot write to', () => {
    const locked = join(workspace, 'locked');
    mkdirSync(locked);
    chmodSync(locked, 0o500);

    const result = validateOutputDir(locked);

    // Root ignores the permission bits, so only assert when the restriction took effect.
    // Match the EACCES wording exactly rather than accepting any failure: the point is that a
    // permission denial is reported as one, not as the generic `Cannot write` fallback.
    if (result !== true) {
      expect(result).toBe(`No write permission for directory: ${locked}`);
    }

    chmodSync(locked, 0o755);
  });

  it('leaves no test artefact behind on success', () => {
    // It probes writability by creating and deleting a file; a leaked probe would end up in
    // the user's results directory.
    expect(validateOutputDir(workspace)).toBe(true);

    expect(readdirSync(workspace)).toEqual([]);
  });
});

describe('KEY_CONFIG', () => {
  it('names an env var and a flag for every credential', () => {
    // Keyed by KeyKind, so an added provider is a compile error — this catches an entry
    // that exists but is half-filled.
    for (const [kind, config] of Object.entries(KEY_CONFIG)) {
      expect(config.envVar, `${kind} envVar`).toMatch(/^[A-Z][A-Z0-9_]+$/);
      expect(config.flag, `${kind} flag`).toMatch(/^--[a-z-]+$/);
      expect(config.label, `${kind} label`).toBeTruthy();
    }
  });

  it('covers every provider plus the Learning Commons key', () => {
    expect(Object.keys(KEY_CONFIG).sort()).toEqual(
      [...Object.values(Provider), 'learning-commons'].sort(),
    );
  });
});

describe('resolveKeySource', () => {
  it('prefers an explicit flag over the environment', () => {
    expect(resolveKeySource(Provider.OpenAI, 'from-flag', 'from-env')).toEqual({
      kind: 'resolved',
      key: 'from-flag',
    });
  });

  it('falls back to the environment when no flag is given', () => {
    expect(resolveKeySource(Provider.Google, undefined, 'from-env')).toEqual({
      kind: 'resolved',
      key: 'from-env',
    });
  });

  it('reports an empty flag as an error rather than asking', () => {
    // The caller meant to pass something; prompting over it would hide the mistake.
    const source = resolveKeySource(Provider.Anthropic, '', 'from-env');

    expect(source.kind).toBe('error');
    expect(source.kind === 'error' && source.reason).toMatch(
      /Anthropic API Key \(--anthropic-api-key\) was provided but is empty/,
    );
  });

  it('asks when the credential is absent, naming both alternatives', () => {
    const source = resolveKeySource('learning-commons', undefined, undefined);

    expect(source.kind).toBe('ask');
    expect(source.kind === 'ask' && source.reason).toMatch(
      /--learning-commons-api-key.*LEARNING_COMMONS_API_KEY/,
    );
  });

  it('treats an empty environment variable as absent', () => {
    // An exported-but-empty variable is a common shell accident and must not be sent as a key.
    expect(resolveKeySource(Provider.OpenAI, undefined, '').kind).toBe('ask');
  });
});

describe('isEntryPoint', () => {
  // The installed shape: `evaluators-batch` is a bin symlink onto dist/batch/cli.js.
  const installed = '/usr/local/lib/node_modules/@learning-commons/evaluators/dist/batch/cli.js';

  it('is true when the module is what node was asked to run', () => {
    expect(isEntryPoint(pathToFileURL(installed).href, installed)).toBe(true);
  });

  it('is true for a relative argv path pointing at the same file', () => {
    // node resolves argv[1] against cwd, so the raw string need not match the URL textually.
    const relative = './dist/batch/cli.js';
    expect(isEntryPoint(pathToFileURL(relative).href, relative)).toBe(true);
  });

  it('is false when another entry point imported the module', () => {
    // What happens in this very test file: the runner is argv[1], cli.js is just an import.
    expect(isEntryPoint(pathToFileURL(installed).href, '/repo/node_modules/vitest/vitest.mjs')).toBe(
      false,
    );
  });

  it('matches an entry point that is already a file URL', () => {
    // `node --entry-url file:///…` puts the URL itself in argv[1]. Feeding that through
    // pathToFileURL would mangle it, and the CLI would exit 0 having done nothing.
    const url = pathToFileURL(installed).href;
    expect(isEntryPoint(url, url)).toBe(true);
  });

  it('canonicalises a non-normalised file URL entry point', () => {
    expect(isEntryPoint('file:///tmp/cli.js', 'file:/tmp/cli.js')).toBe(true);
  });

  it('is false when there is no entry point at all', () => {
    // `node -e` and some embeddings leave argv[1] undefined.
    expect(isEntryPoint(pathToFileURL(installed).href, undefined)).toBe(false);
  });

  it('does not match a file whose path merely shares a prefix', () => {
    expect(isEntryPoint(pathToFileURL('/app/dist/batch/cli.js').href, '/app/dist/batch/cli.js.map'))
      .toBe(false);
  });
});
