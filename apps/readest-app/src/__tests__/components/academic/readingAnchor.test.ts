import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  captureReadingAnchor,
  isReadingAnchor,
  restoreReadingAnchor,
} from '@/components/academic/readingAnchor';
import { mockReadingLayout } from './position-test-layout';

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe('stable academic text anchors', () => {
  it('stores a character across styled text nodes, not an old line or paragraph pixel', () => {
    const root = document.createElement('div');
    const block = document.createElement('p');
    block.dataset['blockId'] = 'long';
    block.innerHTML = `<span>${'0123456789'.repeat(10)}</span><em>${'abcdefghij'.repeat(20)}</em>`;
    root.append(block);
    document.body.append(root);
    let lineHeight = 20;
    const { characterY } = mockReadingLayout(root, block, () => lineHeight);
    root.scrollTop = 400;
    const anchor = captureReadingAnchor(root)!;
    expect(anchor).toMatchObject({ blockId: 'long', textOffset: 200, viewportY: 0 });
    const persisted = JSON.parse(JSON.stringify(anchor));
    expect(isReadingAnchor(persisted)).toBe(true);
    // The same content is remounted; preserving a Text object would now fail.
    block.innerHTML = `<strong>${'0123456789'.repeat(10)}</strong><span>${'abcdefghij'.repeat(20)}</span>`;
    lineHeight = 30;
    expect(restoreReadingAnchor(root, persisted)).toBe(true);
    expect(root.scrollTop).toBe(600);
    expect(characterY(200)).toBe(60);
    lineHeight = 20;
    restoreReadingAnchor(root, persisted);
    expect(root.scrollTop).toBe(400);
  });

  it('ignores asynchronous inline-canvas error text when resolving a saved character', () => {
    const root = document.createElement('div');
    const block = document.createElement('p');
    block.dataset['blockId'] = 'math-prose';
    block.innerHTML = `<span>${'a'.repeat(100)}</span><button><canvas></canvas></button><span>${'b'.repeat(200)}</span>`;
    root.append(block);
    document.body.append(root);
    let lineHeight = 20;
    mockReadingLayout(root, block, () => lineHeight);
    root.scrollTop = 400;
    const anchor = captureReadingAnchor(root)!;
    expect(anchor.textOffset).toBe(200);
    block.querySelector('button')!.append('Fallback math source');
    lineHeight = 30;
    restoreReadingAnchor(root, anchor);
    expect(root.scrollTop).toBe(600);
  });

  it('uses a within-figure ratio and retains its viewport offset when a picture resizes', () => {
    const root = document.createElement('div');
    const figure = document.createElement('figure');
    figure.dataset['blockId'] = 'figure';
    figure.dataset['academicVisual'] = '';
    figure.textContent = 'Tap to zoom';
    root.append(figure);
    document.body.append(root);
    let height = 200;
    root.scrollTop = 100;
    vi.spyOn(root, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 60, 500, 740));
    vi.spyOn(figure, 'getBoundingClientRect').mockImplementation(
      () => new DOMRect(0, 60 - root.scrollTop, 400, height),
    );
    const anchor = captureReadingAnchor(root)!;
    expect(anchor).toEqual({ blockId: 'figure', viewportY: 0, blockRatio: 0.5 });
    height = 400;
    restoreReadingAnchor(root, anchor);
    expect(root.scrollTop).toBe(200);
  });

  it('rejects corrupt anchors and safely declines missing blocks', () => {
    expect(isReadingAnchor({ blockId: 'p', viewportY: NaN, blockRatio: 0 })).toBe(false);
    expect(isReadingAnchor({ blockId: 'p', viewportY: 0, blockRatio: 2 })).toBe(false);
    expect(isReadingAnchor({ blockId: 'p', viewportY: 0, blockRatio: 0, textOffset: -1 })).toBe(
      false,
    );
    expect(
      restoreReadingAnchor(document.createElement('div'), {
        blockId: 'missing',
        viewportY: 0,
        blockRatio: 0,
      }),
    ).toBe(false);
  });
});
