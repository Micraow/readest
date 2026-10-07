import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { ViewSettings } from '@/types/book';
import type { AcademicPositionControl } from './useAcademicPosition';

export type AcademicAppearance = Pick<ViewSettings, 'defaultFontSize' | 'lineHeight'>;
export const appearanceLimits = {
  defaultFontSize: { min: 16, max: 120, step: 1 },
  lineHeight: { min: 1.35, max: 3, step: 0.05 },
};

export function useAcademicAppearance(fingerprint?: string) {
  const storageKey = fingerprint ? `readest:academic-appearance:${fingerprint}` : '';
  const saved = useMemo(() => {
    const values: Partial<AcademicAppearance> = {};
    if (!storageKey) return values;
    try {
      const stored: unknown = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
      if (stored && typeof stored === 'object') {
        for (const key of ['defaultFontSize', 'lineHeight'] as const) {
          const value = (stored as Partial<AcademicAppearance>)[key];
          const { min, max } = appearanceLimits[key];
          if (typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max) {
            values[key] = value;
          }
        }
      }
    } catch {
      // Reading preferences still work when device storage is unavailable.
    }
    return values;
  }, [storageKey]);
  const [edited, setEdited] = useState<{
    storageKey: string;
    values: Partial<AcademicAppearance>;
  } | null>(null);
  const overrides = edited?.storageKey === storageKey ? edited.values : saved;
  const scrollRef = useRef<HTMLDivElement>(null);
  const positionControl = useRef<AcademicPositionControl | null>(null);

  useLayoutEffect(() => {
    positionControl.current?.restore();
  }, [overrides]);

  const updateAppearance = (values: Partial<AcademicAppearance>) => {
    if (!storageKey) return;
    positionControl.current?.prepare();
    setEdited({ storageKey, values });
    try {
      if (Object.keys(values).length) localStorage.setItem(storageKey, JSON.stringify(values));
      else localStorage.removeItem(storageKey);
    } catch {
      // Keep the change for this session even when it cannot be saved.
    }
  };
  return { overrides, updateAppearance, scrollRef, positionControl };
}
