# Centralised theme & style constants

# ── Surfaces ─────────────────────────────────────────────────────────────────
BG          = "#0a0a10"          # app background — near-black indigo
SIDEBAR_BG  = "#0d0d15"
CARD        = "#13131c"          # primary surface
CARD2       = "#1b1b28"          # nested / raised surface
BORDER      = "#232332"          # subtle but visible hairline for definition
HOVER       = "#212130"
INPUT_BG    = "#181823"

# ── Accent (violet) ──────────────────────────────────────────────────────────
ACCENT      = "#8b5cf6"
ACCENT_H    = "#7c3aed"
ACCENT_LITE = "#c4b5fd"
ACCENT_BG   = "#221a3f"          # tinted fill for active nav / badges

# ── Semantic colors ──────────────────────────────────────────────────────────
# Teal/rose pair chosen for colorblind-safe separation (deutan ΔE 8.4) while
# keeping cool = gain / warm = loss. Amounts always carry +/− as backup encoding.
INCOME      = "#2dd4bf"
INCOME_BG   = "#0d2b27"
EXPENSE     = "#fb7185"
EXPENSE_BG  = "#2e1220"
WARNING     = "#fbbf24"
WARNING_BG  = "#2d2410"
BALANCE_POS = "#60a5fa"
BALANCE_NEG = "#fb7185"

TEXT        = "#f4f4f6"
TEXT_DIM    = "#8b90a0"          # legible secondary text
TEXT_MUTED  = "#565b6b"          # readable tertiary text

FONT_FAMILY = "SF Pro Display"

# ── Metrics ──────────────────────────────────────────────────────────────────
RADIUS      = 16                 # cards
RADIUS_SM   = 10                 # buttons, inputs, pills
PAD_PAGE    = 28                 # page gutter

PRESET_COLORS = [
    "#f87171","#fb923c","#fbbf24","#facc15",
    "#a3e635","#4ade80","#34d399","#2dd4bf",
    "#38bdf8","#60a5fa","#818cf8","#a78bfa",
    "#c084fc","#f472b6","#fb7185","#94a3b8",
]

MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]

CURRENCIES = ["EUR","USD","GBP","CHF","JPY","CAD","AUD"]

# Dark solid tints (tkinter doesn't support 8-char hex / alpha)
_TINTS = {
    INCOME:      INCOME_BG,
    EXPENSE:     EXPENSE_BG,
    WARNING:     WARNING_BG,
    BALANCE_POS: "#12203a",
    BALANCE_NEG: EXPENSE_BG,
    ACCENT:      ACCENT_BG,
    ACCENT_LITE: ACCENT_BG,
}

def tint(color: str) -> str:
    """Return a dark solid background tint for a given accent color."""
    return _TINTS.get(color, CARD2)


def mix(c1: str, c2: str, t: float) -> str:
    """Linear blend between two hex colors, t in [0, 1]."""
    a = tuple(int(c1[i:i+2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i+2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# Derived hover shades for tinted buttons
INCOME_BG_H  = mix(INCOME_BG, INCOME, 0.12)
EXPENSE_BG_H = mix(EXPENSE_BG, EXPENSE, 0.12)
