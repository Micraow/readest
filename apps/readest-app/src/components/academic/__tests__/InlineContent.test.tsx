import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InlineContent from '../InlineContent';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { InlineRun } from '@/services/academic/types';

vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (value: string) => value }));

const text: InlineRun = {
  kind: 'text',
  text: 'A selectable sentence ',
  source: { page: 1, boxes: [], itemIndices: [0] },
};
const source: InlineRun = {
  kind: 'source',
  text: 'a / b',
  fontSize: 10,
  baseline: 100,
  source: { page: 1, boxes: [{ x: 10, y: 90, width: 30, height: 16 }], itemIndices: [1, 2] },
};
const renderRegion = vi.fn<AcademicPdfSession['renderRegion']>();
const session: AcademicPdfSession = {
  renderRegion,
  renderPage: vi.fn(),
  analyze: vi.fn(),
  destroy: vi.fn(),
};
const root = { current: null };

describe('InlineContent', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });
  beforeEach(() => {
    renderRegion.mockReset().mockResolvedValue(undefined);
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(60);
  });

  it('keeps ordinary text selectable and renders a bounded local PDF crop with zoom', async () => {
    const onZoom = vi.fn();
    render(
      <InlineContent
        runs={[text, source]}
        text='fallback'
        fontSize={20}
        session={session}
        root={root}
        onZoom={onZoom}
      />,
    );
    expect(screen.getByText('A selectable sentence')).toBeTruthy();
    await waitFor(() => expect(renderRegion).toHaveBeenCalled());
    expect(renderRegion.mock.calls[0]?.slice(0, 2)).toEqual([1, source.source.boxes[0]]);
    const button = screen.getByRole('button');
    expect(button.style.verticalAlign).toBe('-0.6em');
    fireEvent.click(button);
    expect(onZoom).toHaveBeenCalledWith(source.source);
  });

  it('renders text style and falls back to the original text for old blocks', () => {
    const view = render(
      <InlineContent
        runs={[{ ...text, style: { fontStyle: 'italic', verticalAlign: 'sub' } }]}
        text='fallback'
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
      />,
    );
    expect(view.container.querySelector('sub')?.textContent).toBe(text.text);
    view.rerender(
      <InlineContent
        text='fallback'
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
      />,
    );
    expect(view.container.textContent).toBe('fallback');
  });

  it('omits a list marker split across runs without changing the saved runs', () => {
    const runs: InlineRun[] = [
      { ...text, text: '12.' },
      { ...text, text: ' ' },
      { ...text, text: 'A list item' },
    ];
    const view = render(
      <InlineContent
        runs={runs}
        text='A list item'
        omitListMarker
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
      />,
    );
    expect(view.container.textContent).toBe('A list item');
    expect(runs[0]?.text).toBe('12.');
  });

  it('retains a readable fallback after a rendering failure and cancels pending work on unmount', async () => {
    renderRegion.mockRejectedValueOnce(new Error('decode failed'));
    const view = render(
      <InlineContent
        runs={[source]}
        text='fallback'
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
      />,
    );
    await waitFor(() => expect(screen.getByRole('button').textContent).toContain(source.text));
    await act(async () => {
      await Promise.resolve();
    });
    const signal = renderRegion.mock.calls[0]?.[4];
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });
});
