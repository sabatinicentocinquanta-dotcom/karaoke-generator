"""Frame rendering: every function returns a numpy RGB array (H, W, 3)."""

from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

W, H = 1920, 1080
BG_COLOR   = (10, 10, 30)
WHITE      = (255, 255, 255)
HIGHLIGHT  = (255, 215, 0)    # current word — gold
SUNG_COLOR = (90, 90, 90)     # already sung
NEXT_COLOR = (155, 155, 175)  # next-line preview
ACCENT     = (80, 130, 220)   # title bar

_font_cache: dict[int, ImageFont.FreeTypeFont] = {}

_FONT_PATHS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _font_cache:
        loaded = None
        for p in _FONT_PATHS:
            if os.path.exists(p):
                loaded = ImageFont.truetype(p, size)
                break
        _font_cache[size] = loaded or ImageFont.load_default()
    return _font_cache[size]


def _blank() -> Image.Image:
    return Image.new("RGB", (W, H), BG_COLOR)


def _tw(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _th(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[3] - b[1]


def _cx(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    return (W - _tw(draw, text, font)) // 2


def _title_bar(draw: ImageDraw.ImageDraw, title: str, artist: str) -> None:
    f = _font(34)
    text = f"{title}  —  {artist}"
    draw.text((_cx(draw, text, f), 26), text, font=f, fill=ACCENT)


def _to_array(img: Image.Image) -> np.ndarray:
    return np.array(img)


# ── Public render functions ───────────────────────────────────────────────────

BAR_W      = 900   # progress bar total width
BAR_H      = 18    # progress bar height
BAR_RADIUS = 9     # rounded corners
BAR_Y      = 680   # vertical centre of bar
BAR_BG     = (35, 35, 60)
BAR_FILL_L = (60, 100, 220)   # bar fill — left colour
BAR_FILL_R = (180, 80, 220)   # bar fill — right colour (purple)
NOTE_COLOR = (180, 180, 220)


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def render_intro_countdown(title: str, artist: str, progress: float) -> np.ndarray:
    """progress: 0.0 (start of intro) → 1.0 (singing is about to begin)."""
    img = _blank()
    d   = ImageDraw.Draw(img)

    # Title + artist centred, shifted up to leave room for the bar
    ft = _font(100)
    fa = _font(66)
    th_t = _th(d, title, ft)
    th_a = _th(d, artist, fa)
    gap  = 28
    total_h = th_t + gap + th_a
    y = (BAR_Y - 60 - total_h) // 2 + 40   # vertically centred above bar
    d.text((_cx(d, title, ft), y),            title,  font=ft, fill=WHITE)
    d.text((_cx(d, artist, fa), y + th_t + gap), artist, font=fa, fill=NEXT_COLOR)

    # Progress bar background
    bx = (W - BAR_W) // 2
    d.rounded_rectangle(
        [bx, BAR_Y, bx + BAR_W, BAR_Y + BAR_H],
        radius=BAR_RADIUS, fill=BAR_BG,
    )

    # Progress bar fill (coloured, animated width)
    fill_w = max(BAR_RADIUS * 2, int(BAR_W * progress))
    fill_color = _lerp_color(BAR_FILL_L, BAR_FILL_R, progress)
    d.rounded_rectangle(
        [bx, BAR_Y, bx + fill_w, BAR_Y + BAR_H],
        radius=BAR_RADIUS, fill=fill_color,
    )

    # Musical note at the right end of the bar
    fn = _font(36)
    note = "♪"
    nx = bx + BAR_W + 18
    ny = BAR_Y + BAR_H // 2 - _th(d, note, fn) // 2
    d.text((nx, ny), note, font=fn, fill=NOTE_COLOR)

    return _to_array(img)


def render_intro(title: str, artist: str) -> np.ndarray:
    img = _blank()
    d = ImageDraw.Draw(img)
    ft = _font(100)
    fa = _font(66)
    th_t = _th(d, title, ft)
    th_a = _th(d, artist, fa)
    gap = 28
    total_h = th_t + gap + th_a
    y = (H - total_h) // 2
    d.text((_cx(d, title, ft), y), title, font=ft, fill=WHITE)
    d.text((_cx(d, artist, fa), y + th_t + gap), artist, font=fa, fill=NEXT_COLOR)
    return _to_array(img)


def render_instrumental(title: str, artist: str) -> np.ndarray:
    img = _blank()
    d = ImageDraw.Draw(img)
    _title_bar(d, title, artist)
    f = _font(90)
    text = "♪  Strumentale  ♪"
    d.text((_cx(d, text, f), H // 2 - _th(d, text, f) // 2), text, font=f, fill=HIGHLIGHT)
    return _to_array(img)


def render_ending(title: str, artist: str) -> np.ndarray:
    img = _blank()
    d = ImageDraw.Draw(img)
    _title_bar(d, title, artist)
    f = _font(104)
    text = "Ending"
    d.text((_cx(d, text, f), H // 2 - _th(d, text, f) // 2), text, font=f, fill=WHITE)
    return _to_array(img)


def render_by_frank() -> np.ndarray:
    img = _blank()
    d = ImageDraw.Draw(img)
    f = _font(96)
    text = "by Frank"
    d.text((_cx(d, text, f), H // 2 - _th(d, text, f) // 2), text, font=f, fill=HIGHLIGHT)
    return _to_array(img)


def render_karaoke(
    words_state: list[tuple[str, str]],   # [(word, "sung"|"current"|"upcoming"), ...]
    next_line: str | None,
    title: str,
    artist: str,
) -> np.ndarray:
    img = _blank()
    d = ImageDraw.Draw(img)
    _title_bar(d, title, artist)

    # Pick largest font that fits the line
    full_text = " ".join(w for w, _ in words_state)
    chosen_size = 90
    for size in (90, 72, 56, 44):
        if _tw(d, full_text, _font(size)) < W - 80:
            chosen_size = size
            break

    f_main = _font(chosen_size)
    f_next = _font(max(chosen_size - 24, 36))

    lh = _th(d, "Ag", f_main)
    y_main = (H // 2 - lh // 2) if not next_line else (H // 2 - lh - 18)

    # Build coloured word parts (word + space separator)
    parts: list[tuple[str, tuple[int, int, int]]] = []
    for i, (word, state) in enumerate(words_state):
        sep = "" if i == len(words_state) - 1 else " "
        color = SUNG_COLOR if state == "sung" else HIGHLIGHT if state == "current" else WHITE
        parts.append((word + sep, color))

    total_w = sum(_tw(d, t, f_main) for t, _ in parts)
    x = (W - total_w) // 2
    for text_part, color in parts:
        d.text((x, y_main), text_part, font=f_main, fill=color)
        x += _tw(d, text_part, f_main)

    if next_line:
        # Truncate if too long
        preview = next_line
        while preview and _tw(d, preview + "…", f_next) > W - 80:
            preview = preview.rsplit(" ", 1)[0]
        if preview != next_line:
            preview += "…"
        y_next = y_main + lh + 26
        d.text((_cx(d, preview, f_next), y_next), preview, font=f_next, fill=NEXT_COLOR)

    return _to_array(img)
