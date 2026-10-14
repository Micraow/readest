import type { OvisBundle } from './ovis';
import type { PageAnalysis, Rect, ScholarlyBlock, ScholarlyDocument, SourceSpan } from './types';

export interface ProseFusionDecision {
  page: number;
  ovisBlockId: string;
  action: 'native' | 'ovis';
  reason: string;
  nativeBlockId?: string;
  original?: string;
  replacement?: string;
  source?: SourceSpan[];
}

/** Experimental preview only: deliberately not an importable Ovis bundle or a cache write. */
export interface NativeProseFusionPreview {
  policyVersion: 'native-prose-preview-1';
  pdfSha256: string;
  nativeParserVersion: string;
  pages: OvisBundle['pages'];
  decisions: ProseFusionDecision[];
}

// Do not use NFKC: it can flatten mathematical superscripts into ordinary digits.
const ligatures: Record<string, string> = {
  ﬀ: 'ff',
  ﬁ: 'fi',
  ﬂ: 'fl',
  ﬃ: 'ffi',
  ﬄ: 'ffl',
  ﬅ: 'st',
  ﬆ: 'st',
};
const normalized = (text: string) =>
  text
    .replace(/[ﬀ-ﬆ]/g, (char) => ligatures[char]!)
    .replace(/\s+/g, ' ')
    .trim();

