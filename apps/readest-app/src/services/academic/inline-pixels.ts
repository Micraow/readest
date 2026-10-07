/** Find a proven blank seam below the lowest selected glyph's raster baseline. */
export function findInlineBottomCut(
  image: Pick<ImageData, 'width' | 'height' | 'data'>,
  baseline: number,
  scale: number,
): number | undefined {
  if (!Number.isFinite(baseline) || baseline < 0 || baseline >= image.height) return;
  if (!Number.isFinite(scale) || scale <= 0) return;
  // Require at least half a PDF unit, rounded up to full pixels at this density.
  // Every pixel must be almost opaque white; even faint colored ink breaks a seam.
  const minimumBand = Math.max(1, Math.ceil(scale * 0.5));
  let blankRows = 0;
  for (let y = Math.floor(baseline) + 1; y < image.height; y++) {
    let blank = true;
    for (let offset = y * image.width * 4; offset < (y + 1) * image.width * 4; offset += 4) {
      if (
        image.data[offset]! < 250 ||
        image.data[offset + 1]! < 250 ||
        image.data[offset + 2]! < 250 ||
        image.data[offset + 3]! < 250
      ) {
        blank = false;
        break;
      }
    }
    blankRows = blank ? blankRows + 1 : 0;
    if (blankRows >= minimumBand) return y + 1;
  }
  return undefined;
}
