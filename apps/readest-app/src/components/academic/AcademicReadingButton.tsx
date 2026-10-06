import { lazy, Suspense, useEffect, useState } from 'react';
import type { ViewSettings } from '@/types/book';
import { useTranslation } from '@/hooks/useTranslation';
import { useKeyDownActions } from '@/hooks/useKeyDownActions';
import { useAcademicHistory } from './useAcademicHistory';

// PDF parsing and reader UI stay out of the normal PDF opening path.
const AcademicReaderDialog = lazy(() => import('./AcademicReaderDialog'));

function LoadingReading({ onClose }: { onClose: () => void }) {
  const _ = useTranslation();
  useKeyDownActions({ onCancel: onClose });
  useEffect(() => {
    const cancel = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopImmediatePropagation();
      onClose();
    };
    window.addEventListener('keydown', cancel, true);
    return () => window.removeEventListener('keydown', cancel, true);
  }, [onClose]);
  return (
    <button type='button' className='btn btn-ghost btn-sm eink-bordered' onClick={onClose}>
      {_('Cancel')}
    </button>
  );
}

export default function AcademicReadingButton({
  file,
  title,
  onOpenChange,
  viewSettings,
}: {
  file: File;
  title: string;
  viewSettings?: Partial<ViewSettings>;
  onOpenChange?: (open: boolean) => void;
}) {
  const _ = useTranslation();
  const [open, setOpen] = useState(false);
  const change = (next: boolean) => {
    setOpen(next);
    onOpenChange?.(next);
  };
  useAcademicHistory(open, () => change(false));
  return (
    <>
      <button
        type='button'
        className='btn btn-ghost btn-sm eink-bordered min-h-10 shrink-0'
        aria-label={_('PDF / Reading')}
        aria-pressed={open}
        onClick={() => change(true)}
      >
        {_('Reading')}
      </button>
      {open && (
        <Suspense fallback={<LoadingReading onClose={() => change(false)} />}>
          <AcademicReaderDialog
            file={file}
            title={title}
            viewSettings={viewSettings}
            onClose={() => change(false)}
          />
        </Suspense>
      )}
    </>
  );
}
