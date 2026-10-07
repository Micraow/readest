import { useEffect, useId, useRef, useState } from 'react';
import { useTranslation } from '@/hooks/useTranslation';
import { BoxedList, SettingsRow } from '@/components/settings/primitives';
import { appearanceLimits, type AcademicAppearance } from './useAcademicAppearance';

function AppearanceNumber({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  const _ = useTranslation();
  const id = useId();
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  const commit = (next: number) => {
    const bounded = Math.round(Math.max(min, Math.min(max, next)) * 100) / 100;
    setDraft(String(bounded));
    if (bounded !== value) onChange(bounded);
  };
  return (
    <SettingsRow label={<label htmlFor={id}>{label}</label>} className='flex-wrap py-2'>
      <div role='group' aria-label={label} className='flex shrink-0 items-center gap-1'>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered h-10 w-10 border-base-300 border'
          aria-label={_('Decrease')}
          disabled={value <= min}
          onClick={() => commit(value - step)}
        >
          −
        </button>
        <input
          id={id}
          type='number'
          inputMode={step < 1 ? 'decimal' : 'numeric'}
          className='input input-sm eink-bordered h-10 w-16 text-center'
          min={min}
          max={max}
          step={step}
          value={draft}
          onChange={(event) => {
            const raw = event.target.value;
            setDraft(raw);
            const next = Number(raw);
            if (raw && Number.isFinite(next) && next >= min && next <= max) onChange(next);
          }}
          onBlur={() => commit(draft && Number.isFinite(Number(draft)) ? Number(draft) : value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') event.currentTarget.blur();
          }}
        />
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered h-10 w-10 border-base-300 border'
          aria-label={_('Increase')}
          disabled={value >= max}
          onClick={() => commit(value + step)}
        >
          +
        </button>
      </div>
    </SettingsRow>
  );
}

export default function AcademicAppearancePanel({
  id,
  values,
  onChange,
  onReset,
  onClose,
}: {
  id: string;
  values: AcademicAppearance;
  onChange: (key: keyof AcademicAppearance, value: number) => void;
  onReset: () => void;
  onClose: () => void;
}) {
  const _ = useTranslation();
  const panel = useRef<HTMLElement>(null);
  useEffect(() => panel.current?.focus(), []);
  return (
    <section
      ref={panel}
      id={id}
      tabIndex={-1}
      aria-label={_('Reading appearance')}
      className='bg-base-100 eink-bordered border-base-300 absolute end-3 top-full z-10 mt-1 max-h-[65vh] w-[22rem] max-w-[calc(100%_-_1.5rem)] overflow-y-auto rounded-lg border p-3 shadow-lg outline-none'
    >
      <div className='mb-3 flex items-start justify-between gap-2'>
        <div>
          <h2 className='text-lg font-semibold tracking-tight'>{_('Reading appearance')}</h2>
          <p className='text-base-content/70 text-sm leading-relaxed'>{_('Only this document')}</p>
        </div>
        <button
          type='button'
          className='btn btn-ghost btn-circle eink-bordered h-10 min-h-10 w-10'
          aria-label={_('Close')}
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <BoxedList>
        <AppearanceNumber
          label={_('Font Size')}
          value={values.defaultFontSize}
          {...appearanceLimits.defaultFontSize}
          onChange={(value) => onChange('defaultFontSize', value)}
        />
        <AppearanceNumber
          label={_('Line Spacing')}
          value={values.lineHeight}
          {...appearanceLimits.lineHeight}
          onChange={(value) => onChange('lineHeight', value)}
        />
      </BoxedList>
      <button
        type='button'
        className='btn btn-ghost btn-sm eink-bordered mt-3 min-h-10'
        aria-label={_('Reset reading appearance')}
        onClick={onReset}
      >
        {_('Reset')}
      </button>
    </section>
  );
}
