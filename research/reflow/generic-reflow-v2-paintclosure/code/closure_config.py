from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class ClosureConfig:
    maximum_page_width_fraction: float = 0.85
    maximum_page_height_fraction: float = 0.55
    maximum_page_area_fraction: float = 0.4
    maximum_visible_characters: int = 1024
    maximum_seed_expansion_ratio: float = 1.5
    maximum_seed_margin_em: float = 2.0
    maximum_seed_margin_fraction: float = 0.25
    attach_fully_enclosed_backgrounds: bool = True
    close_native_character_interval: bool = True
    close_enclosed_paint_units: bool = True
    close_enclosed_text_units: bool = True
    enabled: bool = True
    def json(self):return asdict(self)
