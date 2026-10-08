import { describe, expect, it } from 'vitest';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem, ScholarlyDocument } from '@/services/academic/types';

// Entirely synthetic text and geometry; no source-paper contents are fixtures.
const item = (
  index: number,
  text: string,
  x: number,
  y: number,
  width = 480,
  fontSize = 10,
): PdfTextItem => ({
  index,
  text,
  box: { x, y, width, height: fontSize },
  baseline: y + fontSize * 0.8,
  fontSize,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const page = (
  items: PdfTextItem[],
  graphics: PageGeometry['graphics'] = [],
  pageNumber = 1,
): PageGeometry => ({
  page: pageNumber,
  width: 600,
  height: 800,
  rotation: 0,
  tagged: false,
  items,
  graphics,
});
const analyze = (pages: PageGeometry[]) => analyzeDocument(pages, 'synthetic-cjk-layout', 'test');
const owner = (document: ScholarlyDocument, index: number) =>
  document.blocks.find((block) => block.source.some((span) => span.itemIndices.includes(index)));

describe('CJK scholarly layout retains visible prose and semantic regions', () => {
  it.each([
    '图 1 示例结果。',
    'Figure 1 示例结果。',
    'Figure 1 TEST 示例结果。',
    '图 1 TEST 示例结果。',
  ])('attaches the unpunctuated caption %s to the figure', (caption) => {
    const d = analyze([
      page(
        [
          item(0, caption, 60, 210, 400),
          item(1, '这是图注的第二行说明。', 60, 224, 400),
          item(2, '这里开始下一段正文，并且不属于图注。', 60, 280),
        ],
        [{ kind: 'image', box: { x: 60, y: 90, width: 480, height: 105 } }],
      ),
    ]);
    const figure = d.blocks.find((block) => block.role === 'figure');
    expect(figure?.captions?.[0]?.label).toBe('1');
    expect(figure?.captions?.[0]?.source.itemIndices).toEqual([0, 1]);
    expect(owner(d, 2)?.type).toBe('paragraph');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it.each([
    '表 1 示例测量。',
    'Table 1 示例测量。',
    'Table 1 TEST 示例测量。',
    '表 1 TEST 示例测量。',
  ])('keeps all ruled-table cells together for caption %s', (caption) => {
    const d = analyze([
      page(
        [
          item(0, '这里介绍实验结果，并提供下方的完整数据。', 60, 100),
          item(1, caption, 160, 150, 280),
          item(2, '方案', 80, 180, 50),
          item(3, '数值', 320, 180, 50),
          item(4, '方案甲', 80, 200, 60),
          item(5, '12', 320, 200, 20),
          item(6, '方案乙', 80, 220, 60),
          item(7, '24', 320, 220, 20),
          item(8, '正文从这里继续，数据不能混入后续段落。', 60, 290),
        ],
        [170, 195, 240].map((y) => ({
          kind: 'rule' as const,
          box: { x: 60, y, width: 480, height: 0.5 },
        })),
      ),
    ]);
    const table = d.blocks.find((block) => block.role === 'table');
    expect(table).toBeDefined();
    expect(table?.source[0]?.itemIndices).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(owner(d, 8)?.type).toBe('paragraph');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('does not absorb preceding Chinese prose or a running header rule into a figure', () => {
    const d = analyze([
      page(
        [
          item(0, '本段介绍新的测量方法，并说明实验采用的基本配置。', 60, 130),
          item(1, '所有条件保持一致，接下来展示比较得到的实验结果。', 60, 144),
          item(2, '图 1 示例结果。', 60, 330, 400),
          item(3, '以下正文继续解释这些结果在实验中的具体含义。', 60, 385),
        ],
        [
          { kind: 'rule', box: { x: 60, y: 88, width: 480, height: 0.5 } },
          { kind: 'image', box: { x: 120, y: 220, width: 360, height: 90 } },
        ],
      ),
    ]);
    expect(owner(d, 0)?.type).toBe('paragraph');
    expect(owner(d, 1)?.type).toBe('paragraph');
    const figure = d.blocks.find((block) => block.role === 'figure');
    expect(figure?.source[0]?.boxes[0]?.y).toBeGreaterThan(200);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps CJK sentences with inline equality and Greek letters selectable', () => {
    const d = analyze([
      page([
        item(0, '这里定义实验配置并描述后续的测量方法。', 60, 110),
        item(1, '我们设定参数 α = 3，并观察系统接下来的变化。', 60, 124),
        item(2, '其余的条件保持不变，因此可以直接比较结果。', 60, 138),
      ]),
    ]);
    expect(d.blocks.filter((block) => block.role === 'equation')).toEqual([]);
    expect(owner(d, 1)?.type).toBe('paragraph');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('preserves a CJK heading containing inline mathematics as a heading', () => {
    const d = analyze([
      page([
        { ...item(0, 'A. 关于函数 f(x) = 0 的说明', 60, 100, 350, 18), fontWeight: 'bold' },
        item(1, '这一段用于解释附录的内容及其基本假设。', 60, 155),
        item(2, '后续正文仍然采用与前文相同的排版规则。', 60, 169),
      ]),
    ]);
    expect(owner(d, 0)?.type).toBe('heading');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps Chinese prose immediately beside a numbered display outside its crop', () => {
    const d = analyze([
      page([
        item(0, '以下公式描述一个简单关系，并用于后续计算。', 60, 180),
        item(1, 'x = y + 1', 230, 194, 90),
        item(2, '(1)', 525, 194, 15),
        item(3, '其中各个变量的含义与前文保持一致。', 60, 208),
      ]),
    ]);
    expect(owner(d, 0)?.type).toBe('paragraph');
    expect(owner(d, 3)?.type).toBe('paragraph');
    expect(owner(d, 1)?.role).toBe('equation');
    expect(owner(d, 1)?.source[0]?.itemIndices).toEqual([1, 2]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('recognizes Chinese bibliography headings and wrapped entries', () => {
    const d = analyze([
      page([
        item(0, '参考文献', 60, 100, 120, 16),
        item(1, '[1] A. Example. A generic publication with a long title', 60, 145, 480),
        item(2, 'continued on the next line. Example Journal, 2020.', 80, 159, 440),
        item(3, '[2] B. Example. Another generic publication.', 60, 193, 480),
      ]),
    ]);
    expect(owner(d, 2)?.type).toBe('reference');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps a wrapped reference URL path containing equals as reference text', () => {
    const d = analyze([
      page([
        item(0, 'References', 60, 100, 120, 16),
        item(1, '[1] Example. https://example.org/library/', 60, 150, 480),
        item(2, 'document(v=release.2).html.', 80, 164, 150),
        item(3, '[2] Another generic source follows here.', 60, 195, 480),
      ]),
    ]);
    expect(d.blocks.filter((block) => block.role === 'equation')).toEqual([]);
    expect(owner(d, 2)?.type).toBe('reference');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('suppresses recurring inset footers without removing nearby one-off notes', () => {
    const d = analyze(
      [1, 2, 3].map((number) =>
        page(
          [
            item(0, `第${number}页的正文内容用于检查阅读顺序。`, 60, 150),
            item(1, `这里保留第${number}页的独有说明。`, 60, 665, 300, 8),
            item(2, '示例作者', 60, 716, 80, 9),
            item(3, String(number), 300, 716, 10, 9),
          ],
          [{ kind: 'rule', box: { x: 60, y: 712, width: 480, height: 0.4 } }],
          number,
        ),
      ),
    );
    for (const p of d.pages) {
      expect(p.suppressedItemIndices).toContain(2);
      expect(p.suppressedItemIndices).toContain(3);
      expect(p.suppressedItemIndices).not.toContain(0);
      expect(p.suppressedItemIndices).not.toContain(1);
    }
    expect(validateSourceCoverage(d)).toEqual([]);
  });
});
