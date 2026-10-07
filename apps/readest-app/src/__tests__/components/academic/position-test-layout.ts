import { vi } from 'vitest';

/** Deterministic line layout for jsdom; real wrapping still needs native acceptance. */
export function mockReadingLayout(
  root: HTMLElement,
  block: HTMLElement,
  lineHeight: () => number,
  charactersPerLine: () => number = () => 10,
  contentTop: () => number = () => 0,
) {
  const rect = (top: number, height: number) => new DOMRect(20, top, 400, height);
  const characterY = (offset: number) =>
    60 + contentTop() + Math.floor(offset / charactersPerLine()) * lineHeight() - root.scrollTop;
  vi.spyOn(root, 'getBoundingClientRect').mockImplementation(() => rect(60, 740));
  vi.spyOn(block, 'getBoundingClientRect').mockImplementation(() =>
    rect(
      60 + contentTop() - root.scrollTop,
      Math.ceil((block.textContent?.length ?? 0) / charactersPerLine()) * lineHeight(),
    ),
  );
  const nativeRange = document.createRange.bind(document);
  const textOffset = (target: Node, offset: number) => {
    const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    let total = 0;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.parentElement?.closest('button, [aria-hidden="true"]')) continue;
      if (node === target) return total + offset;
      total += node.textContent?.length ?? 0;
    }
    return offset;
  };
  vi.spyOn(document, 'createRange').mockImplementation(() => {
    const range = nativeRange();
    const bounds = () => {
      const startOffset = textOffset(range.startContainer, range.startOffset);
      const endOffset = textOffset(range.endContainer, range.endOffset);
      const start = characterY(startOffset);
      const end = characterY(Math.max(startOffset, endOffset - 1)) + lineHeight();
      return rect(start, end - start);
    };
    Object.defineProperties(range, {
      getBoundingClientRect: { value: bounds },
      getClientRects: { value: () => [bounds()] },
    });
    return range;
  });
  return { characterY };
}
