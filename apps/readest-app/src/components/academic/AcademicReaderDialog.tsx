import { useEffect, useId, useRef, useState } from 'react';
import type { ViewSettings } from '@/types/book';
import { useEnv } from '@/context/EnvContext';
import { useTranslation } from '@/hooks/useTranslation';
import { useThemeStore } from '@/store/themeStore';
import { useSettingsStore } from '@/store/settingsStore';
import { useKeyDownActions } from '@/hooks/useKeyDownActions';
import { openAcademicPdf, type AcademicPdfSession } from '@/services/academic/runtime';
import { importOvisBundle, readOvisCache } from '@/services/academic/ovis';
import type {
  AnalysisProgress,
  ScholarlyBlock,
  ScholarlyDocument,
} from '@/services/academic/types';
import ModalPortal from '@/components/ModalPortal';
import ImageViewer from '@/app/reader/components/ImageViewer';
import LayoutInspector from './LayoutInspector';
import ScholarlyReader from './ScholarlyReader';
import { useAcademicHistory } from './useAcademicHistory';
import { visualRoleLabel } from './labels';
import AcademicAppearancePanel from './AcademicAppearancePanel';
import { useAcademicAppearance } from './useAcademicAppearance';
import type { AcademicReferenceControl } from './useAcademicReferences';

