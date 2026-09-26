import { describe, it, expect, vi, afterEach, afterAll } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadImage, sniffImageMediaType, MAX_IMAGE_BYTES } from '../../../src/features/image-source.js';
import { InputValidationError } from '../../../src/errors.js';

const PNG = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3]);
const JPEG = Uint8Array.from([0xff, 0xd8, 0xff, 0xe0, 0, 0x10, 0x4a, 0x46]);
const WEBP = Uint8Array.from([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50]);
const GIF = Uint8Array.from([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0, 0, 0, 0, 0, 0]);

describe('sniffImageMediaType', () => {
  it('recognises PNG, JPEG and WEBP by their signatures', () => {
    expect(sniffImageMediaType(PNG)).toBe('image/png');
    expect(sniffImageMediaType(JPEG)).toBe('image/jpeg');
    expect(sniffImageMediaType(WEBP)).toBe('image/webp');
  });

  it('rejects anything else, including a GIF and plain text', () => {
    expect(sniffImageMediaType(GIF)).toBeUndefined();
    // The four "PNG" letters alone are not the signature; all eight bytes are.
    expect(sniffImageMediaType(Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0, 0, 0, 0, 1, 2]))).toBeUndefined();
    expect(sniffImageMediaType(new TextEncoder().encode('not an image'))).toBeUndefined();
    expect(sniffImageMediaType(new Uint8Array(0))).toBeUndefined();
  });
});

describe('loadImage from a local path', () => {
  const dir = mkdtempSync(join(tmpdir(), 'image-source-'));
  afterEach(() => vi.restoreAllMocks());
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  it('returns an attachment with the sniffed media type and the exact bytes', async () => {
    const path = join(dir, 'chart.dat'); // extension deliberately meaningless
    writeFileSync(path, PNG);
    const part = await loadImage('image', path);
    expect(part).toEqual({ type: 'image', data: PNG, mediaType: 'image/png' });
  });

  it('rejects a file that is not an accepted image format', async () => {
    const path = join(dir, 'anim.png'); // named .png, actually a GIF
    writeFileSync(path, GIF);
    await expect(loadImage('image', path)).rejects.toThrow(InputValidationError);
    await expect(loadImage('image', path)).rejects.toThrow(/not a PNG, JPEG or WEBP/);
  });

  it('rejects a missing file as the caller\'s input, not a dependency failure', async () => {
    await expect(loadImage('image', join(dir, 'missing.png'))).rejects.toThrow(InputValidationError);
    await expect(loadImage('image', join(dir, 'missing.png'))).rejects.toThrow(/could not read file/);
  });

  it('rejects an empty file', async () => {
    const path = join(dir, 'empty.png');
    writeFileSync(path, new Uint8Array(0));
    await expect(loadImage('image', path)).rejects.toThrow(/is empty/);
  });

  it('rejects a file over the 10 MB cap by its size, before reading it', async () => {
    const path = join(dir, 'huge.png');
    const big = new Uint8Array(MAX_IMAGE_BYTES + 1);
    big.set(PNG, 0);
    writeFileSync(path, big);
    await expect(loadImage('image', path)).rejects.toThrow(/maximum is 10 MB/);
    rmSync(path);
  });
});

describe('loadImage from a URL', () => {
  afterEach(() => vi.restoreAllMocks());

  it('fetches the bytes with a timeout and sniffs them', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JPEG, { status: 200 }));
    const part = await loadImage('image', 'https://example.org/figure');
    expect(part.mediaType).toBe('image/jpeg');
    expect(part.data).toEqual(JPEG);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe('https://example.org/figure');
    expect((init as { signal?: unknown }).signal).toBeInstanceOf(AbortSignal);
  });

  it('reports a non-2xx status as the caller\'s input', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('nope', { status: 404 }));
    await expect(loadImage('image', 'https://example.org/gone.png')).rejects.toThrow(/HTTP 404/);
  });

  it('reports a network failure as the caller\'s input, keeping the cause', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('fetch failed'));
    const err = await loadImage('image', 'https://example.org/x.png').catch((e) => e);
    expect(err).toBeInstanceOf(InputValidationError);
    expect(err.message).toMatch(/could not fetch/);
    expect(err.cause).toBeInstanceOf(TypeError);
  });

  it('refuses an oversized response from its Content-Length before downloading it', async () => {
    const body = new ReadableStream({ pull() { throw new Error('body must not be read'); } });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(body, { status: 200, headers: { 'content-length': String(MAX_IMAGE_BYTES + 1) } }),
    );
    await expect(loadImage('image', 'https://example.org/huge.png')).rejects.toThrow(/maximum is 10 MB/);
  });

  it('stops reading an unlabelled response once it passes the cap', async () => {
    const chunk = new Uint8Array(1024 * 1024); // 1 MB per pull, no Content-Length
    chunk.set(PNG, 0);
    let pulls = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) { pulls++; controller.enqueue(chunk); },
    });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(body, { status: 200 }));
    await expect(loadImage('image', 'https://example.org/stream.png')).rejects.toThrow(/maximum is 10 MB/);
    // Cut off just past the cap: 11 reads, not an unbounded number.
    expect(pulls).toBeLessThanOrEqual(12);
  });

  it('reports a body that fails mid-stream as the caller\'s input, keeping the cause', async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(PNG);
        controller.error(new Error('connection reset'));
      },
    });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(body, { status: 200 }));
    const err = await loadImage('image', 'https://example.org/reset.png').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(InputValidationError);
    expect((err as Error).message).toMatch(/could not be read/);
    expect(((err as Error).cause as Error).message).toBe('connection reset');
  });
});
