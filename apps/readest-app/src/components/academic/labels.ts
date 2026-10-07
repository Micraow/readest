import type { VisualRole } from '@/services/academic/types';
import { stubTranslation as _ } from '@/utils/misc';

/** Translation keys for the image viewer, not internal parser role names. */
export function visualRoleLabel(role?: VisualRole): string {
  switch (role) {
    case 'figure':
      return _('Figure');
    case 'table':
      return _('Table');
    case 'equation':
      return _('Equation');
    case 'algorithm':
      return _('Algorithm');
    default:
      return _('Image');
  }
}
