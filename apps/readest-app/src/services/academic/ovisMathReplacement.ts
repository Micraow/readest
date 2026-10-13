/** The exact sanitized source container replaced by trusted KaTeX rendering. */
export function getOvisMathReplacement(math: Element) {
  const tex = math.querySelector('annotation[encoding="application/x-tex"]')?.textContent;
  if (tex === undefined || tex === null) return;
  const displayMode = math.getAttribute('display') === 'block';
  const inline = math.parentElement!;
  const original =
    displayMode && inline.parentElement?.classList.contains('katex-display')
      ? inline.parentElement
      : inline;
  return { tex, displayMode, original };
}
