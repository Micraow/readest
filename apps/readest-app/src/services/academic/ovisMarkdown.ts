import katex from 'katex';
import { Lexer, Marked, Renderer, type Token, type TokenizerAndRendererExtension } from 'marked';
import markedKatex from 'marked-katex-extension';
import { sanitizeOvisMarkdown } from './ovisMarkdownSanitizer';
import { getOvisMathReplacement } from './ovisMathReplacement';

const mathOptions = { output: 'mathml', trust: false, throwOnError: false } as const;
// Complete TeX owns link/code-like text inside it. A closing delimiter inside
// a later Markdown token cannot finish an earlier formula. Raw HTML code stays
// literal even when it appears between math delimiters.
function crossesMarkdownBoundary(tokens: Token[], source: string, end: number): boolean {
  let offset = 0;
  for (const token of tokens) {
    const start = source.indexOf(token.raw, offset);
    if (start >= end) break;
    offset = start + token.raw.length;
    if (token.type === 'html' && 'inRawBlock' in token && token.inRawBlock) return true;
    if (['codespan', 'link', 'image', 'html'].includes(token.type) && offset > end - 2) return true;
    if (
      'tokens' in token &&
      token.tokens &&
      crossesMarkdownBoundary(token.tokens, token.raw, end - start)
    )
      return true;
  }
  return false;
}

// Tokenize before Markdown consumes the backslash escapes. Code spans/fences are
// still owned by Markdown, so their examples are never converted into equations.
const bracketMath: TokenizerAndRendererExtension = {
  name: 'ovisBracketMath',
  level: 'inline',
  start: (source) => source.search(/\\[([]/),
  tokenizer(source) {
    if (this.lexer.state.inRawBlock) {
      // Keep raw-code text ahead of both math extensions and Markdown escapes.
      // Leave tags to Markdown so </code> restores normal inline parsing.
      const raw = /^[^<]+/.exec(source)?.[0];
      return raw ? { type: 'text', raw, text: raw } : undefined;
    }
    const match =
      /^\\\(((?:\\[^\n]|(?!\n[ \t]*\n)[^\\])*?)\\\)|^\\\[((?:\\[\s\S]|[^\\])*?)\\\]/.exec(source);
    if (!match) return;
    if (
      match[1] !== undefined &&
      crossesMarkdownBoundary(Lexer.lexInline(source), source, match[0].length)
    )
      return;
    return {
      type: 'ovisBracketMath',
      raw: match[0],
      text: (match[1] ?? match[2] ?? '').trim(),
      displayMode: match[2] !== undefined,
    };
  },
  renderer(token) {
    return katex.renderToString(token['text'], {
      ...mathOptions,
      displayMode: token['displayMode'],
    });
  },
};

const displayMath: TokenizerAndRendererExtension = {
  name: 'ovisDisplayMath',
  level: 'block',
  tokenizer(source) {
    const match = /^ {0,3}\\\[((?:\\[\s\S]|[^\\])*?)\\\][ \t]*(?:\n|$)/.exec(source);
    if (!match) return;
    return {
      type: 'ovisBracketMath',
      raw: match[0],
      text: (match[1] ?? '').trim(),
      displayMode: true,
    };
  },
};

const ovisMarkdown = new Marked({ gfm: true }).use(
  markedKatex({ ...mathOptions, nonStandard: true }),
  { extensions: [bracketMath, displayMath] },
);

/** OvisMarkdown sanitizes this result before inserting it into the reader. */
export const parseOvisMarkdown = (markdown: string) =>
  ovisMarkdown.parse(markdown, { async: false });

/** Match the reader's fragment semantics, using only surviving Markdown links. */
export function ovisMarkdownFragmentTargets(markdown: string): string[] {
  if (typeof document === 'undefined') return [];
  const source = markdown.toLowerCase();
  const prefix = 'data-readest-markdown-link';
  let marker = prefix;
  for (let suffix = 1; source.includes(marker); suffix++) marker = `${prefix}-${suffix}`;
  // HTML attribute names cannot contain decoded entities. A name absent from
  // the source (case-insensitively) cannot be supplied by a raw HTML anchor.
  const renderer = new Renderer();
  const renderLink = renderer.link.bind(renderer);
  renderer.link = (token) => renderLink(token).replace(/^<a /, `<a ${marker}="" `);
  const template = document.createElement('template');
  template.innerHTML = sanitizeOvisMarkdown(
    ovisMarkdown.parse(markdown, { async: false, renderer }),
  );
  // These containers are subsequently replaced in the real reader. Their
  // original anchors do not survive, even when they passed sanitation.
  for (const math of template.content.querySelectorAll('.katex > math')) {
    getOvisMathReplacement(math)?.original.remove();
  }
  const targets: string[] = [];
  for (const anchor of template.content.querySelectorAll(`a[${marker}]`)) {
    if (anchor.namespaceURI !== 'http://www.w3.org/1999/xhtml') continue;
    const href = anchor.getAttribute('href');
    if (!href?.startsWith('#')) continue;
    try {
      const id = decodeURIComponent(href.slice(1));
      if (id) targets.push(id);
    } catch {
      // The existing reader also ignores malformed percent escapes.
    }
  }
  return targets;
}
