import { cleanup, render } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import OvisMarkdown from '@/components/academic/OvisMarkdown';

afterEach(cleanup);

const equations = [
  ['short', String.raw`\mathcal{Q}(s)=\frac{1}{1+s^2}`, 'A'],
  [
    'long multi-base',
    String.raw`\mathcal{Q}(s)=\sum_{k=1}^{n}\frac{\alpha_k s^k}{1+\beta_k^2}+\mathbb{R}+\mathfrak{g}(s)+\mathbf{v}+\int_0^1 t^2\,dt`,
    'Supplementary relation with an intentionally long label',
  ],
  [
    'aligned',
    String.raw`\begin{aligned}q(s)&=\sum_{k=1}^{n}\alpha_k s^k\\r(s)&=\frac{\mathcal{H}(s)}{1+\beta^2}\end{aligned}`,
    'Appendix B.27',
  ],
  [
    'matrix',
    String.raw`\begin{pmatrix}\alpha&\beta\\\gamma&\delta\end{pmatrix}\begin{pmatrix}x\\y\end{pmatrix}=\begin{pmatrix}u\\v\end{pmatrix}`,
    'Matrix identity with a longer label',
  ],
] as const;

describe('Ovis display equation numbering', () => {
  for (const width of [350, 900]) {
    for (const fontSize of [14, 28]) {
      for (const [name, expression, label] of equations) {
        it(`reserves the measured ${name} label at ${width}px / ${fontSize}px`, async () => {
          const tex = `${expression}\\tag{${label}}`;
          const { container } = render(
            <div style={{ width, fontSize }}>
              <OvisMarkdown markdown={`\\[${tex}\\]`} />
            </div>,
          );
          await document.fonts.ready;
          const display = container.querySelector<HTMLElement>('.katex-display')!;
          const visual = display.querySelector<HTMLElement>('.katex-html')!;
          const tag = visual.querySelector<HTMLElement>(':scope > .tag')!;
          const bases = Array.from(visual.querySelectorAll<HTMLElement>('.base'));
          expect(bases.length).toBeGreaterThan(0);
          expect(display.querySelectorAll('.katex-html')).toHaveLength(1);
          expect(display.querySelectorAll('math')).toHaveLength(1);
          expect(display.querySelector('annotation')?.textContent).toBe(tex);

          for (const scrollLeft of [0, display.scrollWidth]) {
            display.scrollLeft = scrollLeft;
            const edge = display.getBoundingClientRect();
            const right = Math.max(...bases.map((base) => base.getBoundingClientRect().right));
            const left = Math.min(...bases.map((base) => base.getBoundingClientRect().left));
            const number = tag.getBoundingClientRect();
            expect(
              number.left - right,
              'the equation and its number must not overlap',
            ).toBeGreaterThan(1);
            if (scrollLeft === 0) {
              expect(left, 'the first symbol must be reachable').toBeGreaterThanOrEqual(
                edge.left - 1,
              );
            } else {
              expect(number.right, 'the entire number must be reachable').toBeLessThanOrEqual(
                edge.right + 1,
              );
            }
          }

          const selection = window.getSelection()!;
          const range = document.createRange();
          range.selectNodeContents(display);
          selection.removeAllRanges();
          selection.addRange(range);
          const copied = selection.toString().replace(/\s+/g, ' ');
          expect(copied).not.toMatch(/\\(?:tag|mathcal|frac|begin)/);
          expect(copied.split(label)).toHaveLength(2);
          selection.removeAllRanges();
        });
      }
    }
  }
});
