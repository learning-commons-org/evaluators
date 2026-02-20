import { createHash, randomBytes } from 'crypto';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Generate client ID for anonymous tracking
 *
 * Creates SHA256 hash of API keys to create consistent identifier
 * across requests while maintaining anonymity.
 *
 * @param apiKeys - Array of API keys to hash
 * @returns SHA256 hex string
 */
export function generateClientId(...apiKeys: (string | undefined)[]): string {
  // Filter out undefined keys and sort for consistency
  const keys = apiKeys.filter((k): k is string => k !== undefined).sort();

  // If no keys provided, generate random ID for this session
  if (keys.length === 0) {
    return createHash('sha256')
      .update(randomBytes(16))
      .digest('hex');
  }

  // Hash the concatenated keys with delimiter to prevent collisions
  return createHash('sha256')
    .update(keys.join('|'))
    .digest('hex');
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
