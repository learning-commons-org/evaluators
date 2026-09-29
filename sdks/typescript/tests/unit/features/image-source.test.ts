import { describe, it, expect, afterAll } from 'vitest';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  loadImage,
  readImageDimensions,
  sniffImageMediaType,
  type ImageBounds,
} from '../../../src/features/image-source.js';
import { InputValidationError } from '../../../src/errors.js';
import INPUT_SCHEMA from '../../../../../evals/graphics/math/graphics-accuracy/input_schema.json';

/** The bounds a real contract declares, so these tests exercise the numbers that ship. */
const BOUNDS = INPUT_SCHEMA.properties.image_paths.items['x-image'] as ImageBounds;
const LADYBIRDS = join(process.cwd(), '..', '..', 'evals/graphics/math/graphics-accuracy/images/ladybirds.png');

const pad = (head: number[], size = 100) => {
  const out = new Uint8Array(size);
  out.set(head);
  return out;
};
const be32 = (n: number) => [(n >>> 24) & 0xff, (n >>> 16) & 0xff, (n >>> 8) & 0xff, n & 0xff];
const be16 = (n: number) => [(n >>> 8) & 0xff, n & 0xff];
const le24 = (n: number) => [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff];

/** A PNG header declaring `w`×`h`: signature, then an IHDR chunk. */
const png = (w: number, h: number) =>
  pad([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52, ...be32(w), ...be32(h)]);
/** A JPEG with an APP0 segment followed by a baseline start-of-frame declaring `w`×`h`. */
const jpeg = (w: number, h: number) =>
  pad([0xff, 0xd8, 0xff, 0xe0, 0, 4, 0, 0, 0xff, 0xc0, 0, 17, 8, ...be16(h), ...be16(w), 3]);
/** An extended WebP (VP8X) declaring a `w`×`h` canvas. */
const webpX = (w: number, h: number) =>
  pad([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50, 0x38, 0x58, 10, 0, 0, 0, 0, 0, 0, 0, ...le24(w - 1), ...le24(h - 1)]);
/** A lossless WebP (VP8L) declaring `w`×`h`. */
const webpL = (w: number, h: number) => {
  const bits = ((w - 1) & 0x3fff) | (((h - 1) & 0x3fff) << 14);
  return pad([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50, 0x38, 0x4c, 0, 0, 0, 0, 0x2f,
    bits & 0xff, (bits >>> 8) & 0xff, (bits >>> 16) & 0xff, (bits >>> 24) & 0xff]);
};
/** A lossy WebP (VP8) declaring `w`×`h`. */
const webp = (w: number, h: number) =>
  pad([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50, 0x38, 0x20, 0, 0, 0, 0,
    0, 0, 0, 0x9d, 0x01, 0x2a, w & 0xff, (w >>> 8) & 0x3f, h & 0xff, (h >>> 8) & 0x3f]);

describe('sniffImageMediaType', () => {
  it('recognises PNG, JPEG and WebP by their signatures', () => {
    expect(sniffImageMediaType(png(1, 1))).toBe('image/png');
    expect(sniffImageMediaType(jpeg(1, 1))).toBe('image/jpeg');
    expect(sniffImageMediaType(webpX(1, 1))).toBe('image/webp');
  });

  it('rejects anything else, including a GIF and a forged PNG prefix', () => {
    expect(sniffImageMediaType(pad([0x47, 0x49, 0x46, 0x38, 0x39, 0x61]))).toBeUndefined();
    // The four "PNG" letters alone are not the signature; all eight bytes are.
    expect(sniffImageMediaType(pad([0x89, 0x50, 0x4e, 0x47, 0, 0, 0, 0]))).toBeUndefined();
    expect(sniffImageMediaType(new TextEncoder().encode('not an image'))).toBeUndefined();
    expect(sniffImageMediaType(new Uint8Array(0))).toBeUndefined();
  });
});

describe('readImageDimensions', () => {
  it('reads each format from its header', () => {
    expect(readImageDimensions(png(640, 480), 'image/png')).toEqual({ width: 640, height: 480 });
    expect(readImageDimensions(jpeg(1024, 768), 'image/jpeg')).toEqual({ width: 1024, height: 768 });
    expect(readImageDimensions(webpX(2560, 16), 'image/webp')).toEqual({ width: 2560, height: 16 });
    expect(readImageDimensions(webpL(300, 200), 'image/webp')).toEqual({ width: 300, height: 200 });
    expect(readImageDimensions(webp(800, 600), 'image/webp')).toEqual({ width: 800, height: 600 });
  });

  it('reads a real fixture image', () => {
    const dims = readImageDimensions(new Uint8Array(readFileSync(LADYBIRDS)), 'image/png');
    expect(dims?.width).toBeGreaterThan(0);
    expect(dims?.height).toBeGreaterThan(0);
  });

  it('returns undefined for a JPEG with no start-of-frame marker', () => {
    expect(readImageDimensions(pad([0xff, 0xd8, 0xff, 0xd9]), 'image/jpeg')).toBeUndefined();
  });

  it('returns undefined when the marker bytes after a valid signature are wrong', () => {
    // A PNG whose first chunk is not IHDR, so the bytes at 16..23 are not dimensions.
    const notIhdr = png(640, 480);
    notIhdr.set([0x74, 0x45, 0x58, 0x74], 12); // "tEXt"
    expect(readImageDimensions(notIhdr, 'image/png')).toBeUndefined();
    // VP8 without its 9d 01 2a start code; VP8L without its 0x2f signature byte.
    const vp8 = webp(800, 600);
    vp8[23] = 0;
    expect(readImageDimensions(vp8, 'image/webp')).toBeUndefined();
    const vp8l = webpL(300, 200);
    vp8l[20] = 0;
    expect(readImageDimensions(vp8l, 'image/webp')).toBeUndefined();
  });
});

