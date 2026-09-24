// DSN-1's frozen text rendering explicitly says the glyph cannot be identified
// without its image. Receipt OCR, chart values and document text remain usable.
export const IMAGE_REQUIRED_REASON = 'Not evaluated: image required, but no image was sent.';
export function imageInputExclusion(caseRow, record) {
  return caseRow?.task === 'DSN-1' && record && !(record.images_sent > 0)
    ? IMAGE_REQUIRED_REASON : null;
}
