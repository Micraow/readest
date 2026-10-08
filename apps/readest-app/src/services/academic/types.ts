/** Scale-1 PDF.js rotated viewport coordinates, in points, top-left origin. */
export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}
export interface PdfTextItem {
  index: number;
  text: string;
  box: Rect;
  baseline: number;
  fontSize: number;
  fontName: string;
  fontFamily: string;
  /** Confirmed fixed-width text face; the generic PDF fallback can also describe symbol subsets. */
  fontMonospace?: true;
  /** Confirmed symbol/extension face; letter codes may represent mathematical operators. */
  fontMath?: true;
  fontStyle?: 'italic';
  fontWeight?: 'bold';
  angle: number;
  hasEOL: boolean;
}
export interface PdfGraphic {
  box: Rect;
  kind: 'form' | 'image' | 'path' | 'rule';
}
export interface PageGeometry {
  page: number;
  width: number;
  height: number;
  rotation: number;
  items: PdfTextItem[];
  graphics: PdfGraphic[];
  tagged: boolean;
}
export interface SourceSpan {
  page: number;
  boxes: Rect[];
  itemIndices: number[];
}
export interface InlineTextStyle {
  /** Proportional prose inherits the user's reading font. */
  fontFamily?: 'monospace';
  fontStyle?: 'italic';
  fontWeight?: 'bold';
  verticalAlign?: 'sub' | 'super';
}
/** Text remains selectable; ambiguous notation keeps its exact local PDF appearance. */
export type InlineRun =
  | { kind: 'text'; text: string; source: SourceSpan; style?: InlineTextStyle }
  | {
      kind: 'source';
      text: string;
      source: SourceSpan;
      /** Surrounding prose size and absolute baseline, in scale-one PDF points. */
      fontSize: number;
      baseline: number;
      /** Lowest owned glyph baseline when a following source line touches the crop edge. */
      trimBelow?: number;
    };
export interface FontStatistics {
  median: number;
  min: number;
  max: number;
  names: string[];
}
export interface LayoutLine {
  id: string;
  text: string;
  box: Rect;
  itemIndices: number[];
  fontSize: number;
}
export interface LayoutColumn {
  box: Rect;
  confidence: number;
}
export type VisualRole = 'figure' | 'table' | 'algorithm' | 'equation' | 'unknown';
export interface VisualCaption {
  role: 'figure' | 'table';
  label: string;
  text: string;
  source: SourceSpan;
  inlineRuns?: InlineRun[];
}
export interface ScholarlyBlock {
  id: string;
  type: 'heading' | 'paragraph' | 'list' | 'reference' | 'footnote' | 'visual-region';
  text: string;
  source: SourceSpan[];
  order: number;
  confidence: number;
  fontStats: FontStatistics;
  level?: number;
  listItems?: string[];
  inlineRuns?: InlineRun[];
  listInlineRuns?: InlineRun[][];
  role?: VisualRole;
  /** A caption-free preview; the complete source remains available for zoom. */
  previewBox?: Rect;
  /** Inline-only render hint, also carried into its temporary zoom block. */
  trimBelow?: number;
  /** Semantic caption associations; source ownership remains in the block source. */
  captions?: VisualCaption[];
  /** Why a region/page was preserved visually instead of reordered. */
  fallbackReason?: string;
}
export interface PageAnalysis extends PageGeometry {
  lines: LayoutLine[];
  columns: LayoutColumn[];
  visualRegions: Array<{ box: Rect; role: VisualRole; confidence: number }>;
  blockIds: string[];
  suppressedItemIndices: number[];
  unsupportedReason?: string;
}
export interface ScholarlyDocument {
  schemaVersion: number;
  parserVersion: string;
  fingerprint: string;
  pageCount: number;
  metadata: { title?: string; pdfjsVersion: string };
  pages: PageAnalysis[];
  blocks: ScholarlyBlock[];
  readingOrder: string[];
  sourceMap: Record<string, SourceSpan[]>;
  warnings: string[];
}
export interface AnalysisProgress {
  completed: number;
  total: number;
  stage: 'hashing' | 'extracting' | 'layout' | 'cached';
}
