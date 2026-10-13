import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const { invoke } = vi.hoisted(() => ({ invoke: vi.fn() }));
vi.mock('@tauri-apps/api/core', () => ({ invoke, Channel: class {} }));
vi.mock('@/utils/misc', () => ({ getOSPlatform: () => 'linux' }));

import { verifyUpdateSignature } from '@/utils/bridge';

beforeEach(() => invoke.mockReset());

describe('official update signature bridge', () => {
  it('passes only path and signature, even when JavaScript supplies an extra key', async () => {
    invoke.mockResolvedValueOnce(true);
    const result = await Reflect.apply(verifyUpdateSignature, undefined, [
      '/tmp/Readest.AppImage',
      'artifact-signature',
      'renderer-selected-key',
    ]);
    expect(result).toBe(true);
    expect(invoke).toHaveBeenCalledExactlyOnceWith('verify_update_signature', {
      path: '/tmp/Readest.AppImage',
      signature: 'artifact-signature',
    });
  });

  it('preserves a failed verification result', async () => {
    invoke.mockResolvedValueOnce(false);
    expect(await verifyUpdateSignature('/tmp/Readest.AppImage', 'bad-signature')).toBe(false);
  });

  it('propagates native failures without converting them into success', async () => {
    invoke.mockRejectedValueOnce(new Error('read refused'));
    await expect(verifyUpdateSignature('/tmp/Readest.AppImage', 'sig')).rejects.toThrow(
      'read refused',
    );
  });

  it('native IPC has no caller-controlled verification key and delegates to official policy', () => {
    const source = readFileSync(resolve('src-tauri/src/nightly_update.rs'), 'utf8');
    const command = source
      .split('pub async fn verify_update_signature')[1]!
      .split('/// Progress event')[0]!;
    expect(command).not.toMatch(/pub_key\s*:/);
    expect(command).toContain(
      'crate::update_signature::verify_official_signature(&data, &signature)',
    );
    expect(command).toContain('ensure_path_allowed(&app, &path)');
  });
});
