/** A UI-only position, independent of PDF parsing and analysis caches. */
export interface ReadingAnchor {
  blockId: string;
  textOffset?: number;
  viewportY: number;
  blockRatio: number;
}

export function isReadingAnchor(value: unknown): value is ReadingAnchor {
  if (!value || typeof value !== 'object') return false;
  const anchor = value as Partial<ReadingAnchor>;
  return (
    typeof anchor.blockId === 'string' &&
    Number.isFinite(anchor.viewportY) &&
    Number.isFinite(anchor.blockRatio) &&
    anchor.blockRatio! >= 0 &&
    anchor.blockRatio! <= 1 &&
    (anchor.textOffset === undefined ||
      (Number.isSafeInteger(anchor.textOffset) && anchor.textOffset >= 0))
  );
}

function textNodes(block: HTMLElement): Text[] {
  const walker = block.ownerDocument.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    // Canvas error fallbacks and zoom controls may appear asynchronously.
    if (node.textContent && !node.parentElement?.closest('button, [aria-hidden="true"]'))
      nodes.push(node as Text);
  }
  return nodes;
}

const ratio = (y: number, top: number, height: number) =>
  height > 0 ? Math.max(0, Math.min(1, (y - top) / height)) : 0;

export function captureReadingAnchor(root: HTMLElement): ReadingAnchor | null {
  const viewport = root.getBoundingClientRect();
  const bottom = Number.isFinite(viewport.bottom) ? viewport.bottom : Infinity;
  for (const block of root.querySelectorAll<HTMLElement>('[data-block-id]')) {
    const rect = block.getBoundingClientRect();
    if (rect.bottom <= viewport.top || rect.top >= bottom || rect.bottom <= rect.top) continue;
    const point = Math.max(viewport.top, rect.top);
    const fallback: ReadingAnchor = {
      blockId: block.dataset['blockId']!,
      viewportY: point - viewport.top,
      blockRatio: ratio(point, rect.top, rect.bottom - rect.top),
    };
    const picture = block.hasAttribute('data-academic-visual')
      ? block.querySelector('button')
      : null;
    if (
      block.hasAttribute('data-academic-visual') &&
      (!picture || picture.getBoundingClientRect().bottom > viewport.top)
    )
      return fallback;
    const range = block.ownerDocument.createRange();
    if (typeof range.getBoundingClientRect !== 'function') return fallback;
    let offset = 0;
    for (const node of textNodes(block)) {
      range.selectNodeContents(node);
      const bounds = range.getBoundingClientRect();
      if (bounds.bottom > viewport.top + 1 && bounds.top < bottom && bounds.height > 0) {
        // Prefix bounds are monotone across wrapped lines, including styled spans.
        let low = 0,
          high = node.length - 1;
        while (low < high) {
          const mid = Math.floor((low + high) / 2);
          range.setEnd(node, mid + 1);
          if (range.getBoundingClientRect().bottom > viewport.top + 1) high = mid;
          else low = mid + 1;
        }
        range.setStart(node, low);
        range.setEnd(node, low + 1);
        const y = range.getBoundingClientRect().top;
        return {
          blockId: fallback.blockId,
          textOffset: offset + low,
          viewportY: y - viewport.top,
          blockRatio: ratio(y, rect.top, rect.bottom - rect.top),
        };
      }
      offset += node.length;
    }
    return fallback;
  }
  return null;
}

export function restoreReadingAnchor(root: HTMLElement, anchor: ReadingAnchor): boolean {
  const block = Array.from(root.querySelectorAll<HTMLElement>('[data-block-id]')).find(
    (node) => node.dataset['blockId'] === anchor.blockId,
  );
  if (!block) return false;
  const rect = block.getBoundingClientRect();
  let y = rect.top + anchor.blockRatio * (rect.bottom - rect.top);
  if (anchor.textOffset !== undefined) {
    let offset = anchor.textOffset;
    for (const node of textNodes(block)) {
      if (offset < node.length) {
        const range = block.ownerDocument.createRange();
        range.setStart(node, offset);
        range.setEnd(node, offset + 1);
        if (typeof range.getBoundingClientRect === 'function') {
          const character = range.getBoundingClientRect();
          if (character.height > 0) y = character.top;
        }
        break;
      }
      offset -= node.length;
    }
  }
  root.scrollTop += y - root.getBoundingClientRect().top - anchor.viewportY;
  return true;
}
