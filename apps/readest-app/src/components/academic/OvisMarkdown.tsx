import { useMemo, useRef } from 'react';
import DOMPurify from 'dompurify';
import katex from 'katex';
import renderMathInElement from 'katex/contrib/auto-render';
import { parseOvisMarkdown } from '@/services/academic/ovisMarkdown';
import styles from './OvisMarkdown.module.css';
import mathStyles from './OvisKatex.module.css';

const mathOptions = { output: 'htmlAndMathml', trust: false, throwOnError: false } as const;

/** Ovis prose stays selectable; source images are rendered by the existing PDF session. */
export default function OvisMarkdown({ markdown }: { markdown: string }) {
  const root = useRef<HTMLDivElement>(null);
  const html = useMemo(() => {
    const content = document.createElement('div');
    content.innerHTML = DOMPurify.sanitize(parseOvisMarkdown(markdown), {
      USE_PROFILES: { html: true, mathMl: true },
      ADD_TAGS: ['semantics', 'annotation'],
      FORBID_TAGS: [
        'img',
        'picture',
        'source',
        'audio',
        'video',
        'iframe',
        'object',
        'embed',
        'style',
        'form',
        'input',
        'button',
        'textarea',
        'select',
      ],
      FORBID_ATTR: ['style', 'src', 'srcset', 'background'],
    });
    // Native MathML does not reliably distinguish mathematical alphabets.
    // Only KaTeX may generate layout styles, after all model HTML is sanitized.
    content.querySelectorAll('.katex > math').forEach((math) => {
      const tex = math.querySelector('annotation[encoding="application/x-tex"]')?.textContent;
      if (tex === undefined || tex === null) return;
      const displayMode = math.getAttribute('display') === 'block';
      const inline = math.parentElement!;
      const original =
        displayMode && inline.parentElement?.classList.contains('katex-display')
          ? inline.parentElement
          : inline;
      const rendered = document.createElement('span');
      katex.render(tex, rendered, { ...mathOptions, displayMode });
      original.replaceWith(...rendered.childNodes);
    });
    // Markdown's raw HTML table cells bypass its inline-math tokenizer.
    content.querySelectorAll('table').forEach((table) =>
      renderMathInElement(table, {
        ...mathOptions,
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        ignoredClasses: ['katex', 'katex-display', 'katex-error'],
      }),
    );
    // Keep the intrinsic equation and its number in separate columns. KaTeX's
    // absolute tag placement overlaps long equations in a narrow reader.
    content.querySelectorAll('.katex-display > .katex > .katex-html').forEach((math) => {
      const tag = math.querySelector(':scope > .tag');
      if (!tag) return;
      const equation = document.createElement('span');
      equation.className = styles['equation']!;
      for (const node of Array.from(math.childNodes)) {
        if (node !== tag) equation.appendChild(node);
      }
      math.classList.add(styles['tagged']!);
      math.prepend(equation);
    });
    return content.innerHTML;
  }, [markdown]);
  return (
    <div
      ref={root}
      className={`${styles['content']} ${mathStyles['math']}`}
      onClick={(event) => {
        const anchor = event.target instanceof Element ? event.target.closest('a') : null;
        const href = anchor?.getAttribute('href');
        if (!href?.startsWith('#')) return;
        event.preventDefault();
        let id: string;
        try {
          id = decodeURIComponent(href.slice(1));
        } catch {
          return;
        }
        const target = root.current
          ?.closest('article')
          ?.querySelector<HTMLElement>(
            `[id="${CSS.escape(id)}"], [data-block-id="${CSS.escape(id)}"]`,
          );
        target?.scrollIntoView({ block: 'start' });
        (target?.querySelector<HTMLElement>('button') ?? target)?.focus({ preventScroll: true });
      }}
      // Model HTML is sanitized before trusted, non-networked math rendering.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
