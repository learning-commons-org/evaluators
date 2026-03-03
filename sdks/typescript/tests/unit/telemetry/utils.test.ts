import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getSDKVersion } from '../../../src/telemetry/utils.js';

// UUID v4 pattern
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe('Telemetry Utils', () => {
  describe('generateClientId', () => {
    // Reset module cache between tests so cachedClientId doesn't leak across tests
    beforeEach(() => {
      vi.resetModules();
    });

    it('should generate a new UUID, create the config directory, and persist it when no config file exists', async () => {
      const writeFileSync = vi.fn();
      const mkdirSync = vi.fn();
      vi.doMock('node:fs', () => ({
        readFileSync: vi.fn(() => { throw new Error('ENOENT'); }),
        writeFileSync,
        mkdirSync,
      }));
      vi.doMock('node:os', () => ({ homedir: vi.fn(() => '/home/user') }));

      const { generateClientId } = await import('../../../src/telemetry/utils.js');
      const id = generateClientId();

      expect(id).toMatch(UUID_REGEX);
      expect(mkdirSync).toHaveBeenCalledWith(expect.any(String), { recursive: true });
      expect(writeFileSync).toHaveBeenCalledOnce();
      const written = JSON.parse(writeFileSync.mock.calls[0][1] as string) as {
        telemetry: { clientId: string };
      };
      expect(written.telemetry.clientId).toBe(id);
    });

    it('should not re-read from disk on repeated calls', async () => {
      const readFileSync = vi.fn(() => { throw new Error('ENOENT'); });
      vi.doMock('node:fs', () => ({
        readFileSync,
        writeFileSync: vi.fn(),
        mkdirSync: vi.fn(),
      }));
      vi.doMock('node:os', () => ({ homedir: vi.fn(() => '/home/user') }));

      const { generateClientId } = await import('../../../src/telemetry/utils.js');

      generateClientId();
      generateClientId();

      expect(readFileSync).toHaveBeenCalledOnce();
    });

    it('should read and return an existing client ID from config file without writing to disk', async () => {
      const existingId = 'a1b2c3d4-e5f6-4789-ab01-cd23ef456789';
      const writeFileSync = vi.fn();
      const mkdirSync = vi.fn();
      vi.doMock('node:fs', () => ({
        readFileSync: vi.fn(() => JSON.stringify({ telemetry: { clientId: existingId } })),
        writeFileSync,
        mkdirSync,
      }));
      vi.doMock('node:os', () => ({ homedir: vi.fn(() => '/home/user') }));

      const { generateClientId } = await import('../../../src/telemetry/utils.js');

      expect(generateClientId()).toBe(existingId);
      expect(mkdirSync).not.toHaveBeenCalled();
      expect(writeFileSync).not.toHaveBeenCalled();
    });

    it('should generate and persist a new UUID if config file exists but clientId is missing', async () => {
      const writeFileSync = vi.fn();
      vi.doMock('node:fs', () => ({
        readFileSync: vi.fn(() => JSON.stringify({ telemetry: {} })),
        writeFileSync,
        mkdirSync: vi.fn(),
      }));
      vi.doMock('node:os', () => ({ homedir: vi.fn(() => '/home/user') }));

      const { generateClientId } = await import('../../../src/telemetry/utils.js');
      const id = generateClientId();

      expect(id).toMatch(UUID_REGEX);
      expect(writeFileSync).toHaveBeenCalledOnce();
      const written = JSON.parse(writeFileSync.mock.calls[0][1] as string) as {
        telemetry: { clientId: string };
      };
      expect(written.telemetry.clientId).toBe(id);
    });

    it('should return a valid UUID without throwing when filesystem is read-only', async () => {
      vi.doMock('node:fs', () => ({
        readFileSync: vi.fn(() => { throw new Error('ENOENT'); }),
        writeFileSync: vi.fn(() => { throw new Error('EROFS'); }),
        mkdirSync: vi.fn(() => { throw new Error('EROFS'); }),
      }));
      vi.doMock('node:os', () => ({ homedir: vi.fn(() => '/home/user') }));

      const { generateClientId } = await import('../../../src/telemetry/utils.js');

      let id: string | undefined;
      expect(() => { id = generateClientId(); }).not.toThrow();
      expect(id).toMatch(UUID_REGEX);
    });
  });

  describe('getSDKVersion', () => {
    it('should return a valid version string', () => {
      const version = getSDKVersion();

      expect(version).toMatch(/^\d+\.\d+\.\d+$/);
    });

    it('should return same version on repeated calls (cached)', () => {
      const version1 = getSDKVersion();
      const version2 = getSDKVersion();

      expect(version1).toBe(version2);
    });
  });
});
