import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { StrictMode } from 'react';
import { cleanup, render } from '@testing-library/react';
import postcss from 'postcss';
import { afterEach, describe, expect, it } from 'vitest';
import OvisMarkdown from '@/components/academic/OvisMarkdown';
import { parseNoteMarkdown } from '@/app/reader/utils/noteMarkdown';

afterEach(cleanup);

describe('Ovis mathematical typography', () => {
  const expression = String.raw`\mathcal{Q} + \mathbf{v} + \mathbb{R} + \mathfrak{g} + v`;
  it.each([
    ['inline dollar', `$${expression}$`],
    ['inline bracket', `\\(${expression}\\)`],
    ['multiline display', `\\[\n${expression}\n\\]`],
    ['raw HTML table', `<table><tr><td>\\(${expression}\\)</td></tr></table>`],
  ])('renders %s with one font-backed visual layer and accessible original TeX', (_name, markdown) => {
    const { container } = render(<OvisMarkdown markdown={markdown} />);
    expect(container.querySelectorAll('.katex-html')).toHaveLength(1);
    expect(container.querySelectorAll('.katex-mathml math')).toHaveLength(1);
    expect(container.querySelector('.katex-html')?.getAttribute('aria-hidden')).toBe('true');
    expect(container.querySelector('.katex-mathml')?.hasAttribute('aria-hidden')).toBe(false);
    expect(container.querySelector('annotation')?.textContent).toBe(expression);
    for (const font of ['mathcal', 'mathbf', 'mathbb', 'mathfrak', 'mathnormal']) {
      expect(container.querySelector(`.katex-html .${font}`)).toBeTruthy();
    }
  });

  it('keeps trusted layout styles while stripping model styles and active content', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={String.raw`<p id="model" style="position:fixed;background:url(https://example.org/pixel)">Prose</p>

\[\frac{\sqrt{x}}{1+z}\]

<table style="background:red"><tr><td style="position:fixed">$\frac{a}{b}$</td></tr></table>

<span class="katex"><span style="background:url(https://example.org/fake)">Fake math</span></span>
<img src="https://example.org/image"><svg><script>alert(1)</script></svg>`}
      />,
    );
    expect(container.querySelector('#model')?.hasAttribute('style')).toBe(false);
    expect(container.querySelector('table, td')?.hasAttribute('style')).toBe(false);
    expect(container.querySelectorAll('.katex-html .frac-line[style]')).toHaveLength(2);
    expect(container.querySelector('.katex-html svg path')).toBeTruthy();
    expect(
      container.querySelector('img, script, [src], [style*="url("], [style*="fixed"]'),
    ).toBeNull();
    for (const styled of container.querySelectorAll('[style]')) {
      expect(styled.closest('.katex-html')).toBeTruthy();
    }
  });

  it.each([
    [
      'prose',
      String.raw`$\href{https://example.org}{link}+\htmlStyle{position:fixed}{x}+\includegraphics{https://example.org/pixel}$`,
    ],
    [
      'table',
      String.raw`<table><tr><td>$\href{https://example.org}{link}+\htmlStyle{position:fixed}{x}+\includegraphics{https://example.org/pixel}$</td></tr></table>`,
    ],
  ])('does not activate untrusted TeX in %s', (_name, markdown) => {
    const { container } = render(<OvisMarkdown markdown={markdown} />);
    expect(container.querySelector('.katex-html')).toBeTruthy();
    expect(container.querySelector('a, img, iframe, [src], [style*="fixed"]')).toBeNull();
  });

  it('keeps malformed TeX readable without inserting source markup', () => {
    const { container } = render(
      <OvisMarkdown markdown={String.raw`\(\frac{<img src=x>}{\) title.`} />,
    );
    expect(container.querySelector('.katex-error')?.textContent).toBe(
      String.raw`\frac{<img src=x>}{`,
    );
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).toContain('title.');
  });

  it('preserves code and link destinations while rendering each table formula once', () => {
    const { container } = render(
      <OvisMarkdown
        markdown={
          '| Formula |\n| --- |\n| $\\text{cost \\$5 and \\$10}+\\mathcal{Q}$ |\n\n' +
          String.raw`<table><tr><td><code>\(code\) $x$</code><a href="https://example.org/?x=$x$">\(\mathcal{Q}\)</a></td></tr></table>`
        }
      />,
    );
    expect(container.querySelectorAll('.katex-html')).toHaveLength(2);
    expect(container.querySelectorAll('annotation')).toHaveLength(2);
    expect(container.querySelector('code')?.textContent).toBe(String.raw`\(code\) $x$`);
    expect(container.querySelector('a')?.getAttribute('href')).toBe('https://example.org/?x=$x$');
    expect(container.querySelector('a annotation')?.textContent).toBe(String.raw`\mathcal{Q}`);
    expect(container.querySelector('code math')).toBeNull();
  });

  it('replaces all visual and semantic math on rerender and unmount, including strict mode', () => {
    const { container, rerender, unmount } = render(
      <StrictMode>
        <OvisMarkdown markdown={`$${expression}$`} />
      </StrictMode>,
    );
    expect(container.querySelectorAll('.katex-html')).toHaveLength(1);
    rerender(
      <StrictMode>
        <OvisMarkdown markdown={'<table><tr><td>$\\mathbb{Z}$</td></tr></table>'} />
      </StrictMode>,
    );
    expect(container.querySelectorAll('.katex-html')).toHaveLength(1);
    expect(container.querySelectorAll('annotation')).toHaveLength(1);
    expect(container.querySelector('annotation')?.textContent).toBe(String.raw`\mathbb{Z}`);
    expect(container.querySelector('.mathcal')).toBeNull();
    rerender(
      <StrictMode>
        <OvisMarkdown markdown={'<table><tr><td>$\\mathbb{Z}$</td></tr></table>'} />
      </StrictMode>,
    );
    expect(container.querySelectorAll('.katex-html')).toHaveLength(1);
    expect(container.querySelector('annotation')?.textContent).toBe(String.raw`\mathbb{Z}`);
    rerender(
      <StrictMode>
        <OvisMarkdown markdown='Only prose.' />
      </StrictMode>,
    );
    expect(container.querySelector('.katex, math, annotation')).toBeNull();
    unmount();
    expect(container.innerHTML).toBe('');
  });

  it('does not change the shared note parser or add a second layer to notes', () => {
    const before = parseNoteMarkdown(`$${expression}$`);
    render(<OvisMarkdown markdown={`$${expression}$`} />);
    expect(parseNoteMarkdown(`$${expression}$`)).toBe(before);
    expect(before).not.toContain('katex-html');
    expect(before).not.toContain('katex-mathml');
  });

  it('scopes the official stylesheet without changing its rules and resolves only local fonts', () => {
    const require = createRequire(import.meta.url);
    const official = readFileSync(require.resolve('katex/dist/katex.css'), 'utf8');
    const scoped = readFileSync('src/components/academic/OvisKatex.module.css', 'utf8');
    expect(scoped).toContain(createHash('sha256').update(official).digest('hex'));
    expect(scoped).toContain('Copyright (c) 2013-2020 Khan Academy');
    const normalized = postcss.parse(scoped);
    normalized.walkComments((comment) => {
      comment.remove();
    });
    normalized.walkRules((rule) => {
      expect(rule.selectors.every((selector) => selector.startsWith('.math :global('))).toBe(true);
      rule.selectors = rule.selectors.map((selector) =>
        selector.slice('.math :global('.length, -1),
      );
    });
    normalized.walkDecls('src', (decl) => {
      expect(decl.value).not.toMatch(/https?:|data:/);
      for (const match of decl.value.matchAll(/url\(([^)]+)\)/g)) {
        const file = match[1]!.replace(/['"]/g, '');
        expect(() => require.resolve(file)).not.toThrow();
      }
      decl.value = decl.value.replaceAll('katex/dist/fonts/', 'fonts/');
    });
    const original = postcss.parse(official);
    original.walkComments((comment) => {
      comment.remove();
    });
    const compact = (css: string) => css.replace(/\s+/g, '').replaceAll('"', "'");
    expect(compact(normalized.toString())).toBe(compact(original.toString()));
  });
});
