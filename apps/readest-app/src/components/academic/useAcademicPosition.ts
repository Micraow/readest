import { useCallback, useImperativeHandle, useLayoutEffect, useRef, type RefObject } from 'react';
import {
  captureReadingAnchor,
  isReadingAnchor,
  restoreReadingAnchor,
  type ReadingAnchor,
} from './readingAnchor';

export interface AcademicPositionControl {
  prepare: () => void;
  restore: () => void;
}

export function useAcademicPosition(
  root: RefObject<HTMLDivElement | null>,
  fingerprint: string,
  control?: RefObject<AcademicPositionControl | null>,
) {
  const rememberRef = useRef<() => void>(() => {});
  const commands = useRef<AcademicPositionControl | null>(null);
  const remember = useCallback(() => rememberRef.current(), []);
  useImperativeHandle(
    control,
    () => ({
      prepare: () => commands.current?.prepare(),
      restore: () => commands.current?.restore(),
    }),
    [],
  );
  useLayoutEffect(() => {
    const element = root.current;
    const article = element?.querySelector('article');
    if (!element || !article) return;
    const key = `readest:academic-position:${fingerprint}`;
    let anchor: ReadingAnchor | null = null;
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(key) ?? 'null');
      if (typeof saved === 'number' && Number.isFinite(saved) && saved >= 0) {
        element.scrollTop = saved;
      } else if (saved && typeof saved === 'object' && 'scrollTop' in saved) {
        if (typeof saved.scrollTop === 'number' && Number.isFinite(saved.scrollTop))
          element.scrollTop = Math.max(0, saved.scrollTop);
        if (
          'anchor' in saved &&
          isReadingAnchor(saved.anchor) &&
          restoreReadingAnchor(element, saved.anchor)
        )
          anchor = saved.anchor;
      }
    } catch {
      /* Missing or old device-local state is optional. */
    }
    const dimensions = () => [element.clientWidth, article.getBoundingClientRect().height];
    let [width, height] = dimensions();
    let lastScrollTop = element.scrollTop;
    const changed = () => {
      const [nextWidth, nextHeight] = dimensions();
      return nextWidth !== width || nextHeight !== height;
    };
    const rememberNow = () => {
      [width, height] = dimensions();
      anchor = captureReadingAnchor(element);
      lastScrollTop = element.scrollTop;
    };
    rememberRef.current = rememberNow;
    anchor ??= captureReadingAnchor(element);
    const moved = () => Math.abs(element.scrollTop - lastScrollTop) > 0.5;
    const restorePosition = () => {
      [width, height] = dimensions();
      if (anchor) restoreReadingAnchor(element, anchor);
      lastScrollTop = element.scrollTop;
      // Keep the original character: the new line can start before it after wrapping.
    };
    commands.current = {
      prepare: () => {
        if (changed()) restorePosition();
        if (!anchor || moved()) rememberNow();
      },
      restore: restorePosition,
    };
    let timer: ReturnType<typeof setTimeout> | undefined;
    const save = () => {
      if (!changed() && moved()) rememberNow(); // close/pagehide can precede a pending scroll event
      try {
        localStorage.setItem(
          key,
          anchor
            ? JSON.stringify({ version: 1, anchor, scrollTop: element.scrollTop })
            : String(element.scrollTop),
        );
      } catch {
        /* Full device storage does not block reading. */
      }
    };
    const onScroll = () => {
      // A resize can emit scroll before ResizeObserver. Keep the pre-layout anchor.
      if (!changed() && moved()) rememberNow();
      if (!timer)
        timer = setTimeout(() => {
          timer = undefined;
          save();
        }, 250);
    };
    const onResize = () => {
      if (!changed()) return;
      restorePosition();
    };
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(onResize);
    observer?.observe(element);
    observer?.observe(article); // PDF canvases can finish sizing after the first font-layout pass.
    element.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    window.addEventListener('pagehide', save);
    return () => {
      if (timer) clearTimeout(timer);
      save();
      rememberRef.current = () => {};
      commands.current = null;
      observer?.disconnect();
      element.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('pagehide', save);
    };
  }, [root, fingerprint]);
  return { remember };
}
