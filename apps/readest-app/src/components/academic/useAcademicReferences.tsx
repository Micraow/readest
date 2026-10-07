import {
  useId,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from 'react';
import {
  buildAcademicNavigation,
  contentSlotKey,
  navigationElementId,
  type AcademicLink,
} from '@/services/academic/navigation';
import type { ScholarlyDocument } from '@/services/academic/types';
import { useAcademicHistory } from './useAcademicHistory';

export interface AcademicReferenceControl {
  returnToReading: () => boolean;
}
interface ReturnEntry {
  id: number;
  anchor: string;
  offset: number;
  focus: HTMLElement;
}

/** A separate history layer for every jump also handles Back through nested references. */
export function ReferenceHistoryLayer({ onReturn }: { onReturn: () => void }) {
  useAcademicHistory(true, onReturn);
  return null;
}

export function useAcademicReferences(
  document: ScholarlyDocument,
  root: RefObject<HTMLDivElement | null>,
  control?: RefObject<AcademicReferenceControl | null>,
) {
  const prefix = useId();
  const index = useMemo(() => buildAcademicNavigation(document), [document]);
  const [saved, setSaved] = useState<{ fingerprint: string; entries: ReturnEntry[] }>({
    fingerprint: document.fingerprint,
    entries: [],
  });
  const entries = saved.fingerprint === document.fingerprint ? saved.entries : [];
  const current = useRef(entries);
  current.current = entries;
  const sequence = useRef(0);
  const pending = useRef<{ anchor: string; offset: number; focus?: HTMLElement } | null>(null);
  const setEntries = (next: ReturnEntry[]) => {
    current.current = next;
    setSaved({ fingerprint: document.fingerprint, entries: next });
  };
  const returnToReading = (id?: number): boolean => {
    const position =
      id === undefined
        ? current.current.length - 1
        : current.current.findIndex((entry) => entry.id === id);
    const entry = current.current[position];
    if (!entry) return false;
    pending.current = entry;
    setEntries(current.current.slice(0, position));
    return true;
  };
  useImperativeHandle(control, () => ({ returnToReading }));
  useLayoutEffect(() => {
    const placement = pending.current;
    pending.current = null;
    if (!placement) return;
    const scroller = root.current;
    const anchor = window.document.getElementById(placement.anchor);
    if (!scroller || !anchor || !scroller.contains(anchor)) return;
    // Re-measure the clicked text after reflow/font changes; raw scrollTop would drift.
    scroller.scrollTop +=
      anchor.getBoundingClientRect().top - scroller.getBoundingClientRect().top - placement.offset;
    const focus = placement.focus?.isConnected ? placement.focus : anchor;
    focus.focus({ preventScroll: true });
  }, [saved, root]);

  const navigate = (link: AcademicLink, anchor: HTMLAnchorElement) => {
    const scroller = root.current;
    const target = navigationElementId(prefix, link.target);
    const destination = window.document.getElementById(target);
    if (!scroller || !destination || !scroller.contains(destination)) return;
    // Double taps must not add a second return entry. Keep the bounded stack intact.
    if (current.current.at(-1)?.anchor === anchor.id || current.current.length >= 16) return;
    const focused = window.document.activeElement;
    const entry: ReturnEntry = {
      id: ++sequence.current,
      anchor: anchor.id,
      offset: anchor.getBoundingClientRect().top - scroller.getBoundingClientRect().top,
      focus: focused instanceof HTMLElement && scroller.contains(focused) ? focused : anchor,
    };
    pending.current = { anchor: target, offset: 12 };
    setEntries([...current.current, entry]);
  };
  const targetProps = (blockId: string, item?: number) => {
    const key = contentSlotKey(blockId, item);
    return index.targets.has(key) ? { id: navigationElementId(prefix, key), tabIndex: -1 } : {};
  };
  const references = (blockId: string, item?: number) => ({
    links: index.links.get(contentSlotKey(blockId, item)) ?? [],
    prefix,
    onNavigate: navigate,
  });
  return { entries, returnToReading, targetProps, references };
}
