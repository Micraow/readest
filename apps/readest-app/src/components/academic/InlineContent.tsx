import { useEffect, useRef, useState, type RefObject } from 'react';
import { useTranslation } from '@/hooks/useTranslation';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { InlineRun, SourceSpan } from '@/services/academic/types';

type InlineProps = {
  session: AcademicPdfSession;
  fontSize: number;
  root: RefObject<HTMLDivElement | null>;
  onZoom: (source: SourceSpan) => void;
};

function InlineSource({
  run,
  session,
  fontSize,
  root,
  onZoom,
}: InlineProps & { run: Extract<InlineRun, { kind: 'source' }> }) {
  const _ = useTranslation();
  const host = useRef<HTMLButtonElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(false);
  const [width, setWidth] = useState(0);
  const [failed, setFailed] = useState(false);
  const box = run.source.boxes[0];
  useEffect(() => {
    const node = host.current;
    if (!node) return;
    const check = () => {
      const rect = node.getBoundingClientRect();
      setVisible(rect.bottom > -600 && rect.top < window.innerHeight + 600);
    };
    if (typeof IntersectionObserver === 'undefined') {
      check();
      const scroller = root.current;
      scroller?.addEventListener('scroll', check, { passive: true });
      window.addEventListener('resize', check);
      return () => {
        scroller?.removeEventListener('scroll', check);
        window.removeEventListener('resize', check);
      };
    }
    const observer = new IntersectionObserver(
      (entries) => setVisible(entries.some((entry) => entry.isIntersecting)),
      { root: root.current, rootMargin: '600px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [root]);
  useEffect(() => {
    const node = host.current;
    if (!node) return;
    const measure = () => setWidth(Math.max(1, node.clientWidth));
    measure();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure);
      return () => window.removeEventListener('resize', measure);
    }
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [fontSize, box]);
  useEffect(() => {
    const target = canvas.current;
    if (!target || !box || !visible || !width) return;
    const controller = new AbortController();
    setFailed(false);
    void session.renderRegion(run.source.page, box, target, width, controller.signal).catch(() => {
      if (!controller.signal.aborted) setFailed(true);
    });
    return () => {
      controller.abort();
      target.width = 0;
      target.height = 0;
    };
  }, [session, run.source.page, box, visible, width]);
  if (!box) return run.text;
  const label = `${_('Equation')}: ${run.text}. ${_('Tap to zoom')}`;
  return (
    <button
      ref={host}
      type='button'
      className='relative inline-block max-w-full overflow-hidden rounded-sm bg-white p-0 text-black focus-visible:outline focus-visible:outline-1'
      style={{
        width: `${box.width / run.fontSize}em`,
        aspectRatio: `${box.width} / ${box.height}`,
        verticalAlign: `${-(box.y + box.height - run.baseline) / run.fontSize}em`,
        lineHeight: 0,
      }}
      aria-label={label}
      title={_('Tap to zoom')}
      onClick={() => onZoom(run.source)}
    >
      <canvas ref={canvas} className='block max-w-full' aria-hidden='true' />
      {failed && (
        <span className='absolute inset-0 overflow-auto bg-white text-[0.75em] leading-tight'>
          {run.text}
        </span>
      )}
    </button>
  );
}

export default function InlineContent({
  runs,
  text,
  omitListMarker,
  ...props
}: InlineProps & { runs?: InlineRun[]; text: string; omitListMarker?: boolean }) {
  if (!runs?.length) return text;
  let prefix = '';
  if (omitListMarker) {
    for (const run of runs) {
      if (run.kind !== 'text') break;
      prefix += run.text;
    }
  }
  let remove = /^\s*(?:[•●▪◦*–-]|\d+[.)])\s+/.exec(prefix)?.[0].length ?? 0;
  return runs.map((run, index) => {
    if (run.kind === 'source') return <InlineSource key={index} run={run} {...props} />;
    const content = run.text.slice(remove);
    remove = Math.max(0, remove - run.text.length);
    const style = { fontStyle: run.style?.fontStyle, fontWeight: run.style?.fontWeight };
    if (run.style?.verticalAlign === 'sub')
      return (
        <sub key={index} style={style}>
          {content}
        </sub>
      );
    if (run.style?.verticalAlign === 'super')
      return (
        <sup key={index} style={style}>
          {content}
        </sup>
      );
    return (
      <span key={index} style={style}>
        {content}
      </span>
    );
  });
}
