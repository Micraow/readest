import DOMPurify from 'dompurify';

/** Shared safety policy for rendered Ovis content and presentation-only link evidence. */
export const sanitizeOvisMarkdown = (html: string) =>
  DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true, mathMl: true },
    ADD_TAGS: ['semantics', 'annotation'],
    FORBID_TAGS: [
      'img',
      'picture',
      'source',
      'audio',
      'video',
      'iframe',
      'object',
      'embed',
      'style',
      'form',
      'input',
      'button',
      'textarea',
      'select',
    ],
    FORBID_ATTR: ['style', 'src', 'srcset', 'background'],
  });
