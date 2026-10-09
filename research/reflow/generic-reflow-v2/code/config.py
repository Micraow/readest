"""All heuristic decisions live here. No document identity or font-name rules."""
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class Config:
    schema_version: int = 1
    render_scale: float = 2.0
    coordinate_precision_digits: int = 6
    rectangle_precision_digits: int = 3
    geometry_epsilon: float = 0.000001
    line_cluster_lookback: int = 8
    fallback_body_font_pt: float = 10.0
    background_min_glyphs: int = 12
    background_min_area_em2: float = 8.0
    background_rect_area_tolerance: float = 0.02
    background_opacity_min: int = 255
    baseline_tolerance_em: float = 0.25
    word_gap_em: float = 0.22
    column_gap_em: float = 2.5
    paragraph_gap_em: float = 0.7
    paragraph_indent_em: float = 0.8
    list_marker_max_width_em: float = 0.8
    continuation_alignment_em: float = 0.4
    foreground_join_em: float = 0.12
    fraction_rule_min_width_em: float = 1.5
    fraction_vertical_reach_em: float = 1.25
    fraction_side_reach_em: float = 3.0
    attachment_distance_em: float = 0.35
    local_object_padding_em: float = 0.18
    maximum_prose_chars_in_object: int = 80
    maximum_object_height_page_ratio: float = 0.65
    maximum_object_area_page_ratio: float = 0.60
    margin_auxiliary_band_page_ratio: float = 0.055
    margin_mark_width_em: float = 0.65
    minimum_font_pt: float = 1.0
    display_formula_symbol_ratio: float = 0.25
    max_page_seconds: float = 60.0
    max_rss_mib: float = 1024.0
    viewport_width_px: int = 390
    reader_font_px: int = 20

    def json(self): return asdict(self)
