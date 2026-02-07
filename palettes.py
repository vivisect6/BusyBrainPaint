"""Curated color palettes for BusyBrainPaint puzzles.

Each palette contains 24 colors ordered so that any prefix (first 6, 8, 12,
16, or 24) forms a maximally distinguishable subset.
"""

import random
from collections import OrderedDict

# Each palette is 24 RGB tuples, ordered for progressive distinguishability.
PALETTES: OrderedDict[str, list[tuple[int, int, int]]] = OrderedDict()

PALETTES["Classic"] = [
    (231, 76, 60),     # Red
    (46, 204, 113),    # Green
    (52, 152, 219),    # Blue
    (241, 196, 15),    # Yellow
    (155, 89, 182),    # Purple
    (230, 126, 34),    # Orange
    (26, 188, 156),    # Teal
    (236, 240, 241),   # Light gray
    (52, 73, 94),      # Dark blue-gray
    (231, 130, 132),   # Light red
    (125, 206, 160),   # Light green
    (133, 193, 233),   # Light blue
    (249, 231, 159),   # Light yellow
    (195, 155, 211),   # Light purple
    (245, 176, 65),    # Light orange
    (115, 198, 182),   # Light teal
    (169, 50, 38),     # Dark red
    (30, 132, 73),     # Dark green
    (36, 113, 163),    # Dark blue
    (183, 149, 11),    # Dark yellow
    (118, 68, 138),    # Dark purple
    (175, 96, 26),     # Dark orange
    (17, 122, 101),    # Dark teal
    (86, 101, 115),    # Medium gray
]

PALETTES["Pastel"] = [
    (255, 179, 186),   # Pastel pink
    (186, 255, 201),   # Pastel green
    (186, 225, 255),   # Pastel blue
    (255, 255, 186),   # Pastel yellow
    (218, 186, 255),   # Pastel purple
    (255, 223, 186),   # Pastel orange
    (186, 255, 255),   # Pastel cyan
    (255, 186, 255),   # Pastel magenta
    (224, 187, 228),   # Pastel lavender
    (149, 225, 211),   # Pastel mint
    (255, 204, 153),   # Pastel peach
    (167, 199, 231),   # Pastel periwinkle
    (255, 214, 214),   # Blush
    (214, 255, 214),   # Honeydew
    (214, 214, 255),   # Pale blue
    (255, 245, 200),   # Cream
    (240, 200, 210),   # Dusty rose
    (200, 235, 210),   # Seafoam pastel
    (200, 215, 240),   # Ice blue
    (245, 225, 200),   # Sand pastel
    (230, 210, 240),   # Wisteria
    (210, 240, 230),   # Aqua pastel
    (250, 220, 230),   # Cotton candy
    (220, 230, 210),   # Sage pastel
]

PALETTES["Jewel"] = [
    (15, 82, 186),     # Sapphire
    (80, 200, 120),    # Emerald
    (224, 17, 95),     # Ruby
    (153, 102, 204),   # Amethyst
    (255, 191, 0),     # Amber/Topaz
    (0, 168, 164),     # Teal jade
    (220, 20, 60),     # Crimson garnet
    (0, 71, 171),      # Cobalt
    (0, 163, 108),     # Jade
    (200, 16, 46),     # Carnelian
    (72, 61, 139),     # Dark slate blue
    (218, 165, 32),    # Goldenrod
    (0, 139, 139),     # Dark cyan
    (199, 21, 133),    # Medium violet-red
    (75, 83, 32),      # Dark olive
    (178, 34, 34),     # Firebrick
    (25, 25, 112),     # Midnight blue
    (34, 139, 34),     # Forest green
    (148, 103, 189),   # Medium purple
    (184, 134, 11),    # Dark goldenrod
    (0, 128, 128),     # Deep teal
    (139, 0, 0),       # Dark red
    (65, 105, 225),    # Royal blue
    (46, 125, 50),     # Malachite
]

