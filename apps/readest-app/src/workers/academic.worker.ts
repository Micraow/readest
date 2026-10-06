import { analyzeDocumentAsync } from '../services/academic/layout';
import type { PageGeometry } from '../services/academic/types';

/** No provider identities or network access belong in this source-neutral worker. */
self.onmessage = async (
  event: MessageEvent<{
    id: number;
    pages: PageGeometry[];
    fingerprint: string;
    pdfjsVersion: string;
  }>,
) => {
  const { id, pages, fingerprint, pdfjsVersion } = event.data;
  try {
    const document = await analyzeDocumentAsync(
      pages,
      fingerprint,
      pdfjsVersion,
      undefined,
      (completed, total) => {
        self.postMessage({ id, progress: { completed, total } });
      },
    );
    self.postMessage({ id, document });
  } catch (error) {
    self.postMessage({
      id,
      error: error instanceof Error ? error.message : 'Academic analysis failed',
    });
  }
};
