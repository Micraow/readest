import type { CSSProperties } from 'react';
import { useThemeStore } from '@/store/themeStore';

const lightStyle: CSSProperties = { mixBlendMode: 'multiply' };
const darkStyle: CSSProperties = {
  // Match the fixed-layout reader's hue-preserving inversion. Screen makes
  // the inverted white paper blend into the reading surface without resampling.
  filter: 'invert(100%) hue-rotate(180deg)',
  mixBlendMode: 'screen',
};

/** Presentation for math crops only; keep PDF pixels, figures and zoom originals intact. */
export function useMathCanvasStyle(): CSSProperties {
  const isDarkMode = useThemeStore((state) => state.isDarkMode);
  return isDarkMode ? darkStyle : lightStyle;
}
