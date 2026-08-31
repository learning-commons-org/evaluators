/**
 * Packaging checks that `publint` and `attw` do not make.
 *
 * Both of those passed on four separate real defects: an unsatisfiable `zod` peer floor, an
 * `engines` range admitting Node versions where the CommonJS entry throws, a missing `main`
 * that makes legacy runtime resolution fail outright, and unbounded `>=` peer ranges. They
 * check the manifest's shape and how TypeScript resolves types; none of them installs the
 * declared floors or executes the built artifacts. These do.
 *
 * Run against a freshly packed tarball: `npm run verify:package`.
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf-8'));

const failures = [];
const notes = [];

function fail(check, detail) {
  failures.push(`${check}: ${detail}`);
  console.error(`  ✗ ${check}\n      ${detail.split('\n').join('\n      ')}`);
}
function pass(check, detail = '') {
  console.log(`  ✓ ${check}${detail ? ` — ${detail}` : ''}`);
}

function run(cmd, args, cwd) {
  return execFileSync(cmd, args, { cwd, encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] });
}

/** Pack once; every check reads or installs this exact artifact. */
function pack() {
  const out = run('npm', ['pack', '--silent'], ROOT).trim().split('\n').pop();
  return join(ROOT, out);
}

/**
 * Paths inside the tarball, `package/`-prefix stripped.
 *
 * Everything below asserts against these rather than against the working tree: a file can
 * exist in the repo and still be absent from the package, because `files` decides what
 * ships. Checking the repo would pass on exactly the regression these checks exist to catch.
 */