function plainProse(text: string): boolean {
  const sourceText = text.replace(/\r\n?/g, '\n');
  const normalizedText = normalized(sourceText);
  const withoutCitations = normalizedText.replace(/\[\d+(?:\s*[-–,]\s*\d+)*\]/g, '');
  return (
    normalizedText.split(' ').length >= 30 &&
    normalizedText.length <= 12000 &&
    !/\n[ \t]*\n| {2,}\n|^(?: {4}| {0,3}\t)/m.test(sourceText) &&
    !/\]\s*\(/u.test(normalizedText) &&
    !/[\\$<>|`*_{}\[\]=^~]/u.test(withoutCitations) &&
    !/^[#>+-]|^\d+[.)]\s/m.test(text) &&
    // Start with Latin prose only. Unsupported scripts and symbol encodings fail closed.
    !/[^\x20-\x7e\s’‘“”–—]/u.test(normalizedText)
  );
}

const numberWord =
  /^(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|quadrillion|quintillion|sextillion|septillion|octillion|nonillion|decillion|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|thirtieth|fortieth|fiftieth|sixtieth|seventieth|eightieth|ninetieth|hundredth|thousandth|millionth|billionth|trillionth|quadrillionth|quintillionth|halves|quarter|dozen|score)s?$/;

/** Exact six-word anchors; only a tiny number of interior lowercase i/l confusions. */
function aligned(ovis: string, native: string): boolean {
  const a = normalized(ovis).split(' '),
    b = normalized(native).split(' ');
  if (a.length !== b.length || a.length < 30) return false;
  let edits = 0;
  for (let i = 0; i < a.length; i++) {
    if (a[i] === b[i]) continue;
    const left = a[i]!,
      right = b[i]!;
    if (
      i < 6 ||
      i >= a.length - 6 ||
      !/^[a-z]{5,}$/.test(left) ||
      !/^[a-z]{5,}$/.test(right) ||
      left.length !== right.length ||
      numberWord.test(left) ||
      numberWord.test(right)
    )
      return false;
    const differences = [...left].filter((letter, j) => letter !== right[j]);
    if (
      [...left].some(
        (letter, j) =>
          letter !== right[j] &&
          !((letter === 'i' && right[j] === 'l') || (letter === 'l' && right[j] === 'i')),
      )
    )
      return false;
    if (differences.length !== 1 || ++edits > Math.min(2, Math.max(1, Math.floor(a.length / 50))))
      return false;
  }
  return true;
}

const contained = (inner: Rect, outer: Rect) =>
  inner.width > 0 &&
  inner.height > 0 &&
  inner.x >= outer.x - 1 &&
  inner.y >= outer.y - 1 &&
  inner.x + inner.width <= outer.x + outer.width + 1 &&
  inner.y + inner.height <= outer.y + outer.height + 1;

function safeNative(block: ScholarlyBlock, page: PageAnalysis): boolean {
  if (
    block.type !== 'paragraph' ||
    block.confidence < 0.85 ||
    block.fallbackReason ||
    !plainProse(block.text) ||
    block.source.length !== 1 ||
    page.unsupportedReason ||
    !block.inlineRuns?.length ||
    block.inlineRuns.some(
      (run) => run.kind !== 'text' || (run.style && Object.keys(run.style).length > 0),
    )
  )
    return false;
  if (normalized(block.inlineRuns.map((run) => run.text).join('')) !== normalized(block.text))
    return false;
  const source = block.source[0]!;
  if (source.page !== page.page || !source.boxes.length || !source.itemIndices.length) return false;
  const columns = page.columns.filter(
    (column) => column.confidence >= 0.8 && source.boxes.every((box) => contained(box, column.box)),
  );
  if (columns.length !== 1) return false;
  const items = new Map(page.items.map((item) => [item.index, item]));
  return source.itemIndices.every((index) => {
    const item = items.get(index);
    return (
      item &&
      !item.fontMath &&
      !item.fontMonospace &&
      Math.abs(item.angle) < 0.02 &&
      !/[\uFFFD\uE000-\uF8FF\u0000-\u0008]/u.test(item.text)
    );
  });
}

/**
 * Keep Ovis order and complex blocks verbatim. Proposals require unique bidirectional
 * matches, a single native column, monotonic order, and identical PDF identity.
 * These gates are heuristics, not a calibrated probability or proof of OCR accuracy.
 * The caller must inspect the preview; no production reader imports this module.
 */
export function previewNativeProseFusion(
  bundle: OvisBundle,
  native: ScholarlyDocument,
): NativeProseFusionPreview {
  if (bundle.pdfSha256 !== native.fingerprint || bundle.pageCount !== native.pageCount)
    throw new Error('Native prose and Ovis output must belong to the same PDF');
  const pages = structuredClone(bundle.pages);
  const decisions: ProseFusionDecision[] = [];
  const order = new Map(native.readingOrder.map((id, index) => [id, index]));
  for (const page of pages) {
    const nativePage = native.pages.find((candidate) => candidate.page === page.page);
    if (
      !nativePage ||
      Math.abs(nativePage.width - page.width) > 0.01 ||
      Math.abs(nativePage.height - page.height) > 0.01 ||
      nativePage.rotation !== 0
    )
      throw new Error('Native and Ovis page geometry must agree');
    const candidates = native.blocks.filter(
      (block) => block.source.some((source) => source.page === page.page) && block.text.trim(),
    );
    const matches = page.blocks.map((block) =>
      block.kind === 'markdown' && plainProse(block.markdown)
        ? candidates.filter((candidate) => aligned(block.markdown, candidate.text))
        : [],
    );
    const proposed = matches.map((matches) => (matches.length === 1 ? matches[0] : undefined));
    // Ambiguous Ovis blocks still consume possible matches. Counting only unique
    // proposals would let one accepted paragraph duplicate a retained ambiguous one.
    const uses = new Map<string, number>();
    for (const group of matches)
      for (const candidate of group) uses.set(candidate.id, (uses.get(candidate.id) ?? 0) + 1);
    const reused = new Set([...uses].filter(([, count]) => count > 1).map(([id]) => id));
    const inversions = new Set<string>();
    for (let i = 0; i < proposed.length; i++) {
      const current = proposed[i];
      if (!current) continue;
      for (let j = i + 1; j < proposed.length; j++) {
        const next = proposed[j];
        if (next && (order.get(current.id) ?? Infinity) >= (order.get(next.id) ?? -1)) {
          inversions.add(current.id);
          inversions.add(next.id);
        }
      }
    }
    for (const [index, block] of page.blocks.entries()) {
      const decision: ProseFusionDecision = {
        page: page.page,
        ovisBlockId: block.id,
        action: 'ovis',
        reason: 'complex-or-short-content',
      };
      decisions.push(decision);
      if (block.kind !== 'markdown' || !plainProse(block.markdown)) continue;
      const candidate = proposed[index];
      if (!candidate) {
        decision.reason = matches[index]!.length ? 'ambiguous-match' : 'no-safe-alignment';
        continue;
      }
      if (reused.has(candidate.id)) {
        decision.reason = 'reused-native-paragraph';
        continue;
      }
      if (!order.has(candidate.id) || inversions.has(candidate.id)) {
        decision.reason = 'reading-order-conflict';
        continue;
      }
      if (!safeNative(candidate, nativePage)) {
        decision.reason = 'unsafe-native-evidence';
        continue;
      }
      decision.action = 'native';
      decision.reason = 'unique-conservative-alignment';
      decision.nativeBlockId = candidate.id;
      decision.source = structuredClone(candidate.source);
      decision.original = block.markdown;
      decision.replacement = normalized(candidate.text);
      block.markdown = decision.replacement;
    }
  }
  return {
    policyVersion: 'native-prose-preview-1',
    pdfSha256: bundle.pdfSha256,
    nativeParserVersion: native.parserVersion,
    pages,
    decisions,
  };
}