PALETTES["Earth"] = [
    (183, 110, 63),    # Terracotta
    (107, 142, 35),    # Olive
    (194, 154, 108),   # Clay
    (76, 70, 50),      # Dark earth
    (210, 180, 140),   # Tan
    (139, 90, 43),     # Saddle brown
    (85, 107, 47),     # Dark olive green
    (205, 133, 63),    # Peru
    (160, 82, 45),     # Sienna
    (188, 170, 132),   # Khaki
    (143, 151, 121),   # Sage
    (101, 67, 33),     # Dark brown
    (222, 184, 135),   # Burlywood
    (128, 128, 0),     # Olive drab
    (210, 105, 30),    # Chocolate
    (189, 183, 164),   # Warm gray
    (170, 130, 80),    # Camel
    (119, 136, 89),    # Moss green
    (150, 113, 80),    # Mocha
    (200, 160, 110),   # Wheat
    (90, 80, 60),      # Umber
    (165, 148, 120),   # Sandstone
    (180, 120, 70),    # Copper brown
    (130, 140, 100),   # Lichen
]

PALETTES["Ocean"] = [
    (0, 119, 190),     # Ocean blue
    (0, 180, 171),     # Teal
    (127, 199, 175),   # Seafoam
    (255, 127, 80),    # Coral
    (237, 201, 175),   # Sand
    (0, 77, 113),      # Deep sea
    (32, 178, 170),    # Light sea green
    (70, 130, 180),    # Steel blue
    (176, 224, 230),   # Powder blue
    (244, 164, 96),    # Sandy brown
    (0, 139, 139),     # Dark cyan
    (95, 158, 160),    # Cadet blue
    (100, 149, 237),   # Cornflower blue
    (72, 209, 204),    # Medium turquoise
    (240, 230, 210),   # Seashell
    (0, 105, 148),     # Cerulean
    (64, 224, 208),    # Turquoise
    (30, 60, 90),      # Navy dark
    (135, 206, 235),   # Sky blue
    (255, 160, 122),   # Light salmon
    (0, 150, 136),     # Teal green
    (173, 216, 230),   # Light blue
    (188, 143, 143),   # Rosy brown
    (47, 79, 79),      # Dark slate gray
]

PALETTES["Sunset"] = [
    (255, 94, 77),     # Sunset red
    (255, 154, 0),     # Amber
    (255, 200, 87),    # Golden
    (180, 62, 109),    # Berry pink
    (93, 39, 93),      # Deep purple
    (255, 127, 80),    # Coral
    (255, 69, 0),      # Red-orange
    (255, 165, 0),     # Orange
    (219, 68, 55),     # Warm red
    (200, 100, 140),   # Dusty rose
    (128, 0, 64),      # Dark magenta
    (255, 218, 150),   # Pale gold
    (230, 57, 70),     # Poppy
    (255, 183, 77),    # Mango
    (160, 50, 90),     # Wine
    (100, 30, 60),     # Dark plum
    (255, 110, 64),    # Deep orange
    (240, 147, 43),    # Tangerine
    (200, 80, 100),    # Mauve
    (70, 20, 50),      # Midnight purple
    (255, 140, 105),   # Light coral
    (235, 180, 100),   # Warm gold
    (170, 40, 80),     # Raspberry
    (255, 200, 150),   # Peach
]

PALETTES["Berry"] = [
    (142, 36, 170),    # Purple
    (216, 27, 96),     # Magenta
    (136, 14, 79),     # Deep pink
    (106, 27, 154),    # Deep purple
    (255, 64, 129),    # Pink accent
    (81, 45, 168),     # Indigo
    (170, 0, 85),      # Raspberry
    (186, 104, 200),   # Light purple
    (244, 143, 177),   # Pink
    (103, 58, 183),    # Deep violet
    (200, 60, 120),    # Hot pink
    (74, 20, 140),     # Very dark purple
    (233, 30, 99),     # Pink 500
    (156, 39, 176),    # Purple 500
    (255, 128, 171),   # Pink light
    (69, 39, 160),     # Deep indigo
    (173, 20, 87),     # Crimson pink
    (149, 117, 205),   # Medium purple
    (240, 98, 146),    # Light rose
    (48, 18, 84),      # Dark night purple
    (197, 17, 98),     # Pink dark
    (126, 87, 194),    # Soft violet
    (255, 105, 135),   # Salmon pink
    (94, 53, 177),     # Purple indigo
]

