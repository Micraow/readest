"""Typed native-raster ownership policy. No font names or document identity."""
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class InkConfig:
    render_scale: float = 2.0
    crop_padding_pixels: int = 2
    crop_padding_step_pixels: int = 2
    crop_padding_limit_pixels: int = 12
    glyph_support_fringe_pixels: int = 1
    alpha_component_connectivity: int = 8
    resolve_single_owner_components: bool = True
    maximum_page_seconds: float = 60.0
    maximum_rss_mib: float = 1024.0
    maximum_bitmap_pixels: int = 4_000_000
    preserve_unassigned_ink: bool = True
    reject_ambiguous_owner_pixels: bool = True
    def json(self):return asdict(self)

@dataclass(frozen=True)
class LocalGroupConfig:
    max_width_em: float = 12.0
    max_height_em: float = 2.5
    max_visible_characters: int = 48
    fraction_vertical_reach_em: float = 0.8
    script_size_ratio: float = 0.86
    script_near_em: float = 0.5
    script_baseline_reach_em: float = 1.0
    same_baseline_em: float = 0.2
    math_neighbor_gap_em: float = 0.65
    short_identifier_characters: int = 2
    def json(self):return asdict(self)

@dataclass(frozen=True)
class UnitRenderConfig:
    native_canvas_scope: str = "full_page_internal_only"
    padding_pixels: int = 8
    baseline_major_size_ratio: float = 0.86
    paper_background_rgb: tuple[int,int,int] = (255,255,255)
    def json(self):return asdict(self)

@dataclass(frozen=True)
class ReaderLayoutConfig:
    # Ink-to-ink source gap, independent of the reader's fallback font metrics.
    same_baseline_em: float = 0.2
    maximum_preserved_gap_em: float = 0.8
    fallback_word_gap_em: float = 0.33
    minimum_word_gap_em: float = 0.12
    supported_theme: str = 'source_flat_backdrop_only'
    def json(self):return asdict(self)
