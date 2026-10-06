import { describe, it, expect, afterAll } from 'vitest';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { inspectImage, loadImage, type ImageBounds } from '../../../src/features/image-source.js';
import { InputValidationError } from '../../../src/errors.js';
import INPUT_SCHEMA from '../../../../../evals/graphics/math/graphics-accuracy/input_schema.json';

/** The bounds a real contract declares, so these tests exercise the numbers that ship. */
const BOUNDS = INPUT_SCHEMA.properties.image_paths.items['x-image'] as ImageBounds;
const CONTRACT_IMAGE = join(process.cwd(), '..', '..', 'evals/graphics/math/graphics-accuracy/images/apples-in-baskets.png');

/** Real images, each named for its size and format. */
const image = (name: string) => join(process.cwd(), 'tests/fixtures/images', name);
const bytesOf = (name: string) => new Uint8Array(readFileSync(image(name)));

describe('inspectImage', () => {
  it('reads the format and dimensions of PNG, JPEG and WebP', () => {
    expect(inspectImage(bytesOf('512x256.png'))).toEqual({ mediaType: 'image/png', width: 512, height: 256 });
    expect(inspectImage(bytesOf('512x256.jpg'))).toEqual({ mediaType: 'image/jpeg', width: 512, height: 256 });
    expect(inspectImage(bytesOf('512x256.webp'))).toEqual({ mediaType: 'image/webp', width: 512, height: 256 });
  });

  it('rejects anything else: a GIF, a truncated image, text and nothing', () => {
    expect(inspectImage(bytesOf('512x256.gif'))).toBeUndefined();
    expect(inspectImage(bytesOf('512x256.png').slice(0, 8))).toBeUndefined();
    expect(inspectImage(new TextEncoder().encode('not an image'))).toBeUndefined();
    expect(inspectImage(new Uint8Array(0))).toBeUndefined();
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

  it('returns an attachment with the detected media type and the exact bytes', async () => {
    const bytes = bytesOf('512x256.png');
    const part = await loadImage('image_paths[0]', file('chart.dat', bytes), BOUNDS); // extension deliberately meaningless
    expect(part).toEqual({ type: 'image', data: bytes, mediaType: 'image/png' });
  });

  it('reports the media type of each accepted format', async () => {
    await expect(loadImage('f', image('512x256.jpg'), BOUNDS)).resolves.toMatchObject({ mediaType: 'image/jpeg' });
    await expect(loadImage('f', image('512x256.webp'), BOUNDS)).resolves.toMatchObject({ mediaType: 'image/webp' });
  });

  it('accepts a file exactly at min_bytes or max_bytes, and refuses one byte beyond either', async () => {
    const path = image('512x256.png');
    const n = bytesOf('512x256.png').length;
    await expect(loadImage('f', path, { ...BOUNDS, min_bytes: n })).resolves.toMatchObject({ mediaType: 'image/png' });
    await expect(loadImage('f', path, { ...BOUNDS, max_bytes: n })).resolves.toMatchObject({ mediaType: 'image/png' });
    await expect(loadImage('f', path, { ...BOUNDS, min_bytes: n + 1 })).rejects.toThrow(/the minimum is/);
    await expect(loadImage('f', path, { ...BOUNDS, max_bytes: n - 1 })).rejects.toThrow(/the maximum is/);
  });

  it('returns bytes that do not hold the max_bytes read buffer', async () => {
    const part = await loadImage('f', image('512x256.png'), BOUNDS);
    expect(part.data.buffer.byteLength).toBe(bytesOf('512x256.png').length);
  });

  it('accepts a real contract image within the shipped bounds', async () => {
    const part = await loadImage('image_paths[0]', CONTRACT_IMAGE, BOUNDS);
    expect(part.mediaType).toBe('image/png');
  });

  it('names the field and position in every error', async () => {
    await expect(loadImage('image_paths[2]', join(dir, 'missing.png'), BOUNDS)).rejects.toThrow(
      /^image_paths\[2\]: could not read file/,
    );
  });

  it('rejects a file that is not an accepted image by its bytes', async () => {
    const path = file('note.png', new TextEncoder().encode('not an image. '.repeat(10)));
    await expect(loadImage('f', path, BOUNDS)).rejects.toThrow(InputValidationError);
    await expect(loadImage('f', path, BOUNDS)).rejects.toThrow(/not an accepted image \(PNG, JPEG, WEBP\)/);
    await expect(loadImage('f', image('512x256.gif'), BOUNDS)).rejects.toThrow(/not an accepted image/);
  });

  it('rejects a format the contract does not list', async () => {
    const pngOnly: ImageBounds = { ...BOUNDS, formats: ['image/png'] };
    await expect(loadImage('f', image('512x256.jpg'), pngOnly)).rejects.toThrow(/\(PNG\)/);
  });

  it('rejects a file below min_bytes, including an empty one', async () => {
    await expect(loadImage('f', file('empty.png', new Uint8Array(0)), BOUNDS)).rejects.toThrow(/0 bytes \(0\.00 MB\); the minimum is 64 bytes/);
    await expect(loadImage('f', file('tiny.png', bytesOf('512x256.png').slice(0, 40)), BOUNDS)).rejects.toThrow(/minimum is 64/);
  });

  it('rejects a file over max_bytes by its size on disk', async () => {
    const big = new Uint8Array(BOUNDS.max_bytes + 1);
    big.set(bytesOf('512x256.png'));
    await expect(loadImage('f', file('huge.png', big), BOUNDS)).rejects.toThrow(/5,242,881 bytes \(5\.00 MB\); the maximum is 5,242,880 bytes/);
  });

  it('rejects an edge below min_edge', async () => {
    await expect(loadImage('f', image('10x400.png'), BOUNDS)).rejects.toThrow(/10×400 px; each edge must be 16 to 2560/);
  });

  it('rejects an edge above max_edge and says how to fix it', async () => {
    await expect(loadImage('f', image('2677x1605.png'), BOUNDS)).rejects.toThrow(
      /2677×1605 px.*Resize to 2560 px on the long edge/,
    );
  });

  it('accepts both edges exactly at the bounds', async () => {
    await expect(loadImage('f', image('2560x16.png'), BOUNDS)).resolves.toMatchObject({ mediaType: 'image/png' });
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

  it('rejects an image cut off before its dimensions', async () => {
    const cut = file('cut.jpg', bytesOf('512x256.jpg').slice(0, 100));
    await expect(loadImage('f', cut, BOUNDS)).rejects.toThrow(/not an accepted image/);
  });
});
