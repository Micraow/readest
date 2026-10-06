import { useEffect, useRef } from 'react';

const STATE_KEY = 'readestAcademicLayers';
type Layer = { id: string; close: () => void; pushed: boolean; dismissed: boolean };
const layers: Layer[] = [];
const removed = new Set<string>();
let sequence = 0;
let listening = false;
let traversing = false;
const session = Math.random().toString(36).slice(2);

const historyLayers = (): string[] => {
  const value: unknown = window.history.state?.[STATE_KEY];
  return Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string') : [];
};

function reconcile() {
  if (traversing) return;
  const current = historyLayers();
  const firstRemoved = current.findIndex((id) => removed.has(id));
  if (firstRemoved >= 0) {
    traversing = true;
    window.history.go(firstRemoved - current.length);
    return;
  }
  removed.clear();
  // An immediate reopen can happen before the preceding history.back finishes.
  // Queue its entry until that traversal settles, rather than popping the new UI.
  for (const layer of layers) {
    if (layer.pushed || layer.dismissed) continue;
    const ids = historyLayers();
    window.history.pushState({ ...window.history.state, [STATE_KEY]: [...ids, layer.id] }, '');
    layer.pushed = true;
  }
}

function handlePopState() {
  const wasTraversing = traversing;
  traversing = false;
  const ids = historyLayers();
  if (!wasTraversing) {
    for (const layer of [...layers].reverse()) {
      if (layer.pushed && !layer.dismissed && !ids.includes(layer.id)) {
        layer.dismissed = true;
        layer.close();
      }
    }
    // Forward must not silently reopen a parser or a closed document. Skip
    // obsolete same-URL overlay entries, retaining the live underlying layer.
    const obsolete = ids.findIndex(
      (id) => !layers.some((layer) => layer.id === id && !layer.dismissed),
    );
    if (obsolete >= 0) {
      for (const id of ids.slice(obsolete)) removed.add(id);
    }
  }
  reconcile();
}

/** Browser Back counterpart to the native/Escape modal stack; no PDF data in history. */
export function useAcademicHistory(open: boolean, onClose: () => void) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) return;
    if (!listening) {
      // Keep one listener after dismissal to handle Forward into stale entries.
      // Closed layers/callbacks are removed below; no File or parser is retained.
      window.addEventListener('popstate', handlePopState);
      listening = true;
    }
    const layer: Layer = {
      id: `${session}-${++sequence}`,
      close: () => close.current(),
      pushed: false,
      dismissed: false,
    };
    layers.push(layer);
    reconcile();
    return () => {
      layers.splice(layers.indexOf(layer), 1);
      if (layer.pushed) removed.add(layer.id);
      reconcile();
    };
  }, [open]);
}
