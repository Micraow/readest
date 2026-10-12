import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OvisMarkdown from '@/components/academic/OvisMarkdown';
afterEach(cleanup);
describe('Ovis content in the existing reader', () => {
  it('keeps selectable prose and renders inline/display math next to digits', () => {
    const { container } = render(
      <OvisMarkdown markdown={'A selectable paragraph with $x^2$ and $\\geq$3.\n\n$$y=1$$'} />,
    );
    expect(container.textContent).toContain('A selectable paragraph');
    expect(container.querySelectorAll('math')).toHaveLength(3);
    expect(container.textContent).not.toContain('$');
  });
  it('preserves ordered-list starts and list items', () => {
    const { container } = render(
      <OvisMarkdown markdown={'4. First step\n5. Second step\n\n- Bullet'} />,
    );
    expect(container.querySelector('ol')?.getAttribute('start')).toBe('4');
    expect(container.querySelectorAll('li')).toHaveLength(3);
  });
  it('preserves escaped currency and code', () => {
    render(<OvisMarkdown markdown={'Cost \\$5 and \\$10. Code `$a$`.'} />);
    expect(screen.getByText(/Cost \$5 and \$10/)).toBeTruthy();
    expect(screen.getByText('$a$', { selector: 'code' })).toBeTruthy();
  });
  it('renders table math without turning the table into an image', () => {
    const { container } = render(
      <OvisMarkdown markdown={'<table><tr><td>$x^2$</td><td>12</td></tr></table>'} />,
    );
    expect(container.querySelector('table math')).toBeTruthy();
    expect(container.querySelector('td')?.textContent).not.toContain('$');
    expect(container.querySelector('img')).toBeNull();
  });
  it('does not execute or load model-supplied active content', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={
          '<img src="https://example.org/tracker"><iframe src="https://example.org"></iframe><script>alert(1)</script><a href="javascript:alert(1)">bad</a>'
        }
      />,
    );
    expect(container.querySelector('img,iframe,script')).toBeNull();
    expect(container.querySelector('[href^="javascript:"]')).toBeNull();
  });
  it('strips legacy table image-loading attributes', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={
          '<table background="https://example.org/t"><tr><td background="https://example.org/c">Cell</td></tr></table>'
        }
      />,
    );
    expect(container.querySelector('[background]')).toBeNull();
    expect(screen.getByText('Cell')).toBeTruthy();
  });
  it('reaches a source figure through its existing block marker', () => {
    const scroll = vi.fn();
    const { container } = render(
      <article>
        <OvisMarkdown markdown={'[Figure 1](#ovis-figure)'} />
        <figure data-block-id='ovis-figure'>
          <button type='button'>Zoom figure</button>
        </figure>
      </article>,
    );
    const target = container.querySelector('figure') as HTMLElement;
    target.scrollIntoView = scroll;
    fireEvent.click(screen.getByRole('link', { name: 'Figure 1' }));
    expect(scroll).toHaveBeenCalledOnce();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Zoom figure' }));
  });
  it('jumps within the reader without changing the browser URL', () => {
    const scroll = vi.fn();
    const { container } = render(
      <article>
        <OvisMarkdown markdown={'A note [1](#note-1).'} />
        <aside id='note-1' tabIndex={-1}>
          Note text
        </aside>
      </article>,
    );
    const target = container.querySelector('#note-1') as HTMLElement;
    target.scrollIntoView = scroll;
    const before = location.hash;
    fireEvent.click(screen.getByRole('link', { name: '1' }));
    expect(scroll).toHaveBeenCalledOnce();
    expect(location.hash).toBe(before);
    expect(document.activeElement).toBe(target);
  });
  it.each(['note 1', '脚注 1'])('decodes encoded fragment links for block ID %s', (id) => {
    const scroll = vi.fn();
    const hash = window.location.hash;
    const { container } = render(
      <article>
        <OvisMarkdown markdown={`[Go to note](#${encodeURIComponent(id)})`} />
        <section id={id} tabIndex={-1}>
          Note destination
        </section>
      </article>,
    );
    const target = container.querySelector('section')!;
    target.scrollIntoView = scroll;
    fireEvent.click(screen.getByRole('link', { name: 'Go to note' }));
    expect(scroll).toHaveBeenCalledOnce();
    expect(document.activeElement).toBe(target);
    expect(window.location.hash).toBe(hash);
  });
});
