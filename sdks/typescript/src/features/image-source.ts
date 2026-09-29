import { constants } from 'node:fs';
import { open, type FileHandle } from 'node:fs/promises';
import { InputValidationError } from '../errors.js';
import type { ImageAttachment, ImageMediaType } from '../providers/base.js';

/**
 * Loading an image input for a vision evaluator.
 *
 * A contract declares an attached input as an array of local file paths, and bounds each
 * file with an `x-image` block on the array's items. Each path is read here, in the
 * caller's environment, and its bytes leave only as part of the model request. Format and
 * dimensions are taken from the file's own bytes, never from its name, so a mislabelled or
 * oversized file is caught before a paid call.
 *
 * The SDK is therefore reading files the caller names. That is the intended posture — the
 * caller's own environment, the caller's own images — and callers relaying paths from
 * untrusted parties should resolve them to files they control first.
 */

/** The per-file bounds a contract declares in `x-image`, as the SDK reads them. */
export interface ImageBounds {
  formats: readonly ImageMediaType[];
  detect: 'signature';
  min_bytes: number;
  max_bytes: number;
  min_edge: number;
  max_edge: number;
}

/** The image format a byte string declares itself to be, or undefined if none we accept. */
export function sniffImageMediaType(bytes: Uint8Array): ImageMediaType | undefined {
  if (
    bytes.length >= 8 &&
    bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47 &&
    bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a
  ) {
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

/**
 * Width and height from the image header, without decoding pixels.
 *
 * PNG stores them in IHDR; JPEG in its first start-of-frame marker; WebP in the VP8, VP8L or
 * VP8X chunk header. Undefined when the header cannot be read, which means the file is
 * malformed whatever its signature says.
 */
export function readImageDimensions(
  bytes: Uint8Array,
  mediaType: ImageMediaType,
): { width: number; height: number } | undefined {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const has = (n: number) => bytes.length >= n;

  if (mediaType === 'image/png') {
    // Signature (8) + IHDR length (4) + "IHDR" (4), then width and height, big-endian.
    // IHDR must be the first chunk; anything else after a valid signature is not a PNG.
    if (!has(24) || String.fromCharCode(bytes[12], bytes[13], bytes[14], bytes[15]) !== 'IHDR') return undefined;
    return { width: view.getUint32(16), height: view.getUint32(20) };
  }

  if (mediaType === 'image/jpeg') {
    let offset = 2;
    while (offset + 4 <= bytes.length) {
      if (bytes[offset] !== 0xff) return undefined;
      const marker = bytes[offset + 1];
      // Padding and standalone markers carry no length.
      if (marker === 0xff) { offset += 1; continue; }
      if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) { offset += 2; continue; }
      const length = view.getUint16(offset + 2);
      // SOF0–SOF15, excluding DHT (C4), JPG (C8) and DAC (CC).
      const isFrame = marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc;
      if (isFrame) {
        if (offset + 9 > bytes.length) return undefined;
        return { height: view.getUint16(offset + 5), width: view.getUint16(offset + 7) };
      }
      offset += 2 + length;
    }
    return undefined;
  }

  // WebP: RIFF (4) size (4) "WEBP" (4), then the first chunk's FourCC at 12.
  if (!has(30)) return undefined;
  const chunk = String.fromCharCode(bytes[12], bytes[13], bytes[14], bytes[15]);
  if (chunk === 'VP8 ') {
    // Frame tag (3) + start code 9d 01 2a (3), then 14-bit width and height, little-endian.
    if (bytes[23] !== 0x9d || bytes[24] !== 0x01 || bytes[25] !== 0x2a) return undefined;
    return { width: view.getUint16(26, true) & 0x3fff, height: view.getUint16(28, true) & 0x3fff };
  }
  if (chunk === 'VP8L') {
    // Signature byte 0x2f at 20, then 14-bit width-1 and height-1 packed little-endian.
    if (bytes[20] !== 0x2f) return undefined;
    const bits = view.getUint32(21, true);
    return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
  }
  if (chunk === 'VP8X') {
    // Canvas width-1 and height-1 as 24-bit little-endian at 24 and 27.
    const u24 = (at: number) => bytes[at] | (bytes[at + 1] << 8) | (bytes[at + 2] << 16);
    return { width: u24(24) + 1, height: u24(27) + 1 };
  }
  return undefined;
}

/**
 * Read at most `limit` bytes from an open file. A file that grew after `stat` is cut off here
 * rather than read whole; the caller's size check then rejects it.
 */
async function readBounded(file: FileHandle, limit: number): Promise<Uint8Array> {
  const buffer = new Uint8Array(limit);
  let total = 0;
  while (total < limit) {
    const { bytesRead } = await file.read(buffer, total, limit - total, total);
    if (bytesRead === 0) break;
    total += bytesRead;
  }
  return buffer.subarray(0, total);
}

/** Exact bytes, with MB alongside for readability: a file one byte over must not read as equal. */
const size = (bytes: number) => `${bytes.toLocaleString('en-US')} bytes (${(bytes / (1024 * 1024)).toFixed(2)} MB)`;

/**
 * Read the image at `path` and return it as an attachment, enforcing every bound the
 * contract declares for it.
 *
 * @param field the input's name and position, for error messages (e.g. `image_paths[0]`)
 * @param path a local file path, absolute or relative to the working directory
 * @param bounds the contract's `x-image` block for this input
 * @throws {InputValidationError} if the file cannot be read, is not an accepted format by
 * its bytes, has an unreadable header, or falls outside the declared size or edge bounds
 */
export async function loadImage(field: string, path: string, bounds: ImageBounds): Promise<ImageAttachment> {
  let data: Uint8Array;
  let file: FileHandle | undefined;
  try {
    // One handle for the check and the read, so the file cannot be swapped between them.
    // O_NONBLOCK keeps a FIFO from blocking the open; it is then refused as not a regular file.
    file = await open(path, constants.O_RDONLY | constants.O_NONBLOCK);
    const info = await file.stat();
    if (!info.isFile()) {
      throw new InputValidationError(`${field}: "${path}" is not a regular file.`);
    }
    if (info.size > bounds.max_bytes) {
      throw new InputValidationError(`${field}: "${path}" is ${size(info.size)}; the maximum is ${size(bounds.max_bytes)}.`);
    }
    data = await readBounded(file, bounds.max_bytes + 1);
  } catch (cause) {
    if (cause instanceof InputValidationError) throw cause;
    throw new InputValidationError(`${field}: could not read file "${path}".`, cause);
  } finally {
    await file?.close();
  }

  if (data.length < bounds.min_bytes) {
    throw new InputValidationError(
      `${field}: "${path}" is ${size(data.length)}; the minimum is ${size(bounds.min_bytes)}.`,
    );
  }
  if (data.length > bounds.max_bytes) {
    throw new InputValidationError(`${field}: "${path}" is ${size(data.length)}; the maximum is ${size(bounds.max_bytes)}.`);
  }

  const mediaType = sniffImageMediaType(data);
  if (!mediaType || !bounds.formats.includes(mediaType)) {
    const accepted = bounds.formats.map((f) => f.replace('image/', '').toUpperCase()).join(', ');
    throw new InputValidationError(
      `${field}: "${path}" is not an accepted image (${accepted}), judged by its bytes, not its name.`,
    );
  }

  const dims = readImageDimensions(data, mediaType);
  if (!dims) {
    throw new InputValidationError(`${field}: "${path}" has an unreadable ${mediaType} header.`);
  }
  const { width, height } = dims;
  if (Math.min(width, height) < bounds.min_edge || Math.max(width, height) > bounds.max_edge) {
    throw new InputValidationError(
      `${field}: "${path}" is ${width}×${height} px; each edge must be ${bounds.min_edge} to ` +
        `${bounds.max_edge} px. Resize to ${bounds.max_edge} px on the long edge before submitting.`,
    );
  }

  return { type: 'image', data, mediaType };
}
