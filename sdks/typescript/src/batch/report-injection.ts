/**
 * Shared machinery for the self-contained HTML reports a family can emit.
 *
 * A report is one file: a static template with its data spliced into an inline `<script>`.
 * Both steps below are load-bearing for that to be safe, and both were previously written
 * per family — one of the two copies without the replacer-function guard, which made
 * evaluated text able to terminate the script early.
 */

const INJECTION_MARKER = 'var REPORT_DATA = null; // __REPLACED_BY_FORMATTER__';

/**
 * Serialise report data for embedding in an inline `<script>`.
 *
 * `<`, `>` and `&` are escaped so evaluated text cannot close the script element, and
 * U+2028/U+2029 — valid in JSON but line terminators to a pre-ES2019 parser — are escaped
 * so they cannot break the script.
 */
export function toInlineJson(data: unknown): string {
  return JSON.stringify(data)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

/**
 * Splice a payload into a report template.
 *
 * `label` names the family in the failure, so a corrupted template says which report is
 * broken. The template is a parameter so that failure is reachable from a test.
 */
export function injectReportData(template: string, payload: string, label: string): string {
  if (!template.includes(INJECTION_MARKER)) {
    throw new Error(
      `${label} report template injection marker not found — template may be corrupted`,
    );
  }
  // A replacer function, not a string. As a string, `$$`, `$&`, `` $` `` and `$'` in the
  // payload are substitution patterns: `$'` inserts everything after the match, which
  // splices the template tail — including its literal `</script>` — into the inline
  // script, defeating the escaping above. Evaluated text reaches this payload, so a
  // passage containing `$'` was enough to corrupt the report.
  return template.replace(INJECTION_MARKER, () => `var REPORT_DATA = ${payload};`);
}
