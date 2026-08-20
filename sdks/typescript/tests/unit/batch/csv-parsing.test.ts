import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { parseCSV } from '../../../src/batch/index.js';

// ---- Helpers ----

function withTempCSV(content: string, fn: (csvPath: string) => void): void {
  const tmpPath = path.join(os.tmpdir(), `batch-test-${Date.now()}-${Math.round(performance.now())}.csv`);
  fs.writeFileSync(tmpPath, content);
  try {
    fn(tmpPath);
  } finally {
    fs.unlinkSync(tmpPath);
  }
}

// ---- Tests ----
//
// parseCSV is family-agnostic: it reads every column into `columns` keyed by
// header and imposes no schema. Column requirements/aliases/defaults are the
// family's job (see column-normalization.test.ts).

describe('parseCSV', () => {
  describe('generic column capture', () => {
    it('captures every column keyed by its header', () => {
      withTempCSV('TEXT,Grade\nhello world,5', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(1);
        expect(inputs[0].columns.TEXT).toBe('hello world');
        expect(inputs[0].columns.Grade).toBe('5');
      });
    });

    it('trims values', () => {
      withTempCSV('question,standard\n  2 + 2 = ?  ,  4.OA.A.1  ', (p) => {
        const inputs = parseCSV(p);
        expect(inputs[0].columns.question).toBe('2 + 2 = ?');
        expect(inputs[0].columns.standard).toBe('4.OA.A.1');
      });
    });
  });

  describe('parsing the test fixture', () => {
    const csvPath = path.join(__dirname, '../../fixtures/batch-test.csv');

    it('returns one BatchInput per non-empty data row', () => {
      expect(parseCSV(csvPath)).toHaveLength(2);
    });

    it('assigns rowIndex matching the 1-based CSV line number (header is line 1)', () => {
      const inputs = parseCSV(csvPath);
      expect(inputs[0].rowIndex).toBe(2);
      expect(inputs[1].rowIndex).toBe(3);
    });

    it('preserves all original CSV columns in originalRow', () => {
      const inputs = parseCSV(csvPath);
      expect(inputs[0].originalRow).toHaveProperty('row_id');
      expect(inputs[0].originalRow).toHaveProperty('source');
      expect(inputs[0].originalRow).toHaveProperty('category');
    });
  });

  describe('row filtering', () => {
    it('skips fully-empty rows but keeps rows with any value', () => {
      withTempCSV('text,grade\nhello world,5\n,\ngoodbye world,', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(2);
        expect(inputs[0].columns.text).toBe('hello world');
        expect(inputs[1].columns.text).toBe('goodbye world');
      });
    });

    it('preserves the original CSV line number in rowIndex even when rows are skipped', () => {
      withTempCSV('text,grade\nfirst,3\n,\nsecond,5', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(2);
        expect(inputs[0].rowIndex).toBe(2);
        expect(inputs[1].rowIndex).toBe(4); // line 3 was skipped
      });
    });
  });

  describe('error cases', () => {
    it('throws when file does not exist', () => {
      expect(() => parseCSV('/no/such/file.csv')).toThrow('CSV file not found');
    });

    it('throws when file is empty', () => {
      withTempCSV('', (p) => {
        expect(() => parseCSV(p)).toThrow('CSV file is empty');
      });
    });
  });
});
