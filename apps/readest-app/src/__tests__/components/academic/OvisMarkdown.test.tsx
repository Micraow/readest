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
  it.each([
    ['Astronomy: \\(r^2 + h^2\\) is selectable.', 'r2+h2'],
    ['更换标题：\\(\\nu + v\\) 保留原始符号。', 'ν+v'],
  ])('renders standard inline TeX delimiters without content-specific rules: %s', (markdown, expectedMath) => {
    const { container } = render(<OvisMarkdown markdown={markdown} />);
    expect(container.querySelectorAll('math')).toHaveLength(1);
    expect(container.querySelector('math mrow')?.textContent).toBe(expectedMath);
    expect(container.querySelector('math')?.getAttribute('display')).not.toBe('block');
  });
  it.each([
    ['soft-wrapped inline', 'A \\(x +\n\\nu\\) result.', 1, null],
    ['compact comparisons', String.raw`\(x<y>z\)`, 1, null],
    ['bracket product', String.raw`A \([x](y)\) product.`, 1, null],
    ['matrix', String.raw`\(\begin{bmatrix}a&b\\c&d\end{bmatrix}\)`, 1, null],
    ['complete code-like TeX text', '\\(\\text{`label`}+x\\)', 1, null],
    ['blank paragraph', 'A \\(x +\n\n y\\) result.', 0, null],
    ['soft-wrapped code span', 'A \\(x +\n`code \\) literal` after.', 0, 'code'],
    ['soft-wrapped link', 'A \\(x +\n[link](https://example.org/\\)) after.', 0, 'a'],
    ['nested code', 'A \\(x +\n**`code \\) literal`** after.', 0, 'code'],
    ['HTML code', 'A \\(x +\n<code>code \\) literal</code> after.', 0, 'code'],
    ['single-line code', 'A \\(x + `code \\) literal` after.', 0, 'code'],
    ['bare URL', 'A \\(x+\nhttps://example.org/y\\) after.', 0, 'a'],
    ['single-line link', String.raw`A \(x + [link](https://example.org/\)) after.`, 0, 'a'],
    ['enclosed raw HTML code', String.raw`\(x + <code>y</code>\)`, 0, 'code'],
    ['unclosed inline', String.raw`A \(x + y result.`, 0, null],
  ] as const)('applies delimiter precedence to %s', (_name, markdown, count, retainedTag) => {
    const { container } = render(<OvisMarkdown markdown={markdown} />);
    expect(container.querySelectorAll('math')).toHaveLength(count);
    if (retainedTag) expect(container.querySelector(retainedTag)).toBeTruthy();
    if (count) expect(container.querySelector('a, code')).toBeNull();
  });
  it('renders multiline bracket-delimited equations as selectable display math', () => {
    const { container } = render(
      <OvisMarkdown markdown={'Before.\n\n\\[\n\\frac{a}{b} + \\nu \\tag{S.9}\n\\]\n\nAfter.'} />,
    );
    expect(container.querySelectorAll('math[display="block"]')).toHaveLength(1);
    expect(container.textContent).toContain('Before.');
    expect(container.textContent).toContain('After.');
    expect(container.querySelector('img')).toBeNull();
  });
  it('leaves TeX delimiters in code, escaped literals and unclosed delimiters unchanged', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={
          '`\\(code\\)`\n\n```tex\n\\[not math\\]\n```\n\n\\\\(literal\\\\) and an unclosed \\(formula.'
        }
      />,
    );
    expect(container.querySelectorAll('math')).toHaveLength(0);
    expect(container.querySelectorAll('code')[0]?.textContent).toBe('\\(code\\)');
    expect(container.querySelectorAll('code')[1]?.textContent).toContain('\\[not math\\]');
    expect(container.textContent).toContain('\\(literal\\)');
  });
  it('keeps blank lines inside a display equation out of Markdown paragraph splitting', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={'\\[\n\\begin{aligned}\nx &= 1 \\\\\n y &= 2\n\\end{aligned}\n\\]'}
      />,
    );
    expect(container.querySelectorAll('math[display="block"]')).toHaveLength(1);
    expect(container.querySelector('p')).toBeNull();
  });
  it('preserves standard TeX inside raw inline HTML code', () => {
    const markdown = String.raw`Example <code>\(not math\)</code> followed by \(x^2\).`;
    const { container } = render(<OvisMarkdown markdown={markdown} />);
    expect(container.querySelector('code')?.textContent).toBe(String.raw`\(not math\)`);
    expect(container.querySelector('code math')).toBeNull();
    expect(container.querySelectorAll('math')).toHaveLength(1);
  });
  it('preserves both math syntaxes inside HTML code and resumes after the closing tag', () => {
    const { container } = render(
      <OvisMarkdown markdown={String.raw`<code>$x$ \(y\)</code> then $z$ and \(w\).`} />,
    );
    expect(container.querySelector('code')?.textContent).toBe(String.raw`$x$ \(y\)`);
    expect(container.querySelector('code math')).toBeNull();
    expect(container.querySelectorAll('math')).toHaveLength(2);
  });
  it('does not trust links or media requested from TeX', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={
          '\\(\\href{javascript:alert(1)}{run}\\) and \\[\\includegraphics{https://example.org/tracker}\\]'
        }
      />,
    );
    expect(container.querySelector('a, img, iframe, [src]')).toBeNull();
  });
  it('is independent of page labels and renamed content for a held-out formula', () => {
    const expression = '\\sum_{k=1}^{m} \\frac{\\alpha_k}{1+z_k^2}';
    const math = [];
    for (const title of ['# Unseen Section 28', '# Renamed Manual B', '# 新的章节']) {
      const { container, unmount } = render(
        <OvisMarkdown
          markdown={`${title}\n\n- Value \\(${expression}\\).\n\n\\[${expression}\\]`}
        />,
      );
      expect(container.querySelectorAll('math')).toHaveLength(2);
      expect(container.querySelector('li math')).toBeTruthy();
      math.push(Array.from(container.querySelectorAll('math'), (element) => element.outerHTML));
      unmount();
    }
    expect(math[1]).toEqual(math[0]);
    expect(math[2]).toEqual(math[0]);
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
