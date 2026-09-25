import { readFile, stat } from 'node:fs/promises';
import { InputValidationError } from '../errors.js';
import type { ImageAttachment, ImageMediaType } from '../providers/base.js';

/**
 * Loading an image input for a vision evaluator.
 *
 * A contract declares the image as a string: a local file path (absolute, or relative to
 * the process working directory) or an http(s) URL. Whatever the string points at is read
 * here, in the caller's environment, and never leaves it except as part of the model
 * request. The format is taken from the file's own bytes, not from its extension or the
 * server's content type, so a mislabelled file is caught before a paid call.
 *
 * The SDK is therefore reading files and fetching URLs the caller names. That is the
 * intended posture — the caller's own environment, the caller's own images — and callers
 * relaying strings from untrusted parties should resolve them to files they control first.
 */

/** Every vendor the SDK supports accepts these three natively; the contracts declare no others. */
export const IMAGE_MEDIA_TYPES: readonly ImageMediaType[] = ['image/png', 'image/jpeg', 'image/webp'];

/** The cap the contracts declare. Gemini's inline limit is 20 MB; Claude's request cap is 32 MB. */
export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;

/** How long a URL fetch may take before it is the caller's problem. */
const FETCH_TIMEOUT_MS = 30_000;

/** The image format a byte string declares itself to be, or undefined if none we accept. */
export function sniffImageMediaType(bytes: Uint8Array): ImageMediaType | undefined {
  if (bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
    return 'image/png';
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return 'image/jpeg';
  }
  if (
    bytes.length >= 12 &&
    bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46 && // RIFF
    bytes[8] === 0x57 && bytes[9] === 0x45 && bytes[10] === 0x42 && bytes[11] === 0x50 // WEBP
  ) {
    return 'image/webp';
  }
  return undefined;
}

function isHttpUrl(source: string): boolean {
  return /^https?:\/\//i.test(source);
}

function tooLarge(field: string, source: string, bytes: number): InputValidationError {
  return new InputValidationError(
    `${field}: "${source}" is ${(bytes / (1024 * 1024)).toFixed(1)} MB; the maximum is ${MAX_IMAGE_BYTES / (1024 * 1024)} MB.`,
  );
}

/**
 * Read a response body with a byte budget, so an oversized or hostile URL is cut off at the
 * cap rather than buffered whole. `Content-Length`, when present, is checked first.
 */
async function readBounded(field: string, source: string, response: Response): Promise<Uint8Array> {
  const declared = Number(response.headers.get('content-length'));
  if (Number.isFinite(declared) && declared > MAX_IMAGE_BYTES) {
    throw tooLarge(field, source, declared);
  }
  if (!response.body) {
    return new Uint8Array(await response.arrayBuffer());
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_IMAGE_BYTES) {
      await reader.cancel();
      throw tooLarge(field, source, total);
    }
    chunks.push(value);
  }
  const out = new Uint8Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.byteLength;
  }
  return out;
}

async function readSource(field: string, source: string): Promise<Uint8Array> {
  if (isHttpUrl(source)) {
    let response: Response;
    try {
      response = await fetch(source, { signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
    } catch (cause) {
      throw new InputValidationError(`${field}: could not fetch "${source}".`, cause);
    }
    if (!response.ok) {
      throw new InputValidationError(`${field}: fetching "${source}" returned HTTP ${response.status}.`);
    }
    return readBounded(field, source, response);
  }
  try {
    const { size } = await stat(source);
    if (size > MAX_IMAGE_BYTES) throw tooLarge(field, source, size);
    return new Uint8Array(await readFile(source));
  } catch (cause) {
    if (cause instanceof InputValidationError) throw cause;
    throw new InputValidationError(`${field}: could not read file "${source}".`, cause);
  }
}

/**
 * Read the image `source` names and return it as an attachment.
 *
 * @param field the input's name, for error messages
 * @param source a local file path or an http(s) URL
 * @throws {InputValidationError} if the source cannot be read, is not PNG, JPEG or WEBP by
 * its bytes, or exceeds {@link MAX_IMAGE_BYTES}
 */
export async function loadImage(field: string, source: string): Promise<ImageAttachment> {
  const data = await readSource(field, source);
  if (data.length === 0) {
    throw new InputValidationError(`${field}: "${source}" is empty.`);
  }
  if (data.length > MAX_IMAGE_BYTES) {
    throw tooLarge(field, source, data.length);
  }
  const mediaType = sniffImageMediaType(data);
  if (!mediaType) {
    throw new InputValidationError(
      `${field}: "${source}" is not a PNG, JPEG or WEBP image (judged by its bytes, not its name).`,
    );
  }
  return { type: 'image', data, mediaType };
}
