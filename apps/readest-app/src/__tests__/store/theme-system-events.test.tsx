import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/utils/style', () => ({
  getThemeCode: vi.fn(() => ({ bg: '#fff', fg: '#000', palette: { 'base-100': '#fff' } })),
}));
vi.mock('@/utils/bridge', () => ({
  getSystemColorScheme: vi.fn(async () => ({ colorScheme: 'light' })),
  startAmbientLightUpdates: vi.fn(async () => ({ success: true })),
  stopAmbientLightUpdates: vi.fn(async () => ({ success: true })),
}));
vi.mock('@tauri-apps/api/core', () => ({
  addPluginListener: vi.fn(async () => ({ unregister: vi.fn() })),
}));
vi.mock('@tauri-apps/api/window', () => ({
  getCurrentWindow: vi.fn(() => ({
    isFullscreen: vi.fn(async () => false),
    isMaximized: vi.fn(async () => false),
  })),
}));
vi.mock('@/services/environment', () => ({ isWebAppPlatform: vi.fn(() => false) }));

import { useMathCanvasStyle } from '@/components/academic/useMathCanvasStyle';
import { initSystemThemeListener, useThemeStore } from '@/store/themeStore';
import type { AppService } from '@/types/system';

// Exercise the real listener, store and math subscriber. The OS media event is
// synthetic; these tests do not establish native Linux or Android acceptance.
class ColorSchemeQuery extends EventTarget {
  matches = false;
  readonly media = '(prefers-color-scheme: dark)';

  change(matches: boolean) {
    this.matches = matches;
    this.dispatchEvent(new Event('change'));
  }
}

const documentListeners = vi.spyOn(document, 'addEventListener');
const windowListeners = vi.spyOn(window, 'addEventListener');
let media: ColorSchemeQuery;

beforeEach(() => {
  documentListeners.mockClear();
  windowListeners.mockClear();
  localStorage.clear();
  useThemeStore.setState({
    themeScope: 'reader',
    themeMode: 'auto',
    readerThemeMode: 'auto',
    libraryThemeMode: null,
    themeColor: 'default',
    readerThemeColor: 'default',
    libraryThemeColor: null,
    isDarkMode: false,
    systemIsDarkMode: false,
    ambientIsDarkMode: false,
  });
  media = new ColorSchemeQuery();
  vi.spyOn(window, 'matchMedia').mockImplementation(() => media as unknown as MediaQueryList);
});

afterEach(() => {
  cleanup();
  for (const [type, listener, options] of documentListeners.mock.calls) {
    document.removeEventListener(type, listener, options);
  }
  for (const [type, listener, options] of windowListeners.mock.calls) {
    window.removeEventListener(type, listener, options);
  }
  vi.mocked(window.matchMedia).mockRestore();
  document.documentElement.removeAttribute('data-theme');
  localStorage.clear();
});

describe.each(['Linux', 'Android'] as const)('%s system-theme event chain', (platform) => {
  const initialize = () => {
    initSystemThemeListener({
      isIOSApp: false,
      isAndroidApp: platform === 'Android',
      isLinuxApp: platform === 'Linux',
      hasWindow: platform === 'Linux',
      hasAmbientLightSensor: false,
    } as AppService);
    return renderHook(useMathCanvasStyle);
  };

  it('updates math from media changes in both directions without setting the store directly', () => {
    const { result } = initialize();
    expect(result.current).toEqual({ mixBlendMode: 'multiply' });
    act(() => media.change(true));
    expect(useThemeStore.getState().systemIsDarkMode).toBe(true);
    expect(localStorage.getItem('systemIsDarkMode')).toBe('true');
    expect(document.documentElement.getAttribute('data-theme')).toBe('default-dark');
    expect(result.current).toEqual({
      filter: 'invert(100%) hue-rotate(180deg)',
      mixBlendMode: 'screen',
    });
    act(() => media.change(false));
    expect(useThemeStore.getState().systemIsDarkMode).toBe(false);
    expect(localStorage.getItem('systemIsDarkMode')).toBe('false');
    expect(document.documentElement.getAttribute('data-theme')).toBe('default-light');
    expect(result.current).toEqual({ mixBlendMode: 'multiply' });
  });

  it('catches up on visibility when a media change was missed', () => {
    const { result } = initialize();
    media.matches = true;
    expect(result.current).toEqual({ mixBlendMode: 'multiply' });
    act(() => document.dispatchEvent(new Event('visibilitychange')));
    expect(useThemeStore.getState().systemIsDarkMode).toBe(true);
    expect(result.current.mixBlendMode).toBe('screen');
    media.matches = false;
    act(() => document.dispatchEvent(new Event('visibilitychange')));
    expect(result.current).toEqual({ mixBlendMode: 'multiply' });
  });

  it('keeps manual light and dark overrides, then resumes current system color in Auto', () => {
    const { result } = initialize();
    act(() => useThemeStore.getState().setThemeMode('light'));
    act(() => media.change(true));
    expect(useThemeStore.getState().systemIsDarkMode).toBe(true);
    expect(result.current).toEqual({ mixBlendMode: 'multiply' });
    act(() => useThemeStore.getState().setThemeMode('auto'));
    expect(result.current.mixBlendMode).toBe('screen');
    act(() => useThemeStore.getState().setThemeMode('dark'));
    act(() => media.change(false));
    expect(useThemeStore.getState().systemIsDarkMode).toBe(false);
    expect(result.current.mixBlendMode).toBe('screen');
    act(() => useThemeStore.getState().setThemeMode('auto'));
    expect(result.current).toEqual({ mixBlendMode: 'multiply' });
  });
});
