import * as fs from 'fs';
import { parse } from 'csv-parse/sync';
import type { BatchInput } from './types.js';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function findColumn(row: Record<string, any>, columnName: string): string | undefined {
  const normalizedTarget = columnName.toLowerCase().trim();
  for (const key of Object.keys(row)) {
    if (key.toLowerCase().trim() === normalizedTarget) {
      return key;
    }
  }
  return undefined;
}

/**
 * Parse a CSV file into BatchInput rows.
 *
 * Requires columns named "text" and "grade" (case-insensitive, whitespace-trimmed).
 * Rows missing either value are silently skipped.
 *
 * @throws {Error} If the file does not exist, is empty, or is missing required columns
 */
export function parseCSV(csvPath: string): BatchInput[] {
  if (!fs.existsSync(csvPath)) {
    throw new Error(`CSV file not found: ${csvPath}`);
  }

  const records = parse(fs.readFileSync(csvPath, 'utf-8'), {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  }) as Record<string, any>[];

  if (records.length === 0) {
    throw new Error('CSV file is empty');
  }

  const firstRow = records[0];
  const textColumn = findColumn(firstRow, 'text');
  const gradeColumn = findColumn(firstRow, 'grade');

  if (!textColumn) {
    throw new Error('CSV must have a "text" column (case-insensitive)');
  }
  if (!gradeColumn) {
    throw new Error('CSV must have a "grade" column (case-insensitive)');
  }

  const inputs: BatchInput[] = [];

  for (let i = 0; i < records.length; i++) {
    const row = records[i];
    const text = row[textColumn];
    const grade = row[gradeColumn];

    if (!text || !grade) {
      console.warn(`Warning: skipping row ${i + 2} — missing text or grade`);
      continue;
    }

    inputs.push({
      text: String(text).trim(),
      grade: String(grade).trim(),
      rowIndex: i + 2, // 1-based, offset by 1 for the header row
      originalRow: row,
    });
  }

  return inputs;
}
