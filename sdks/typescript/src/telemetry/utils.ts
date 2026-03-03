import { randomUUID } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/** Cached client ID — populated on first call, reused for process lifetime */
let cachedClientId: string | undefined;

/**
 * Get or create a persistent client ID for anonymous tracking.
 *
 * On first run, generates a UUID and tries to save it to:
 *   - Windows:  %APPDATA%\learning-commons\config.json
 *   - macOS/Linux: ~/.config/learning-commons/config.json
 *
 * On subsequent runs, reads the saved UUID from disk.
 * Falls back to an in-memory UUID (per-process) if the filesystem
 * is unavailable (e.g., serverless, read-only containers).
 */
export function generateClientId(): string {
  if (cachedClientId) {
    return cachedClientId;
  }

  const configFile = getConfigFilePath();

  // Try to read existing client ID from disk
  try {
    const data = JSON.parse(readFileSync(configFile, 'utf-8')) as {
      telemetry?: { clientId?: string };
    };
    if (data?.telemetry?.clientId) {
      cachedClientId = data.telemetry.clientId;
      return cachedClientId;
    }
  } catch {
    // File doesn't exist yet — fall through to generate
  }

  // Generate new UUID and try to persist it
  const clientId = randomUUID();
  try {
    mkdirSync(dirname(configFile), { recursive: true });
    writeFileSync(configFile, JSON.stringify({ telemetry: { clientId } }, null, 2));
  } catch {
    // Filesystem unavailable — use in-memory UUID for this process
  }

  cachedClientId = clientId;
  return cachedClientId;
}

function getConfigFilePath(): string {
  const configDir =
    process.platform === 'win32'
      ? join(process.env.APPDATA ?? homedir(), 'learning-commons')
      : join(homedir(), '.config', 'learning-commons');
  return join(configDir, 'config.json');
}

let cachedVersion: string | undefined;

/**
 * Get SDK version from package.json
 */
export function getSDKVersion(): string {
  if (cachedVersion) {
    return cachedVersion;
  }

  const possiblePaths = [
    join(__dirname, '../../package.json'), // From src/
    join(__dirname, '../package.json'),    // From dist/
  ];

  for (const path of possiblePaths) {
    try {
      const pkg = JSON.parse(readFileSync(path, 'utf-8')) as { version?: string };
      cachedVersion = pkg.version || '0.0.0';
      return cachedVersion;
    } catch {
      continue;
    }
  }

  // Fallback if no package.json found
  cachedVersion = '0.0.0';
  return cachedVersion;
}
