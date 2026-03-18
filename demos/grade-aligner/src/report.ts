import { writeFileSync, mkdirSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import type { AlignmentResult } from './agent/types.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPORTS_DIR = path.resolve(__dirname, '../reports');

const BAND_CLASSES: Record<string, string> = {
  'K-1':    'band-k1',
  '2-3':    'band-23',
  '4-5':    'band-45',
  '6-8':    'band-68',
  '9-10':   'band-910',
  '11-CCR': 'band-ccr',
};

function bandBadge(band: string): string {
  const cls = BAND_CLASSES[band] ?? 'band-unknown';
  return `<span class="badge ${cls}">${band}</span>`;
}

function escape(text: string): string {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Render paragraph breaks as block spacing; single newlines as line breaks
  return escaped
    .split(/\n{2,}/)
    .map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('');
}

function buildRows(result: AlignmentResult): string {
  const rows: string[] = [];

  // ── Original row ──────────────────────────────────────────────────────────
  rows.push(`
    <tr class="row-original">
      <td class="col-step"><span class="step-label">Original</span></td>
      <td class="col-text">${escape(result.originalText)}</td>
      <td class="col-band">${bandBadge(result.originalGlaBand)}</td>
      <td class="col-notes">Source text — target grade <strong>${result.targetGrade}</strong></td>
    </tr>`);

  // ── Iteration rows ────────────────────────────────────────────────────────
  for (let i = 0; i < result.iterations.length; i++) {
    const iter = result.iterations[i];
    rows.push(`
    <tr class="row-iteration">
      <td class="col-step"><span class="step-label">Step ${i + 1}</span></td>
      <td class="col-text">${escape(iter.text)}</td>
      <td class="col-band">${bandBadge(iter.glaBand)}</td>
      <td class="col-notes">${escape(iter.reasoning)}</td>
    </tr>`);
  }

  // ── Final row ─────────────────────────────────────────────────────────────
  rows.push(`
    <tr class="row-final">
      <td class="col-step"><span class="step-label">Aligned</span></td>
      <td class="col-text">${escape(result.alignedText)}</td>
      <td class="col-band">${bandBadge(result.finalGlaBand)}</td>
      <td class="col-notes">${escape(result.rationale)}</td>
    </tr>`);

  return rows.join('\n');
}

function buildHtml(result: AlignmentResult): string {
  const steps = result.iterations.length;
  const alreadyAligned = steps === 0;
  const date = new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grade Alignment Report — Grade ${result.targetGrade}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      padding: 2rem;
      line-height: 1.5;
    }

    .container { max-width: 1300px; margin: 0 auto; }

    /* ── Header ─────────────────────────────────────────────────────────── */
    header {
      background: white;
      border-radius: 10px;
      padding: 1.5rem 2rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      display: flex;
      align-items: flex-start;
      gap: 2rem;
    }

    .header-title h1 { font-size: 1.4rem; font-weight: 700; margin-bottom: 0.3rem; }
    .header-title p  { color: #666; font-size: 0.9rem; }

    .header-stats {
      display: flex;
      gap: 1.5rem;
      margin-left: auto;
      flex-shrink: 0;
    }

    .stat {
      text-align: center;
      background: #f7f8fa;
      border-radius: 8px;
      padding: 0.6rem 1rem;
      min-width: 80px;
    }
    .stat-value { font-size: 1.4rem; font-weight: 700; color: #1a1a2e; }
    .stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 0.1rem; }

    /* ── Table ──────────────────────────────────────────────────────────── */
    .table-wrap {
      background: white;
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

    table { width: 100%; border-collapse: collapse; }

    thead tr { background: #1a1a2e; }
    th {
      padding: 0.85rem 1rem;
      text-align: left;
      color: #fff;
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      white-space: nowrap;
    }

    td {
      padding: 1rem;
      vertical-align: top;
      border-bottom: 1px solid #eef0f3;
      font-size: 0.88rem;
    }

    tr:last-child td { border-bottom: none; }

    .col-step  { width: 7%;  }
    .col-text  { width: 42%; }
    .col-band  { width: 10%; text-align: center; }
    .col-notes { width: 41%; }

    /* ── Row variants ───────────────────────────────────────────────────── */
    .row-original  { background: #fafafa; }
    .row-iteration { background: #fff; }
    .row-final     { background: #f0fdf4; }

    .step-label {
      display: inline-block;
      font-weight: 600;
      font-size: 0.82rem;
      padding: 0.2rem 0.5rem;
      border-radius: 5px;
    }

    .row-original  .step-label { background: #e5e7eb; color: #374151; }
    .row-iteration .step-label { background: #dbeafe; color: #1e40af; }
    .row-final     .step-label { background: #bbf7d0; color: #166534; }

    /* ── Text cell ──────────────────────────────────────────────────────── */
    .col-text {
      max-height: 220px;
      overflow-y: auto;
      line-height: 1.65;
    }

    /* ── Notes cell ─────────────────────────────────────────────────────── */
    .col-notes { line-height: 1.6; }

    /* ── Paragraph spacing inside cells ────────────────────────────────── */
    td p { margin-bottom: 0.6em; }
    td p:last-child { margin-bottom: 0; }

    /* ── Grade band badges ──────────────────────────────────────────────── */
    .badge {
      display: inline-block;
      padding: 0.3rem 0.65rem;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      white-space: nowrap;
    }
    .band-k1      { background: #dbeafe; color: #1e40af; }
    .band-23      { background: #dcfce7; color: #166534; }
    .band-45      { background: #fef9c3; color: #854d0e; }
    .band-68      { background: #ffedd5; color: #9a3412; }
    .band-910     { background: #fce7f3; color: #9d174d; }
    .band-ccr     { background: #ede9fe; color: #5b21b6; }
    .band-unknown { background: #e5e7eb; color: #374151; }

    /* ── Footer ─────────────────────────────────────────────────────────── */
    footer {
      margin-top: 1rem;
      text-align: right;
      font-size: 0.8rem;
      color: #aaa;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-title">
        <h1>Grade Alignment Report</h1>
        <p>Generated ${date}</p>
      </div>
      <div class="header-stats">
        <div class="stat">
          <div class="stat-value">${result.targetGrade}</div>
          <div class="stat-label">Target Grade</div>
        </div>
        <div class="stat">
          <div class="stat-value">${result.originalGlaBand}</div>
          <div class="stat-label">Original Band</div>
        </div>
        <div class="stat">
          <div class="stat-value">${alreadyAligned ? '—' : String(steps)}</div>
          <div class="stat-label">${alreadyAligned ? 'Already Aligned' : 'Steps Taken'}</div>
        </div>
      </div>
    </header>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-step">Step</th>
            <th class="col-text">Text</th>
            <th class="col-band">Grade Band</th>
            <th class="col-notes">Notes</th>
          </tr>
        </thead>
        <tbody>
          ${buildRows(result)}
        </tbody>
      </table>
    </div>

    <footer>Learning Commons · Grade Aligner Demo</footer>
  </div>
</body>
</html>`;
}

export function generateReport(result: AlignmentResult, outputPath?: string): string {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  const reportPath = outputPath ?? path.join(REPORTS_DIR, `report-${stamp}.html`);
  mkdirSync(path.dirname(reportPath), { recursive: true });
  writeFileSync(reportPath, buildHtml(result), 'utf-8');
  return reportPath;
}
