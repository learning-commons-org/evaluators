// Shared fetch helper used by every evaluator page.
export async function fetchJson(url: string, init?: RequestInit): Promise<any> {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.error ?? `Request failed (${response.status})`);
  }
  if (body === null) {
    throw new Error('Server returned a non-JSON response — is the backend running?');
  }
  return body;
}
