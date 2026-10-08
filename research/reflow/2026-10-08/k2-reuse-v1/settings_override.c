#include "setting.h"

/* Uniform fidelity-oriented configuration, frozen before diagnostic outputs.
 * No segmentation or grouping algorithm is changed. */
void k2pdfopt_settings_init_from_koptcontext_upstream(K2PDFOPT_SETTINGS *, const KOPTContext *);
void k2pdfopt_settings_init_from_koptcontext(K2PDFOPT_SETTINGS *s, const KOPTContext *c) {
    k2pdfopt_settings_init_from_koptcontext_upstream(s, c);
    s->hyphen_detect = 0;
    s->src_trim = 0;
    s->contrast_max = 1.0;
    s->dst_gamma = 1.0;
    s->dst_sharpen = 0;
    s->dst_dither = 0;
    s->dst_bpc = 8;
    s->src_paintwhite = 0;
    s->erase_vertical_lines = 0;
    s->erase_horizontal_lines = 0;
    s->dst_negative = 0;
    s->defect_size_pts = 0.0;
#ifdef HAVE_OCR_LIB
    s->dst_ocr = 0;
#endif
}
