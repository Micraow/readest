import katex from 'katex';
import { Lexer, Marked, type Token, type TokenizerAndRendererExtension } from 'marked';
import markedKatex from 'marked-katex-extension';

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
