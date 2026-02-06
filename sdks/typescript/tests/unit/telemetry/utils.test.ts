import { describe, it, expect } from 'vitest';
import { generateClientId, getSDKVersion } from '../../../src/telemetry/utils.js';

describe('Telemetry Utils', () => {
  describe('generateClientId', () => {
    it('should generate consistent hash for same keys', () => {
      const id1 = generateClientId('key1', 'key2');
      const id2 = generateClientId('key1', 'key2');

      expect(id1).toBe(id2);
    });

    it('should generate same hash regardless of key order', () => {
      const id1 = generateClientId('key1', 'key2');
      const id2 = generateClientId('key2', 'key1');

      expect(id1).toBe(id2);
    });

    it('should filter out undefined keys', () => {
      const id1 = generateClientId('key1', undefined, 'key2');
      const id2 = generateClientId('key1', 'key2');

      expect(id1).toBe(id2);
    });

    it('should generate different hashes for different keys', () => {
      const id1 = generateClientId('key1', 'key2');
      const id2 = generateClientId('key1', 'key3');

      expect(id1).not.toBe(id2);
    });

    it('should return 64-character hex string', () => {
      const id = generateClientId('key1', 'key2');

      expect(id).toMatch(/^[a-f0-9]{64}$/);
    });

    it('should handle single key', () => {
      const id = generateClientId('single-key');

      expect(id).toMatch(/^[a-f0-9]{64}$/);
    });

    it('should generate random ID when no keys provided', () => {
      const id1 = generateClientId();
      const id2 = generateClientId();

      // Random IDs should be different
      expect(id1).not.toBe(id2);
      expect(id1).toMatch(/^[a-f0-9]{64}$/);
      expect(id2).toMatch(/^[a-f0-9]{64}$/);
    });

    it('should generate random ID when all keys are undefined', () => {
      const id1 = generateClientId(undefined, undefined);
      const id2 = generateClientId(undefined, undefined);

      // Random IDs should be different
      expect(id1).not.toBe(id2);
    });

    it('should prevent collision with delimiter (theoretical)', () => {
      // Without delimiter: ["ab", "c"] and ["a", "bc"] would both hash "abc"
      // With delimiter: ["ab", "c"] → "ab|c" and ["a", "bc"] → "a|bc"
      const id1 = generateClientId('ab', 'c');
      const id2 = generateClientId('a', 'bc');

      expect(id1).not.toBe(id2);
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
