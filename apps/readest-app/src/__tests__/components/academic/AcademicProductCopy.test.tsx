import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import zh from '../../../../public/locales/zh-CN/translation.json';
import AcademicReadingButton from '@/components/academic/AcademicReadingButton';
import ScholarlyReader from '@/components/academic/ScholarlyReader';
import type { ScholarlyDocument } from '@/services/academic/types';

vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => (key: string) => (zh as Record<string, string>)[key] ?? key,
}));
vi.mock('@/hooks/useKeyDownActions', () => ({ useKeyDownActions: () => ({}) }));
vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: (select: (state: unknown) => unknown) =>
    select({ settings: { globalViewSettings: { defaultFontSize: 18 } } }),
}));

afterEach(cleanup);
describe('Chinese academic reader product copy', () => {
  it('names the reading mode without changing the existing book reading status', () => {
    render(<AcademicReadingButton file={new File(['%PDF-'], 'paper.pdf')} title='Paper' />);
    expect(screen.getByText('阅读模式')).toBeTruthy();
    expect(zh.Reading).toBe('在读');
    expect(screen.queryByText('在读')).toBeNull();
  });

  it('uses translated image names for accessibility and omits layout-engine details', () => {
    const source = [
      { page: 1, boxes: [{ x: 0, y: 0, width: 200, height: 100 }], itemIndices: [0] },
    ];
    const doc: ScholarlyDocument = {
      schemaVersion: 1,
      parserVersion: 'test',
      fingerprint: 'copy-test',
      pageCount: 1,
      metadata: { pdfjsVersion: 'test' },
      pages: [],
      warnings: [],
      readingOrder: ['figure'],
      sourceMap: { figure: source },
      blocks: [
        {
          id: 'figure',
          type: 'visual-region',
          role: 'figure',
          text: '',
          order: 0,
          confidence: 0.9,
          source,
          fontStats: { median: 10, min: 10, max: 10, names: [] },
          fallbackReason: 'Internal preservation diagnostic',
        },
      ],
    };
    render(
      <ScholarlyReader
        document={doc}
        session={{
          analyze: vi.fn(),
          renderPage: vi.fn(),
          renderRegion: vi.fn().mockResolvedValue(undefined),
          destroy: vi.fn(),
        }}
        onZoom={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: '插图: 点击放大' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '插图: 点击放大' })).toBeTruthy();
    expect(
      screen.queryByText(/Original layout preserved|Internal preservation diagnostic/),
    ).toBeNull();
  });
});
