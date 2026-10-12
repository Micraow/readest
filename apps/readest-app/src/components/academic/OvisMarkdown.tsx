import { useEffect, useMemo, useRef } from 'react';
import DOMPurify from 'dompurify';
import renderMathInElement from 'katex/contrib/auto-render';
import { parseNoteMarkdown } from '@/app/reader/utils/noteMarkdown';
import styles from './OvisMarkdown.module.css';

/** Ovis prose stays selectable; source images are rendered by the existing PDF session. */
export default function OvisMarkdown({ markdown }: { markdown: string }) {
  const root = useRef<HTMLDivElement>(null);
  const html = useMemo(
    () =>
      DOMPurify.sanitize(parseNoteMarkdown(markdown), {
        USE_PROFILES: { html: true, mathMl: true },
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
      }),
    [markdown],
  );
  useEffect(() => {
    // Markdown's raw HTML table cells bypass its inline-math tokenizer.
    root.current?.querySelectorAll('table').forEach((table) =>
      renderMathInElement(table, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        output: 'mathml',
        trust: false,
        throwOnError: false,
      }),
    );
  }, [html]);
  return (
    <div
      ref={root}
      className={styles['content']}
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
      // Both Markdown and table math are sanitized; no model-supplied media loads.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