export default function AcademicReaderDialog({
  file,
  title,
  onClose,
  viewSettings,
}: {
  file: File;
  title: string;
  viewSettings?: Partial<ViewSettings>;
  onClose: () => void;
}) {
  const _ = useTranslation();
  const { appService } = useEnv();
  const insets = useThemeStore((state) => state.safeAreaInsets);
  const [document, setDocument] = useState<ScholarlyDocument | null>(null);
  const activeDocument = useRef<ScholarlyDocument | null>(null);
  const showDocument = (next: ScholarlyDocument | null) => {
    activeDocument.current = next;
    setDocument(next);
  };
  const [nativeDocument, setNativeDocument] = useState<ScholarlyDocument | null>(null);
  const [ovisDocument, setOvisDocument] = useState<ScholarlyDocument | null>(null);
  const [engine, setEngine] = useState<'native' | 'ovis'>('native');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState(false);
  const importInput = useRef<HTMLInputElement>(null);
  const importAbort = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const [session, setSession] = useState<AcademicPdfSession | null>(null);
  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [error, setError] = useState<'' | 'unsupported' | 'failed'>('');
  const [attempt, setAttempt] = useState(0);
  const [inspecting, setInspecting] = useState(false);
  const [appearanceOpen, setAppearanceOpen] = useState(false);
  const appearanceButton = useRef<HTMLButtonElement>(null);
  const appearanceId = useId();
  const globalSettings = useSettingsStore((state) => state.settings.globalViewSettings);
  const { overrides, updateAppearance, scrollRef, positionControl } = useAcademicAppearance(
    document?.fingerprint,
  );
  const readingSettings = { ...globalSettings, ...viewSettings, ...overrides };
  const [zoomUrl, setZoomUrl] = useState<string | null>(null);
  const [zoomRole, setZoomRole] = useState('');
  const [zooming, setZooming] = useState(false);
  const [zoomError, setZoomError] = useState(false);
  const zoomAbort = useRef<AbortController | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const referenceControl = useRef<AcademicReferenceControl>(null);
  const closeZoom = () => {
    zoomAbort.current?.abort();
    setZooming(false);
    setZoomUrl(null);
  };
  const closeAppearance = () => {
    setAppearanceOpen(false);
    appearanceButton.current?.focus();
  };
  const closeTop = () => {
    if (zoomUrl || zooming) closeZoom();
    else if (inspecting) setInspecting(false);
    else if (appearanceOpen) closeAppearance();
    else if (!referenceControl.current?.returnToReading()) onClose();
  };
  const closeRef = useRef(closeTop);
  closeRef.current = closeTop;
  useKeyDownActions({ onCancel: closeTop });
  useAcademicHistory(inspecting, () => setInspecting(false));
  useAcademicHistory(zooming || !!zoomUrl, closeZoom);
  useAcademicHistory(appearanceOpen, closeAppearance);

  useEffect(() => {
    const previous = window.document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeRef.current();
      }
      if (event.key === 'Tab' && panel.current) {
        const controls = Array.from(
          panel.current.querySelectorAll<HTMLElement>(
            ':is(a[href],button:not(:disabled),input:not(:disabled),select:not(:disabled),[tabindex="0"])',
          ),
        ).filter((node) => node.getClientRects().length);
        const first = controls[0],
          last = controls.at(-1);
        if (event.shiftKey && window.document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && window.document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener('keydown', keyboard, true);
    return () => {
      window.removeEventListener('keydown', keyboard, true);
      previous?.focus();
    };
  }, []);

  useEffect(() => {
    if (!appService) return;
    const controller = new AbortController();
    let active: AcademicPdfSession | undefined;
    const opening = ++generation.current;
    importAbort.current?.abort();
    setNativeDocument(null);
    setOvisDocument(null);
    setEngine('native');
    setImporting(false);
    setImportError(false);
    showDocument(null);
    setSession(null);
    setError('');
    setProgress(null);
    setInspecting(false);
    setAppearanceOpen(false);
    setZooming(false);
    setZoomUrl(null);
    setZoomError(false);
    void (async () => {
      try {
        active = await openAcademicPdf(file, controller.signal);
        if (controller.signal.aborted) {
          await active.destroy();
          return;
        }
        setSession(active);
        const cached = await readOvisCache(file, appService, controller.signal);
        if (controller.signal.aborted) return;
        if (cached) {
          if (generation.current === opening || !activeDocument.current) {
            setOvisDocument(cached);
            showDocument(cached);
            setEngine('ovis');
          }
        } else {
          const parsed = await active.analyze(appService, setProgress, controller.signal);
          if (!controller.signal.aborted) {
            setNativeDocument(parsed);
            if (generation.current === opening || !activeDocument.current) {
              showDocument(parsed);
              setEngine('native');
            }
          }
        }
      } catch (cause) {
        if (controller.signal.aborted || (generation.current !== opening && activeDocument.current))
          return;
        setError(
          cause instanceof Error && cause.name === 'NoTextLayerError' ? 'unsupported' : 'failed',
        );
      }
    })();
    return () => {
      controller.abort();
      generation.current++;
      importAbort.current?.abort();
      zoomAbort.current?.abort();
      void active?.destroy().catch(() => undefined);
    };
  }, [file, appService, attempt]);

  const selectEngine = async (next: 'native' | 'ovis') => {
    if (!session || !appService) return;
    const request = ++generation.current;
    importAbort.current?.abort();
    const controller = new AbortController();
    importAbort.current = controller;
    closeZoom();
    setInspecting(false);
    setImportError(false);
    const ready = next === 'ovis' ? ovisDocument : nativeDocument;
    if (ready) {
      showDocument(ready);
      setEngine(next);
      setImporting(false);
      return;
    }
    setImporting(true);
    try {
      const parsed = await session.analyze(appService, setProgress, controller.signal);
      if (!controller.signal.aborted && generation.current === request) {
        setNativeDocument(parsed);
        showDocument(parsed);
        setEngine('native');
      }
    } catch {
      if (!controller.signal.aborted) setImportError(true);
    } finally {
      if (generation.current === request) setImporting(false);
    }
  };
  const importResult = async (result: File) => {
    if (!appService || !session) return;
    const request = ++generation.current;
    importAbort.current?.abort();
    const controller = new AbortController();
    importAbort.current = controller;
    setImporting(true);
    setImportError(false);
    try {
      const parsed = await importOvisBundle(
        file,
        JSON.parse(await result.text()) as unknown,
        appService,
        controller.signal,
      );
      if (!controller.signal.aborted && generation.current === request) {
        closeZoom();
        setInspecting(false);
        setOvisDocument(parsed);
        showDocument(parsed);
        setEngine('ovis');
        setError('');
      }
    } catch {
      if (!controller.signal.aborted) setImportError(true);
    } finally {
      if (generation.current === request) setImporting(false);
    }
  };

  useEffect(
    () => () => {
      if (zoomUrl) URL.revokeObjectURL(zoomUrl);
    },
    [zoomUrl],
  );
  const zoom = async (block: ScholarlyBlock) => {
    const source = block.source[0],
      box = source?.boxes[0];
    if (!session || !source || !box) return;
    zoomAbort.current?.abort();
    const controller = new AbortController();
    zoomAbort.current = controller;
    setZooming(true);
    setZoomError(false);
    setZoomRole(_(visualRoleLabel(block.role)));
    const canvas = window.document.createElement('canvas');
    try {
      await session.renderRegion(
        source.page,
        box,
        canvas,
        Math.min(2048, Math.max(1200, box.width * 3)),
        controller.signal,
        block.trimBelow,
      );
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (controller.signal.aborted) return;
      if (!blob) throw new Error('Canvas unavailable');
      setZoomUrl(URL.createObjectURL(blob));
    } catch {
      if (!controller.signal.aborted) setZoomError(true);
    } finally {
      canvas.width = 0;
      canvas.height = 0;
      if (zoomAbort.current === controller) setZooming(false);
    }
  };
  const labels: Record<AnalysisProgress['stage'], string> = {
    hashing: _('Checking PDF…'),
    extracting: _('Reading PDF…'),
    layout: _('Preparing reading mode…'),
    cached: _('Ready to read'),
  };
  return (
    <ModalPortal showOverlay={false}>
      <div
        ref={panel}
        role='dialog'
        aria-modal='true'
        aria-label={_('Academic Reading Mode')}
        tabIndex={-1}
        className='bg-base-100 text-base-content flex h-full w-full flex-col outline-none'
        style={{ paddingTop: insets?.top ?? 0, paddingBottom: insets?.bottom ?? 0 }}
      >
        <header className='border-base-300 relative flex min-h-14 shrink-0 flex-wrap items-center gap-2 border-b px-3 py-2'>
          <div
            className='join eink-bordered border-base-300 rounded-lg border'
            role='group'
            aria-label={_('PDF / Reading')}
          >
            <button
              type='button'
              className='btn btn-ghost btn-sm join-item min-h-10'
              aria-label={_('Original PDF')}
              onClick={onClose}
            >
              {_('PDF')}
            </button>
            <button
              type='button'
              className='btn btn-contrast btn-sm join-item min-h-10'
              aria-pressed='true'
            >
              {_('Reading mode')}
            </button>
          </div>
          <span className='min-w-0 flex-1 truncate text-sm font-medium'>{title}</span>
          <input
            ref={importInput}
            type='file'
            accept='.json,application/json'
            aria-label={_('Ovis result file')}
            className='hidden'
            onChange={(event) => {
              const selected = event.target.files?.[0];
              event.target.value = '';
              if (selected) void importResult(selected);
            }}
          />
          <button
            type='button'
            className='btn btn-ghost btn-sm eink-bordered min-h-10'
            disabled={!session || importing}
            onClick={() => importInput.current?.click()}
          >
            {_('Import Ovis result')}
          </button>
          {ovisDocument && (
            <div
              role='group'
              aria-label={_('Reading source')}
              className='join eink-bordered border-base-300 rounded-lg border'
            >
              <button
                type='button'
                className='btn btn-ghost btn-sm join-item min-h-10'
                aria-pressed={engine === 'native'}
                onClick={() => void selectEngine('native')}
              >
                {_('Native PDF text')}
              </button>
              <button
                type='button'
                className='btn btn-ghost btn-sm join-item min-h-10'
                aria-pressed={engine === 'ovis'}
                onClick={() => void selectEngine('ovis')}
              >
                Ovis
              </button>
            </div>
          )}
          {document && (
            <button
              ref={appearanceButton}
              type='button'
              className='btn btn-ghost btn-sm eink-bordered min-h-10'
              aria-label={_('Reading appearance')}
              aria-expanded={appearanceOpen}
              aria-controls={appearanceId}
              onClick={() => {
                if (appearanceOpen) closeAppearance();
                else {
                  closeZoom();
                  setInspecting(false);
                  setAppearanceOpen(true);
                }
              }}
            >
              <span aria-hidden='true' className='text-base'>
                Aa
              </span>
            </button>
          )}
          {process.env.NODE_ENV !== 'production' && document && !document.metadata.ovis && (
            <button
              type='button'
              className='btn btn-ghost btn-sm eink-bordered'
              onClick={() => {
                closeZoom();
                setAppearanceOpen(false);
                setInspecting(true);
              }}
            >
              {_('Inspect layout')}
            </button>
          )}
          <button
            type='button'
            className='btn btn-circle btn-ghost eink-bordered shrink-0'
            onClick={onClose}
            aria-label={_('Close Reading Mode')}
          >
            ×
          </button>
          {appearanceOpen && (
            <AcademicAppearancePanel
              id={appearanceId}
              values={{
                defaultFontSize: Math.max(16, readingSettings.defaultFontSize || 18),
                lineHeight: Math.max(1.35, readingSettings.lineHeight || 1.6),
              }}
              onChange={(key, value) => updateAppearance({ ...overrides, [key]: value })}
              onReset={() => updateAppearance({})}
              onClose={closeAppearance}
            />
          )}
        </header>
        <p className='text-base-content/70 border-base-300 border-b px-4 py-2 text-sm'>
          {_(
            'Local Ovis inference is unavailable in this build. You can import a previously generated Ovis result.',
          )}
        </p>
        {importing && (
          <p role='status' className='px-4 py-2 text-sm'>
            {_('Preparing reading mode…')}
          </p>
        )}
        {importError && (
          <p role='alert' className='px-4 py-2 text-sm'>
            {_('Could not import this Ovis result. Check that it belongs to this PDF.')}
          </p>
        )}
        {document?.metadata.ovis && (
          <div className='border-base-300 border-b px-4 py-2 text-sm'>
            <p>{_('Imported Ovis result. Inline symbols may still need checking.')}</p>
            {document.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}
        {error ? (
          <div className='space-y-4 p-6'>
            <p role='alert'>
              {error === 'unsupported'
                ? _('Reading mode is not available for this PDF. Please use the PDF view.')
                : _('Could not open reading mode. Try again or return to the PDF.')}
            </p>
            <button
              type='button'
              className='btn btn-contrast'
              onClick={() => setAttempt((value) => value + 1)}
            >
              {_('Retry')}
            </button>
          </div>
        ) : document && session ? (
          <ScholarlyReader
            key={`${document.fingerprint}:${document.parserVersion}`}
            referenceControl={referenceControl}
            document={document}
            session={session}
            viewSettings={readingSettings}
            scrollRef={scrollRef}
            positionControl={positionControl}
            onZoom={(block) => void zoom(block)}
          />
        ) : (
          <div role='status' aria-live='polite' className='space-y-3 p-6'>
            <p>{progress ? labels[progress.stage] : _('Opening PDF…')}</p>
            {progress && progress.total > 0 && (
              <progress
                className='progress w-full'
                value={progress.completed}
                max={progress.total}
              />
            )}
            <button type='button' className='btn btn-ghost eink-bordered' onClick={onClose}>
              {_('Cancel')}
            </button>
          </div>
        )}
        {zooming && (
          <div className='border-base-300 flex items-center gap-3 border-t p-3' role='status'>
            <span>{_('Loading a clearer image…')}</span>
            <button
              type='button'
              className='btn btn-sm btn-ghost eink-bordered'
              onClick={closeZoom}
            >
              {_('Cancel')}
            </button>
          </div>
        )}
        {zoomError && (
          <p role='alert' className='p-3 text-sm'>
            {_('Could not load the image. Please try again or return to the PDF.')}
          </p>
        )}
        {inspecting && document && session && (
          <LayoutInspector
            document={document}
            renderPage={session.renderPage}
            onClose={() => setInspecting(false)}
          />
        )}
        {zoomUrl && (
          <ImageViewer
            reserveChromeSpace
            src={zoomUrl}
            caption={zoomRole}
            gridInsets={insets ?? { top: 0, right: 0, bottom: 0, left: 0 }}
            onClose={closeZoom}
          />
        )}
      </div>
    </ModalPortal>
  );
}
