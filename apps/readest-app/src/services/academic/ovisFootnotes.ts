import { ovisMarkdownFragmentTargets, parseOvisMarkdown } from './ovisMarkdown';
import type { ScholarlyDocument } from './types';

/** Presentation-only: leave native, unlinked and ambiguous notes in source order. */
export function linkedOvisFootnoteIds(scholarly: ScholarlyDocument): Set<string> {
  const notes = new Set<string>();
  if (!scholarly.metadata.ovis) return notes;
  const counts = new Map<string, number>();
  const incoming = new Set<string>();
  for (const block of scholarly.blocks) {
    counts.set(block.id, (counts.get(block.id) ?? 0) + 1);
    if (block.type !== 'footnote' && block.markdown !== undefined) {
      for (const id of ovisMarkdownFragmentTargets(block.markdown)) incoming.add(id);
    }
  }
  for (const block of scholarly.blocks) {
    if (
      block.type === 'footnote' &&
      block.markdown !== undefined &&
      counts.get(block.id) === 1 &&
      incoming.has(block.id)
    )
      notes.add(block.id);
  }
  if (!notes.size) return notes;
  // Raw HTML can provide a competing same-article target. Be conservative even
  // if sanitation later removes it; moving a note must never rely on that ID.
  const template = document.createElement('template');
  for (const block of scholarly.blocks) {
    if (block.markdown === undefined) continue;
    template.innerHTML = parseOvisMarkdown(block.markdown);
    for (const target of template.content.querySelectorAll('[id], [data-block-id]')) {
      for (const attribute of ['id', 'data-block-id']) {
        const id = target.getAttribute(attribute);
        if (id) notes.delete(id);
      }
    }
  }
  return notes;
}
