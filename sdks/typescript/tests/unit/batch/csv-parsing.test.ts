import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { parseCSV } from '../../../src/batch/index.js';

// ---- Helpers ----

function withTempCSV(content: string, fn: (csvPath: string) => void): void {
  const tmpPath = path.join(os.tmpdir(), `batch-test-${Date.now()}.csv`);
  fs.writeFileSync(tmpPath, content);
  try {
    fn(tmpPath);
  } finally {
    fs.unlinkSync(tmpPath);
  }
}

// ---- Tests ----

describe('parseCSV', () => {
  describe('column detection', () => {
    it('finds text and grade columns case-insensitively', () => {
      // batch-test.csv has "TEXT" and "  Grade  " (with whitespace padding)
      const csvPath = path.join(__dirname, '../../fixtures/batch-test.csv');
      const inputs = parseCSV(csvPath);
      expect(inputs.length).toBeGreaterThan(0);
      for (const input of inputs) {
        expect(input.text).toBeTruthy();
        expect(input.grade).toBeTruthy();
      }
    });

    it('accepts uppercase TEXT and mixed-case Grade columns', () => {
      withTempCSV('TEXT,Grade\nhello world,5', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(1);
        expect(inputs[0].text).toBe('hello world');
        expect(inputs[0].grade).toBe('5');
      });
    });

    it('accepts columns with surrounding whitespace in the header', () => {
      withTempCSV('  text  ,  grade  \nhello world,5', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(1);
        expect(inputs[0].text).toBe('hello world');
      });
    });
  });

  describe('parsing the test fixture', () => {
    const csvPath = path.join(__dirname, '../../fixtures/batch-test.csv');

    it('returns one BatchInput per non-empty data row', () => {
      expect(parseCSV(csvPath)).toHaveLength(2);
    });

    it('trims text and grade values', () => {
      for (const input of parseCSV(csvPath)) {
        expect(input.text).toBe(input.text.trim());
        expect(input.grade).toBe(input.grade.trim());
      }
    });

    it('assigns rowIndex matching the 1-based CSV line number (header is line 1)', () => {
      const inputs = parseCSV(csvPath);
      expect(inputs[0].rowIndex).toBe(2); // first data row is CSV line 2
      expect(inputs[1].rowIndex).toBe(3); // second data row is CSV line 3
    });

    it('preserves all original CSV columns in originalRow', () => {
      const inputs = parseCSV(csvPath);
      // batch-test.csv has: row_id, TEXT, Grade, source, category
      expect(inputs[0].originalRow).toHaveProperty('row_id');
      expect(inputs[0].originalRow).toHaveProperty('source');
      expect(inputs[0].originalRow).toHaveProperty('category');
    });
  });

  describe('row filtering', () => {
    it('skips rows where text is empty', () => {
      withTempCSV('text,grade\nhello world,5\n,4\ngoodbye world,3', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(2);
        expect(inputs[0].text).toBe('hello world');
        expect(inputs[1].text).toBe('goodbye world');
      });
    });

    it('skips rows where grade is empty', () => {
      withTempCSV('text,grade\nhello world,5\ngoodbye world,', (p) => {
        const inputs = parseCSV(p);
        expect(inputs).toHaveLength(1);
        expect(inputs[0].text).toBe('hello world');
      });
    });

    it('preserves the original CSV line number in rowIndex even when rows are skipped', () => {
      // header=line1, first=line2, skipped=line3, second=line4
      withTempCSV('text,grade\nfirst,3\n,4\nsecond,5', (p) => {
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

    it('throws when "text" column is missing', () => {
      withTempCSV('grade,content\n5,hello world', (p) => {
        expect(() => parseCSV(p)).toThrow('"text" column');
      });
    });

    it('throws when "grade" column is missing', () => {
      withTempCSV('text,level\nhello world,5', (p) => {
        expect(() => parseCSV(p)).toThrow('"grade" column');
      });
    });
  });
});