function tarballPaths(tarball) {
  return new Set(
    run('tar', ['tzf', tarball], ROOT)
      .split('\n')
      .map((l) => l.trim().replace(/^package\//, ''))
      .filter(Boolean),
  );
}

// ---------------------------------------------------------------------------
// 1. Peer ranges are bounded.
//
// An unbounded `>=` lets the next major of a peer install with no warning and break at
// run time, which is the one thing a peer range exists to prevent.
// ---------------------------------------------------------------------------
function checkPeerBounds() {
  const unbounded = Object.entries(pkg.peerDependencies ?? {}).filter(
    ([, range]) => /^>=?[^<]*$/.test(range.trim()) && !range.includes('<'),
  );
  if (unbounded.length > 0) {
    fail(
      'peer ranges are bounded',
      unbounded.map(([n, r]) => `${n}: "${r}" admits the next major`).join('\n'),
    );
    return;
  }
  pass('peer ranges are bounded');
}

// ---------------------------------------------------------------------------
// 2. The declared peer floors install together.
//
// Peers can contradict each other: `ai@7` requires `zod@^3.25.76 || ^4.1.8`, so a `zod`
// floor below 4.1.8 is not installable alongside it no matter what we declare.
// ---------------------------------------------------------------------------
function checkPeerFloorsInstall(tarball) {
  const floors = Object.entries(pkg.peerDependencies ?? {})
    .map(([name, range]) => {
      const m = range.match(/(\d+\.\d+\.\d+)/);
      return m ? `${name}@${m[1]}` : null;
    })
    .filter(Boolean);

  const dir = mkdtempSync(join(tmpdir(), 'verify-floors-'));
  try {
    writeFileSync(join(dir, 'package.json'), JSON.stringify({ name: 'f', private: true }) + '\n');
    run('npm', ['install', '--silent', tarball, ...floors], dir);
    pass('declared peer floors install together', floors.join(' '));
  } catch (e) {
    const out = `${e.stdout ?? ''}${e.stderr ?? ''}`;
    const reason = out.split('\n').filter((l) => /ERESOLVE|Found:|peer /.test(l)).slice(0, 4);
    fail('declared peer floors install together', [floors.join(' '), ...reason].join('\n'));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
// 3. `main` is present and exists.
//
// Resolvers without `exports` support (webpack 4, browserify, tools built on `resolve`)
// read `main` only. `attw` reports node10 green off `types` alone, so it cannot see this.
// ---------------------------------------------------------------------------
function checkMain(shipped) {
  if (!pkg.main) {
    fail('main is declared and shipped', 'absent — legacy resolvers cannot find the package at all');
    return;
  }
  const rel = pkg.main.replace(/^\.\//, '');
  if (!shipped.has(rel)) {
    fail('main is declared and shipped', `${pkg.main} is not in the tarball (check "files")`);
    return;
  }
  pass('main is declared and shipped', pkg.main);
}

/**
 * Every `exports` subpath needs a directory stub too, since a resolver that ignores
 * `exports` also has no way to find the subpath. `main` alone fixes only the root.
 */
function checkSubpathStubs(tarball, shipped) {
  const subpaths = Object.keys(pkg.exports ?? {}).filter(
    (k) => k.startsWith('./') && k !== './package.json',
  );
  const missing = [];
  for (const sub of subpaths) {
    const dir = sub.slice(2);
    const stubPath = `${dir}/package.json`;
    if (!shipped.has(stubPath)) {
      missing.push(`${sub}: ${stubPath} is not in the tarball (check "files")`);
      continue;
    }
    // Read it out of the tarball too, so a stub that ships but points nowhere is caught.
    const stub = JSON.parse(run('tar', ['xzOf', tarball, `package/${stubPath}`], ROOT));
    if (!stub.main) {
      missing.push(`${sub}: shipped stub declares no "main"`);
      continue;
    }
    const target = join(dir, stub.main).replace(/\\/g, '/');
    if (!shipped.has(target)) {
      missing.push(`${sub}: stub main "${stub.main}" resolves to ${target}, not in the tarball`);
    }
  }
  if (missing.length > 0) {
    fail('exports subpaths have legacy stubs', missing.join('\n'));
    return;
  }
  pass('exports subpaths have legacy stubs', subpaths.join(', ') || 'none');
}

// ---------------------------------------------------------------------------
// 4. `engines` excludes Node versions where `require()` of the CJS entry throws.
//
// The CJS build statically requires ESM-only packages, so it needs `require(esm)`:
// unflagged in 20.19+ and 22.12+, absent in 21.x and 22.0–22.11.
// ---------------------------------------------------------------------------
function checkEnginesAgainstRequireEsm() {
  const range = pkg.engines?.node ?? '';
  const broken = ['21.0.0', '22.0.0', '22.11.0'];
  const admitted = broken.filter((v) => satisfiesLoosely(range, v));
  if (admitted.length > 0) {
    fail(
      'engines excludes Nodes without require(esm)',
      `"${range}" admits ${admitted.join(', ')}, where requiring the CJS entry throws ERR_REQUIRE_ESM`,
    );
    return;
  }
  pass('engines excludes Nodes without require(esm)', range);
}

/** Minimal range test for the two forms we use, so this needs no dependency. */
function satisfiesLoosely(range, version) {
  const [maj, min] = version.split('.').map(Number);
  return range.split('||').some((partRaw) => {
    const part = partRaw.trim();
    let m = part.match(/^\^(\d+)\.(\d+)\.\d+$/);
    if (m) return maj === Number(m[1]) && min >= Number(m[2]);
    m = part.match(/^>=(\d+)\.(\d+)\.\d+$/);
    if (m) return maj > Number(m[1]) || (maj === Number(m[1]) && min >= Number(m[2]));
    return false;
  });
}

// ---------------------------------------------------------------------------
// 5. Both entry points load, from ESM and from CommonJS.
// ---------------------------------------------------------------------------
function checkRuntimeLoads(tarball) {
  const dir = mkdtempSync(join(tmpdir(), 'verify-load-'));
  try {
    writeFileSync(join(dir, 'package.json'), JSON.stringify({ name: 'l', private: true }) + '\n');
    // The peers the artifacts actually import at load time.
    run('npm', ['install', '--silent', tarball, 'ai', 'zod'], dir);

    writeFileSync(
      join(dir, 'load.cjs'),
      `const a = require('@learning-commons/evaluators');\n` +
        `const b = require('@learning-commons/evaluators/batch');\n` +
        `if (a.getEvaluators().length === 0 || b.getFamilies().length === 0) throw new Error('empty');\n` +
        `console.log('cjs ok');\n`,
    );
    writeFileSync(
      join(dir, 'load.mjs'),
      `import { getEvaluators } from '@learning-commons/evaluators';\n` +
        `import { getFamilies } from '@learning-commons/evaluators/batch';\n` +
        `if (getEvaluators().length === 0 || getFamilies().length === 0) throw new Error('empty');\n` +
        `console.log('esm ok');\n`,
    );

    run(process.execPath, [join(dir, 'load.mjs')], dir);
    pass('ESM require of both entry points');

    run(process.execPath, [join(dir, 'load.cjs')], dir);
    pass('CommonJS require of both entry points');

    // The CJS entry must not depend on this Node happening to have require(esm) unflagged,
    // beyond what `engines` promises. Reported as a note: it is the reason for check 4.
    try {
      run(process.execPath, ['--no-experimental-require-module', join(dir, 'load.cjs')], dir);
      notes.push('CJS entry loads even without require(esm) — engines could be widened again');
    } catch {
      notes.push(
        'CJS entry needs require(esm) (statically requires ESM-only peers), which is why ' +
          'engines excludes 21.x and 22.0-22.11',
      );
    }
  } catch (e) {
    fail('entry points load', `${e.stdout ?? ''}${e.stderr ?? ''}`.split('\n').slice(0, 6).join('\n'));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
console.log('Packaging checks beyond publint/attw:\n');
const tarball = pack();
try {
  const shipped = tarballPaths(tarball);
  checkPeerBounds();
  checkMain(shipped);
  checkSubpathStubs(tarball, shipped);
  checkEnginesAgainstRequireEsm();
  checkPeerFloorsInstall(tarball);
  checkRuntimeLoads(tarball);
} finally {
  rmSync(tarball, { force: true });
}

if (notes.length > 0) {
  console.log('\nNotes:');
  for (const n of notes) console.log(`  - ${n}`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} packaging check(s) failed.`);
  process.exit(1);
}
console.log('\nAll packaging checks passed.');
