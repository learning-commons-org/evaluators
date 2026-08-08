import * as fs from 'fs';
import { parse } from 'csv-parse/sync';
import type { BatchInput } from './types.js';

/**
 * Parse a CSV file into raw {@link BatchInput} rows.
 *
 * Family-agnostic: every column is read into `columns` keyed by its header
 * (trimmed). Column requirements, aliases, and defaults are applied later by
 * the selected family (see `normalizeRow`), so this loader imposes no schema.
 * Fully empty rows are skipped.
 *
 * @throws {Error} If the file does not exist or is empty
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

  const inputs: BatchInput[] = [];

  for (let i = 0; i < records.length; i++) {
    const row = records[i];
    // Null-prototype: CSV headers are user-controlled, so a header like
    // "__proto__" must not touch Object.prototype.
    const columns: Record<string, string> = Object.create(null);
    let hasValue = false;
    for (const [key, value] of Object.entries(row)) {
      const str = value == null ? '' : String(value).trim();
      columns[key] = str;
      if (str !== '') hasValue = true;
    }

    if (!hasValue) continue; // skip fully-empty rows

    inputs.push({
      rowIndex: i + 2, // 1-based, offset by 1 for the header row
      columns,
      originalRow: row,
    });
  }

  return inputs;
}
