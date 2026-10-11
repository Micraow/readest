import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InlineContent from '../InlineContent';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { InlineRun } from '@/services/academic/types';
import { useThemeStore } from '@/store/themeStore';

vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (value: string) => value }));
vi.mock('@/store/themeStore', async () => {
  const { create } = await import('zustand');
  return { useThemeStore: create(() => ({ isDarkMode: false })) };
});

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
  trimBelow: 104,
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
    useThemeStore.setState({ isDarkMode: false });
    renderRegion.mockReset().mockResolvedValue(undefined);
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(60);
  });

  it('keeps a source glyph and its unspaced operand in one bounded inline word', async () => {
    const sum = { ...source, text: '\u0002' };
    const runs: InlineRun[] = [
      { ...text, text: 'The amount is I = ' },
      sum,
      { ...text, text: 'W', style: { fontStyle: 'italic' } },
      { ...text, text: 'i', style: { fontStyle: 'italic', verticalAlign: 'sub' } },
      { ...text, text: '. The following sentence stays outside.' },
    ];
    const before = JSON.stringify(runs);
    const onZoom = vi.fn();
    const view = render(
      <InlineContent
        runs={runs}
        text=''
        fontSize={16}
        session={session}
        root={root}
        onZoom={onZoom}
      />,
    );
    const button = screen.getByRole('button');
    const word = button.parentElement!;
    expect(word.classList.contains('inline-block')).toBe(true);
    expect(word.classList.contains('max-w-full')).toBe(true);
    expect(word.textContent).toBe('Wi.');
    expect(word.querySelector('sub')?.textContent).toBe('i');
    expect(word.querySelector('sub')?.style.fontStyle).toBe('italic');
    expect(view.container.textContent).toBe(
      'The amount is I = Wi. The following sentence stays outside.',
    );
    expect(word.className).not.toMatch(/nowrap|overflow-hidden/);
    expect(word.style.lineHeight).toBe('');
    expect(JSON.stringify(runs)).toBe(before);
    await waitFor(() => expect(renderRegion).toHaveBeenCalledTimes(1));
    const canvas = button.querySelector('canvas');
    view.rerender(
      <InlineContent
        runs={runs}
        text=''
        fontSize={22}
        session={session}
        root={root}
        onZoom={onZoom}
      />,
    );
    expect(screen.getByRole('button').querySelector('canvas')).toBe(canvas);
    fireEvent.click(button);
    expect(onZoom).toHaveBeenCalledWith(sum.source, sum.trimBelow);
  });

  it('splits text tokens but keeps a source with spaces in its alt text atomic', () => {
    const view = render(
      <InlineContent
        runs={[
          { ...text, text: 'Before (' },
          source,
          { ...text, text: ') after' },
          { ...text, text: ' ' },
          source,
          { ...text, text: 'x next' },
        ]}
        text=''
        fontSize={16}
        session={session}
        root={root}
        onZoom={vi.fn()}
      />,
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]?.parentElement?.textContent).toBe('()');
    expect(buttons[1]?.parentElement?.textContent).toBe('x');
    expect(buttons[0]?.parentElement).not.toBe(buttons[1]?.parentElement);
    expect(buttons[0]?.getAttribute('aria-label')).toContain('a / b');
    expect(view.container.textContent).toBe('Before () after x next');
  });

  it('does not merge whitespace-separated prose or source-only words', () => {
    const view = render(
      <InlineContent
        runs={[text, source, { ...text, text: ' ' }, { ...text, text: 'ordinary prose' }]}
        text=''
        fontSize={16}
        session={session}
        root={root}
        onZoom={vi.fn()}
      />,
    );
    expect(screen.getByRole('button').parentElement).toBe(view.container);
    expect(view.container.textContent).toBe('A selectable sentence  ordinary prose');
    expect(view.container.querySelector('span.inline-block')).toBeNull();
  });

  it('keeps list and reference offsets while grouping an adjacent math word outside the link', () => {
    const runs: InlineRun[] = [{ ...text, text: '12. See [34]' }, source, { ...text, text: 'x.' }];
    const view = render(
      <InlineContent
        runs={runs}
        text=''
        omitListMarker
        fontSize={16}
        session={session}
        root={root}
        onZoom={vi.fn()}
        references={{
          links: [
            { id: 'list', start: 8, end: 12, target: 'reference', kind: 'reference', number: '34' },
          ],
          prefix: 'test',
          onNavigate: vi.fn(),
        }}
      />,
    );
    const anchor = screen.getByRole('link');
    expect(anchor.textContent).toBe('[34]');
    expect(anchor.querySelector('button')).toBeNull();
    expect(screen.getByRole('button').parentElement?.textContent).toBe('x.');
    expect(screen.getByRole('button').closest('a')).toBeNull();
    expect(view.container.textContent).toBe('See [34]x.');
  });

  it('updates only math presentation with the live theme without rendering the PDF again', async () => {
    const onZoom = vi.fn();
    const before = JSON.stringify(source);
    const view = render(
      <InlineContent
        runs={[text, source]}
        text='fallback'
        fontSize={20}
        session={session}
        root={root}
        onZoom={onZoom}
      />,
    );
    await waitFor(() => expect(renderRegion).toHaveBeenCalledTimes(1));
    const canvas = view.container.querySelector('canvas')!;
    const button = screen.getByRole('button');
    const geometry = [button.style.width, button.style.aspectRatio, button.style.verticalAlign];
    expect(canvas.style.mixBlendMode).toBe('multiply');
    expect(canvas.style.filter).toBe('');
    expect(button.classList.contains('bg-white')).toBe(false);
    act(() => useThemeStore.setState({ isDarkMode: true }));
    expect(canvas.style.filter).toBe('invert(100%) hue-rotate(180deg)');
    expect(canvas.style.mixBlendMode).toBe('screen');
    expect(view.container.querySelector('canvas')).toBe(canvas);
    expect([button.style.width, button.style.aspectRatio, button.style.verticalAlign]).toEqual(
      geometry,
    );
    expect(screen.getByText('A selectable sentence').style.filter).toBe('');
    expect(renderRegion).toHaveBeenCalledTimes(1);
    expect(session.analyze).not.toHaveBeenCalled();
    fireEvent.click(button);
    expect(onZoom).toHaveBeenCalledWith(source.source, 104);
    act(() => useThemeStore.setState({ isDarkMode: false }));
    expect(canvas.style.filter).toBe('');
    expect(canvas.style.mixBlendMode).toBe('multiply');
    expect(renderRegion).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(source)).toBe(before);
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
    expect(renderRegion.mock.calls[0]?.[5]).toBe(104);
    const button = screen.getByRole('button');
    expect(button.style.verticalAlign).toBe('-0.6em');
    fireEvent.click(button);
    expect(onZoom).toHaveBeenCalledWith(source.source, 104);
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

  it('applies monospace only to confirmed code runs, including styled scripts', () => {
    const view = render(
      <div style={{ fontFamily: 'Georgia' }}>
        <InlineContent
          runs={[
            text,
            { ...text, text: 'buffer_size', style: { fontFamily: 'monospace' } },
            {
              ...text,
              text: 'n',
              style: {
                fontFamily: 'monospace',
                fontStyle: 'italic',
                fontWeight: 'bold',
                verticalAlign: 'super',
              },
            },
          ]}
          text='fallback'
          fontSize={20}
          session={session}
          root={root}
          onZoom={vi.fn()}
        />
      </div>,
    );
    expect(screen.getByText('A selectable sentence').style.fontFamily).toBe('');
    expect(screen.getByText('buffer_size').style.fontFamily).toBe('monospace');
    expect(view.container.querySelector('sup')?.style.cssText).toContain('font-family: monospace');
    expect(view.container.querySelector('sup')?.style.fontStyle).toBe('italic');
    expect(view.container.querySelector('sup')?.style.fontWeight).toBe('bold');
    expect(view.container.textContent).toBe(`${text.text}buffer_sizen`);
    expect(renderRegion).not.toHaveBeenCalled();
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

  it('links one selectable range across styled runs without nesting a source zoom control', () => {
    const onNavigate = vi.fn();
    const runs: InlineRun[] = [
      { ...text, text: 'See [' },
      { ...text, text: '3', style: { fontWeight: 'bold' } },
      { ...text, text: '4', style: { fontStyle: 'italic' } },
      { ...text, text: ']. ' },
      source,
    ];
    const before = JSON.stringify(runs);
    const link = {
      id: 'citation',
      start: 4,
      end: 8,
      target: 'reference',
      kind: 'reference' as const,
      number: '34',
    };
    const view = render(
      <InlineContent
        runs={runs}
        text='fallback'
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
        references={{ links: [link], prefix: 'test', onNavigate }}
      />,
    );
    const anchor = screen.getByRole('link');
    expect(anchor.textContent).toBe('[34]');
    expect(anchor.querySelector('[style="font-weight: bold;"]')?.textContent).toBe('3');
    expect(anchor.querySelector('[style="font-style: italic;"]')?.textContent).toBe('4');
    expect(anchor.querySelector('button')).toBeNull();
    expect(view.container.textContent).toBe('See [34]. ');
    expect(JSON.stringify(runs)).toBe(before);
    fireEvent.click(anchor);
    expect(onNavigate).toHaveBeenCalledWith(link, anchor);
  });

  it('rejects a supplied link range that overlaps a source zoom button', () => {
    render(
      <InlineContent
        runs={[{ ...text, text: 'See [' }, source, { ...text, text: '].' }]}
        text=''
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
        references={{
          links: [
            {
              id: 'invalid',
              start: 4,
              end: 11,
              target: 'reference',
              kind: 'reference',
              number: '34',
            },
          ],
          prefix: 'test',
          onNavigate: vi.fn(),
        }}
      />,
    );
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByRole('button').closest('a')).toBeNull();
  });

  it('keeps fallback list offsets before stripping the marker at render time', () => {
    render(
      <InlineContent
        text='12. See [34].'
        omitListMarker
        fontSize={20}
        session={session}
        root={root}
        onZoom={vi.fn()}
        references={{
          links: [
            { id: 'list', start: 8, end: 12, target: 'reference', kind: 'reference', number: '34' },
          ],
          prefix: 'test',
          onNavigate: vi.fn(),
        }}
      />,
    );
    expect(screen.getByRole('link').textContent).toBe('[34]');
    expect(document.body.textContent).toBe('See [34].');
  });

  it('retains a readable fallback after a rendering failure and cancels pending work on unmount', async () => {
    useThemeStore.setState({ isDarkMode: true });
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
    const fallback = screen.getByText(source.text);
    expect(fallback.classList.contains('bg-base-100')).toBe(true);
    expect(fallback.classList.contains('bg-white')).toBe(false);
    expect(fallback.style.filter).toBe('');
    await act(async () => {
      await Promise.resolve();
    });
    const signal = renderRegion.mock.calls[0]?.[4];
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });
});