describe('loadImage', () => {
  const dir = mkdtempSync(join(tmpdir(), 'image-source-'));
  afterAll(() => rmSync(dir, { recursive: true, force: true }));
  const file = (name: string, bytes: Uint8Array) => {
    const path = join(dir, name);
    writeFileSync(path, bytes);
    return path;
  };

  it('returns an attachment with the sniffed media type and the exact bytes', async () => {
    const bytes = png(512, 256);
    const part = await loadImage('image_paths[0]', file('chart.dat', bytes), BOUNDS); // extension deliberately meaningless
    expect(part).toEqual({ type: 'image', data: bytes, mediaType: 'image/png' });
  });

  it('accepts a real fixture image within the shipped bounds', async () => {
    const part = await loadImage('image_paths[0]', LADYBIRDS, BOUNDS);
    expect(part.mediaType).toBe('image/png');
  });

  it('names the field and position in every error', async () => {
    await expect(loadImage('image_paths[2]', join(dir, 'missing.png'), BOUNDS)).rejects.toThrow(
      /^image_paths\[2\]: could not read file/,
    );
  });

  it('rejects a file that is not an accepted image by its bytes', async () => {
    const path = file('note.png', pad([...new TextEncoder().encode('not an image')]));
    await expect(loadImage('f', path, BOUNDS)).rejects.toThrow(InputValidationError);
    await expect(loadImage('f', path, BOUNDS)).rejects.toThrow(/not an accepted image \(PNG, JPEG, WEBP\)/);
  });

  it('rejects a format the contract does not list', async () => {
    const pngOnly: ImageBounds = { ...BOUNDS, formats: ['image/png'] };
    await expect(loadImage('f', file('photo.jpg', jpeg(100, 100)), pngOnly)).rejects.toThrow(/\(PNG\)/);
  });

  it('rejects a file below min_bytes, including an empty one', async () => {
    await expect(loadImage('f', file('empty.png', new Uint8Array(0)), BOUNDS)).rejects.toThrow(/0 bytes \(0\.00 MB\); the minimum is 64 bytes/);
    await expect(loadImage('f', file('tiny.png', png(20, 20).slice(0, 40)), BOUNDS)).rejects.toThrow(/minimum is 64/);
  });

  it('rejects a file over max_bytes by its size on disk', async () => {
    const big = new Uint8Array(BOUNDS.max_bytes + 1);
    big.set(png(100, 100));
    await expect(loadImage('f', file('huge.png', big), BOUNDS)).rejects.toThrow(/5,242,881 bytes \(5\.00 MB\); the maximum is 5,242,880 bytes/);
  });

  it('rejects an edge below min_edge', async () => {
    await expect(loadImage('f', file('small.png', png(10, 400)), BOUNDS)).rejects.toThrow(/10×400 px; each edge must be 16 to 2560/);
  });

  it('rejects an edge above max_edge and says how to fix it', async () => {
    await expect(loadImage('f', file('wide.webp', webpX(2677, 1605)), BOUNDS)).rejects.toThrow(
      /2677×1605 px.*Resize to 2560 px on the long edge/,
    );
  });

  it('accepts both edges exactly at the bounds', async () => {
    await expect(loadImage('f', file('edge.png', png(2560, 16)), BOUNDS)).resolves.toMatchObject({ mediaType: 'image/png' });
  });

  it('rejects a path that is not a regular file, rather than reading it unbounded', async () => {
    await expect(loadImage('f', dir, BOUNDS)).rejects.toThrow(/is not a regular file/);
  });

  it('refuses a FIFO without blocking on it', async () => {
    const fifo = join(dir, 'pipe.png');
    execFileSync('mkfifo', [fifo]);
    // With a blocking open this would hang until a writer appeared; the test timeout would fail it.
    await expect(loadImage('f', fifo, BOUNDS)).rejects.toThrow(/is not a regular file/);
  });

  it('rejects a header it cannot read', async () => {
    await expect(loadImage('f', file('bad.jpg', pad([0xff, 0xd8, 0xff, 0xd9])), BOUNDS)).rejects.toThrow(/unreadable image\/jpeg header/);
  });
});
