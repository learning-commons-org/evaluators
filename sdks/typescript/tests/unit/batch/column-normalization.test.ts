import { describe, it, expect } from 'vitest';
import {
  normalizeRow,
  validateRequiredColumns,
  resolveMembers,
} from '../../../src/batch/families/family.js';
import { QTC_FAMILY } from '../../../src/batch/families/qtc.js';
import { STANDARDS_FAMILY } from '../../../src/batch/families/standards.js';
import { Jurisdiction } from '../../../src/knowledge-graph/index.js';

function raw(columns: Record<string, string>, rowIndex = 2) {
  return { rowIndex, columns, originalRow: { ...columns } };
}

describe('validateRequiredColumns', () => {
  it('passes when required columns are present (via canonical name)', () => {
    expect(() => validateRequiredColumns(STANDARDS_FAMILY, ['question', 'statementCode'])).not.toThrow();
  });

  it('accepts aliases for required columns', () => {
    // standards: statementCode alias "ccss_standard", question alias "text"
    expect(() => validateRequiredColumns(STANDARDS_FAMILY, ['text', 'ccss_standard'])).not.toThrow();
  });

  it('throws listing the missing canonical column', () => {
    expect(() => validateRequiredColumns(STANDARDS_FAMILY, ['question'])).toThrow(/statementCode/);
  });
});

describe('normalizeRow — standards family', () => {
  it('maps aliases onto canonical names', () => {
    const row = normalizeRow(raw({ text: '2+2=?', ccss_standard: '4.OA.A.1' }), STANDARDS_FAMILY);
    expect(row.columns.question).toBe('2+2=?');
    expect(row.columns.statementCode).toBe('4.OA.A.1');
  });

  it('applies the Multi-State jurisdiction default when absent', () => {
    const row = normalizeRow(raw({ question: 'q', statementCode: '4.OA.A.1' }), STANDARDS_FAMILY);
    expect(row.columns.jurisdiction).toBe(Jurisdiction.MultiState);
  });

  it('keeps an explicit jurisdiction over the default', () => {
    const row = normalizeRow(
      raw({ question: 'q', statementCode: '4.OA.A.1', jurisdiction: 'California' }),
      STANDARDS_FAMILY,
    );
    expect(row.columns.jurisdiction).toBe('California');
  });

  it('throws for a row missing a required value', () => {
    expect(() => normalizeRow(raw({ question: 'q' }), STANDARDS_FAMILY)).toThrow(/statementCode/);
  });

  it('prefers the canonical column over an alias when both are present', () => {
    // `question` has alias `text`; a CSV with both must use the canonical column.
    const row = normalizeRow(
      raw({ text: 'passage context', question: '2+2=?', statementCode: '4.OA.A.1' }),
      STANDARDS_FAMILY,
    );
    expect(row.columns.question).toBe('2+2=?');
  });

  it('falls back to an alias when the canonical column is present but empty', () => {
    const row = normalizeRow(
      raw({ question: '', text: 'the real item', statementCode: '4.OA.A.1' }),
      STANDARDS_FAMILY,
    );
    expect(row.columns.question).toBe('the real item');
  });
});

describe('normalizeRow — QTC family', () => {
  it('requires text and grade', () => {
    expect(() => normalizeRow(raw({ text: 'hello' }), QTC_FAMILY)).toThrow(/grade/);
  });
});

describe('resolveMembers', () => {
  it('defaults to all members', () => {
    expect(resolveMembers(QTC_FAMILY).length).toBe(QTC_FAMILY.members.length);
  });

  it('resolves a selected subset in order', () => {
    const selected = resolveMembers(QTC_FAMILY, ['vocabulary', 'conventionality']);
    expect(selected.map((m) => m.id)).toEqual(['vocabulary', 'conventionality']);
  });

  it('throws for an unknown member id', () => {
    expect(() => resolveMembers(QTC_FAMILY, ['nope'])).toThrow(/Unknown evaluator "nope"/);
  });
});
