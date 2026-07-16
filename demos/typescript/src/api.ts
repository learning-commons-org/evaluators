// Shared fetch helper used by every evaluator page.
export async function fetchJson(url: string, init?: RequestInit): Promise<any> {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => null);
  if (body === null) {
    const status = response.ok ? '' : ` (status ${response.status})`;
    throw new Error(`Server returned a non-JSON response${status} — is the backend running?`);
  }
  if (!response.ok) {
    throw new Error(body?.error ?? `Request failed (${response.status})`);
  }
  return body;
}
