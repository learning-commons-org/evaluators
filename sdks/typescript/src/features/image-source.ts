import { constants } from 'node:fs';
import { open, type FileHandle } from 'node:fs/promises';
import { imageSize } from 'image-size';
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

const MEDIA_TYPES: Record<string, ImageMediaType> = { png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp' };

/**
 * Format and dimensions read from the image's own bytes — its signature and header, without
 * decoding pixels — or undefined when the bytes are not a PNG, JPEG or WebP with a readable
 * header, whatever the file is named.
 */
export function inspectImage(bytes: Uint8Array): { mediaType: ImageMediaType; width: number; height: number } | undefined {
  try {
    const { type, width, height } = imageSize(bytes);
    const mediaType = type ? MEDIA_TYPES[type] : undefined;
    return mediaType && width > 0 && height > 0 ? { mediaType, width, height } : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Read at most `limit` bytes from an open file. A file that grew after `stat` is cut off here
 * rather than read whole; the caller's size check then rejects it. The result is a right-sized
 * copy, so an attachment does not hold the `limit`-sized read buffer.
 */
async function readBounded(file: FileHandle, limit: number): Promise<Uint8Array> {
  const buffer = new Uint8Array(limit);
  let total = 0;
  while (total < limit) {
    const { bytesRead } = await file.read(buffer, total, limit - total, total);
    if (bytesRead === 0) break;
    total += bytesRead;
  }
  return buffer.slice(0, total);
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
 * @throws {InputValidationError} if the file cannot be read, is not an accepted format with a
 * readable header by its bytes, or falls outside the declared size or edge bounds
 */
export async function loadImage(
  field: string,
  path: string,
  bounds: ImageBounds,
): Promise<Omit<ImageAttachment, 'position'>> {
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

  const image = inspectImage(data);
  if (!image || !bounds.formats.includes(image.mediaType)) {
    const accepted = bounds.formats.map((f) => f.replace('image/', '').toUpperCase()).join(', ');
    throw new InputValidationError(
      `${field}: "${path}" is not an accepted image (${accepted}), judged by its bytes, not its name.`,
    );
  }
  const { mediaType, width, height } = image;
  if (Math.min(width, height) < bounds.min_edge || Math.max(width, height) > bounds.max_edge) {
    throw new InputValidationError(
      `${field}: "${path}" is ${width}×${height} px; each edge must be ${bounds.min_edge} to ` +
        `${bounds.max_edge} px. Resize to ${bounds.max_edge} px on the long edge before submitting.`,
    );
  }

  return { type: 'image', data, mediaType };
}