PALETTES["Autumn"] = [
    (204, 85, 0),      # Burnt orange
    (218, 165, 32),    # Goldenrod
    (128, 0, 0),       # Burgundy
    (107, 142, 35),    # Olive green
    (210, 105, 30),    # Chocolate
    (189, 183, 107),   # Dark khaki
    (178, 34, 34),     # Firebrick
    (184, 134, 11),    # Dark gold
    (160, 82, 45),     # Sienna
    (85, 107, 47),     # Dark olive
    (205, 92, 0),      # Dark orange
    (139, 69, 19),     # Saddle brown
    (244, 164, 96),    # Sandy brown
    (154, 120, 58),    # Tawny
    (165, 42, 42),     # Brown
    (143, 151, 121),   # Artichoke
    (230, 145, 56),    # Carrot
    (120, 80, 40),     # Raw umber
    (180, 140, 60),    # Harvest gold
    (100, 50, 30),     # Dark umber
    (215, 125, 45),    # Pumpkin
    (160, 130, 70),    # Straw
    (145, 60, 30),     # Rust
    (170, 160, 110),   # Pale olive
]

PALETTES["Neon"] = [
    (255, 0, 255),     # Magenta
    (0, 255, 0),       # Green
    (0, 255, 255),     # Cyan
    (255, 255, 0),     # Yellow
    (255, 0, 128),     # Hot pink
    (0, 128, 255),     # Electric blue
    (255, 128, 0),     # Neon orange
    (128, 0, 255),     # Violet
    (0, 255, 128),     # Spring green
    (255, 0, 64),      # Neon red
    (64, 255, 0),      # Lime
    (0, 64, 255),      # Blue
    (255, 64, 255),    # Light magenta
    (64, 255, 255),    # Light cyan
    (255, 255, 64),    # Light yellow
    (255, 64, 128),    # Neon pink
    (128, 255, 0),     # Chartreuse
    (0, 255, 192),     # Aquamarine
    (255, 128, 128),   # Salmon neon
    (192, 0, 255),     # Purple neon
    (0, 192, 255),     # Sky neon
    (255, 192, 0),     # Gold neon
    (128, 255, 128),   # Pale green neon
    (255, 128, 255),   # Orchid neon
]

PALETTES["Stained Glass"] = [
    (0, 51, 160),      # Cobalt blue
    (180, 0, 30),      # Deep crimson
    (0, 128, 58),      # Forest green
    (245, 190, 0),     # Rich gold
    (100, 0, 120),     # Royal purple
    (0, 140, 150),     # Deep teal
    (200, 60, 0),      # Burnt orange
    (20, 20, 80),      # Midnight
    (0, 100, 30),      # Dark emerald
    (160, 0, 60),      # Garnet
    (60, 80, 170),     # Medium blue
    (220, 150, 0),     # Amber
    (80, 0, 80),       # Plum
    (0, 110, 110),     # Dark cyan
    (230, 100, 50),    # Tangerine
    (140, 30, 50),     # Dark rose
    (30, 70, 130),     # Steel blue
    (50, 130, 50),     # Kelly green
    (200, 180, 50),    # Olive gold
    (90, 30, 100),     # Eggplant
    (0, 90, 90),       # Deep aqua
    (170, 50, 20),     # Brick red
    (80, 120, 200),    # Cornflower
    (120, 160, 40),    # Chartreuse
]

PALETTE_NAMES: list[str] = list(PALETTES.keys())


def get_palette(name: str, num_colors: int) -> list[tuple[int, int, int]]:
    """Return the first num_colors colors from the named palette.

    Args:
        name: Palette name, or "Random" to pick one at random.
        num_colors: How many colors to return.

    Returns:
        List of RGB tuples of length num_colors.

    Raises:
        ValueError: If name is not recognized and is not "Random".
    """
    if name == "Random":
        name = random.choice(PALETTE_NAMES)

    if name not in PALETTES:
        raise ValueError(f"Unknown palette: {name!r}. Available: {PALETTE_NAMES}")

    colors = PALETTES[name]
    return colors[:num_colors]
