import { useLayoutEffect, useRef } from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  useAcademicPosition,
  type AcademicPositionControl,
} from '@/components/academic/useAcademicPosition';
import { mockReadingLayout } from './position-test-layout';

let columns = 10;
let beforeHeight = 0;
let notifyResize = () => {};
let rememberNavigation = () => {};
let characterY = (_offset: number) => 0;
let controls: AcademicPositionControl | null = null;
const disconnect = vi.fn();
const key = 'readest:academic-position:position-state';
const text = '0123456789'.repeat(100);

function Harness() {
  const root = useRef<HTMLDivElement>(null);
  const control = useRef<AcademicPositionControl | null>(null);
  // Install deterministic layout before the position hook's layout effect restores storage.
  useLayoutEffect(() => {
    const element = root.current!;
    const paragraph = element.querySelector('p')!;
    characterY = mockReadingLayout(
      element,
      paragraph,
      () => 20,
      () => columns,
      () => beforeHeight,
    ).characterY;
    vi.spyOn(element, 'clientWidth', 'get').mockImplementation(() => columns * 30);
    vi.spyOn(element.querySelector('article')!, 'getBoundingClientRect').mockImplementation(
      () =>
        new DOMRect(
          0,
          60 - element.scrollTop,
          columns * 30,
          beforeHeight + Math.ceil(text.length / columns) * 20,
        ),
    );
  }, []);
  const position = useAcademicPosition(root, 'position-state', control);
  rememberNavigation = position.remember;
  useLayoutEffect(() => {
    controls = control.current;
  });
  return (
    <div ref={root} data-testid='position-root'>
      <article>
        <p data-block-id='long'>{text}</p>
      </article>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  columns = 10;
  beforeHeight = 0;
  disconnect.mockClear();
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: () => void) {
        notifyResize = callback;
      }
      observe() {}
      disconnect = disconnect;
    },
  );
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('academic position state', () => {
  it('keeps the exact saved character through reopen at different widths', () => {
    let view = render(<Harness />);
    let root = screen.getByTestId('position-root');
    root.scrollTop = 400;
    fireEvent.scroll(root);
    view.unmount();
    expect(JSON.parse(localStorage.getItem(key)!).anchor.textOffset).toBe(200);
    for (const nextColumns of [7, 10, 7, 10]) {
      vi.restoreAllMocks();
      columns = nextColumns;
      view = render(<Harness />);
      root = screen.getByTestId('position-root');
      expect(characterY(200)).toBe(60);
      expect(root.scrollTop).toBe(Math.floor(200 / columns) * 20);
      view.unmount();
      expect(JSON.parse(localStorage.getItem(key)!).anchor.textOffset).toBe(200);
    }
  });

  it('preserves the character through repeated font-style wraps and later canvas sizing', () => {
    render(<Harness />);
    const root = screen.getByTestId('position-root');
    root.scrollTop = 400;
    fireEvent.scroll(root);
    for (const nextColumns of [7, 10, 7, 10]) {
      controls!.prepare();
      columns = nextColumns;
      controls!.restore();
      fireEvent.scroll(root);
      expect(characterY(200)).toBe(60);
    }
    beforeHeight = 120; // renderRegion resolves and sizes a preceding image later
    fireEvent.scroll(root); // browser scroll can precede observer delivery
    act(notifyResize);
    expect(root.scrollTop).toBe(520);
    expect(characterY(200)).toBe(60);
    beforeHeight = 160;
    act(notifyResize);
    expect(characterY(200)).toBe(60);
  });

  it('lets explicit reference navigation supersede a pending resize anchor', () => {
    render(<Harness />);
    const root = screen.getByTestId('position-root');
    root.scrollTop = 400;
    fireEvent.scroll(root);
    columns = 7;
    root.scrollTop = 900;
    rememberNavigation();
    act(notifyResize);
    expect(root.scrollTop).toBe(900);
    expect(characterY(315)).toBe(60);
    beforeHeight = 120;
    act(notifyResize);
    expect(root.scrollTop).toBe(1020);
    expect(characterY(315)).toBe(60);
  });

  it('flushes a real scroll before its scroll event and disconnects on close', () => {
    const view = render(<Harness />);
    const root = screen.getByTestId('position-root');
    root.scrollTop = 400;
    fireEvent.scroll(root);
    root.scrollTop = 600; // close occurs before the scroll event is dispatched
    view.unmount();
    const saved = JSON.parse(localStorage.getItem(key)!);
    expect(saved.scrollTop).toBe(600);
    expect(saved.anchor.textOffset).toBe(300);
    expect(disconnect).toHaveBeenCalledOnce();
  });

  it.each([
    '420',
    '{"version":1,"scrollTop":420,"anchor":{"blockId":"missing","viewportY":0,"blockRatio":0}}',
  ])('retains the pixel fallback for old or unavailable anchors: %s', (saved) => {
    localStorage.setItem(key, saved);
    render(<Harness />);
    expect(screen.getByTestId('position-root').scrollTop).toBe(420);
  });

  it('ignores corrupt stored data', () => {
    localStorage.setItem(key, '{broken');
    render(<Harness />);
    expect(screen.getByTestId('position-root').scrollTop).toBe(0);
  });
});
