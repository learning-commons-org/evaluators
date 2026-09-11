import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  validateOutputDir,
  KEY_CONFIG,
  resolveKeySource,
  resolveKey,
  isEntryPoint,
} from '../../../src/batch/cli.js';
import prompts from 'prompts';

vi.mock('prompts', () => ({ default: vi.fn() }));
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

  it('matches a symlink pointing at the module, as an installed bin does', () => {
    // The regression this test exists for: `npm install` puts the bin in
    // node_modules/.bin as a symlink, so argv[1] is the link and import.meta.url is the
    // resolved target. Comparing them textually leaves the CLI exiting 0 in silence.
    const real = join(workspace, 'cli.js');
    const link = join(workspace, 'evaluators-batch');
    writeFileSync(real, '');
    symlinkSync(real, link);

    // realpathSync on the target too: macOS resolves /tmp through /private/tmp, and
    // import.meta.url would already be the fully resolved form.
    const moduleUrl = pathToFileURL(realpathSync(real)).href;

    expect(isEntryPoint(moduleUrl, link)).toBe(true);
  });

  it('is false for a symlink pointing at a different file', () => {
    // Resolving links must not turn every link into a match.
    const real = join(workspace, 'cli.js');
    const other = join(workspace, 'other.js');
    const link = join(workspace, 'link-to-other');
    writeFileSync(real, '');
    writeFileSync(other, '');
    symlinkSync(other, link);

    expect(isEntryPoint(pathToFileURL(realpathSync(real)).href, link)).toBe(false);
  });

  it('is false when argv[1] names something that does not exist', () => {
    // Resolution fails rather than throwing out of the guard and crashing at import.
    expect(isEntryPoint(pathToFileURL(installed).href, join(workspace, 'absent.js'))).toBe(false);
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

describe('resolveKey', () => {
  /** Stands in for `process.exit`, which is otherwise fatal to the test run. */
  class Exited extends Error {
    constructor(readonly code: number | undefined) {
      super(`exit ${code}`);
    }
  }

  let errors: string[];
  let logs: string[];

  beforeEach(() => {
    errors = [];
    logs = [];
    vi.mocked(prompts).mockReset();
    vi.spyOn(process, 'exit').mockImplementation((code) => {
      throw new Exited(code as number | undefined);
    });
    vi.spyOn(console, 'error').mockImplementation((...args) => void errors.push(args.join(' ')));
    vi.spyOn(console, 'log').mockImplementation((...args) => void logs.push(args.join(' ')));
    delete process.env.OPENAI_API_KEY;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete process.env.OPENAI_API_KEY;
  });

  it('returns the flag without reading the environment or asking', async () => {
    process.env.OPENAI_API_KEY = 'from-env';

    await expect(resolveKey(Provider.OpenAI, 'from-flag', true)).resolves.toBe('from-flag');
    expect(prompts).not.toHaveBeenCalled();
  });

  it('reads the environment when no flag is given', async () => {
    process.env.OPENAI_API_KEY = 'from-env';

    await expect(resolveKey(Provider.OpenAI, undefined, true)).resolves.toBe('from-env');
    expect(prompts).not.toHaveBeenCalled();
  });

  it('exits 1 on an empty flag even when it could have asked', async () => {
    await expect(resolveKey(Provider.OpenAI, '', true)).rejects.toThrow('exit 1');
    expect(errors.join('\n')).toContain('was provided but is empty');
    expect(prompts).not.toHaveBeenCalled();
  });

  it('exits 1 rather than hanging when it cannot ask', async () => {
    // The -y path: a prompt here would block a CI job forever instead of failing it.
    await expect(resolveKey(Provider.OpenAI, undefined, false)).rejects.toThrow('exit 1');
    expect(errors.join('\n')).toContain('running non-interactively');
    expect(prompts).not.toHaveBeenCalled();
  });

  /** Answers under whatever name the prompt declares, so the two cannot drift apart. */
  function answerPrompt(value: unknown) {
    vi.mocked(prompts).mockImplementation(async (question) => {
      const { name } = question as { name: string };
      return { [name]: value };
    });
  }

  it('asks for a missing credential and returns what was typed', async () => {
    answerPrompt('typed-by-hand');

    await expect(resolveKey(Provider.OpenAI, undefined, true)).resolves.toBe('typed-by-hand');
  });

  it('names the credential it is asking for', async () => {
    answerPrompt('typed-by-hand');

    await resolveKey(Provider.OpenAI, undefined, true);

    // A bare `:` prompt gives no clue which of four keys is wanted.
    expect(vi.mocked(prompts).mock.calls[0][0]).toMatchObject({ message: 'OpenAI API Key:' });
  });

  it('masks the credential while it is being typed', async () => {
    answerPrompt('typed-by-hand');

    await resolveKey(Provider.OpenAI, undefined, true);

    // A visible API key ends up in screen shares and terminal scrollback.
    expect(vi.mocked(prompts).mock.calls[0][0]).toMatchObject({ type: 'password' });
  });

  it('exits 0, not 1, when the user cancels the prompt', async () => {
    // Ctrl-C is a choice, not a failure, and a non-zero exit would fail a wrapping script.
    vi.mocked(prompts).mockResolvedValue({});

    await expect(resolveKey(Provider.OpenAI, undefined, true)).rejects.toThrow('exit 0');
    expect(logs.join('\n')).toContain('Cancelled.');
  });

  it('rejects an empty answer at the prompt', async () => {
    answerPrompt('k');
    await resolveKey(Provider.OpenAI, undefined, true);

    const { validate } = vi.mocked(prompts).mock.calls[0][0] as unknown as {
      validate: (v: string) => true | string;
    };
    expect(validate('')).toBe('OpenAI API Key is required');
    expect(validate('k')).toBe(true);
  });
});
