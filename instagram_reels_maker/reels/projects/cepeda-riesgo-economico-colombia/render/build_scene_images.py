from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_DIR = Path(__file__).resolve().parents[1]
WIDTH = 1080
HEIGHT = 1920
RED = (184, 24, 34, 255)
BLACK = (0, 0, 0, 218)
WHITE = (255, 255, 255, 255)
GOLD = (255, 222, 134, 255)


RAW_IMAGES = {
    "hook": "images/raw_001_hook.png",
    "fiscal": "images/raw_002_fiscal.png",
    "promesas": "images/raw_003_promesas.png",
    "bolsillo": "images/raw_004_bolsillo.png",
    "energia": "images/raw_005_energia.png",
    "cierre": "images/raw_006_cierre.png",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    for path in [
        Path("C:/Windows/Fonts") / name,
        Path("C:/Windows/Fonts/Arial.ttf"),
    ]:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=18, fill=fill)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, typeface: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=typeface)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= 44:
        typeface = font(size, bold=True)
        if all(draw.textbbox((0, 0), line, font=typeface)[2] <= max_width for line in wrap_text(draw, text, typeface, max_width)):
            return typeface
        size -= 4
    return font(44, bold=True)


def draw_overlay(scene: dict[str, object]) -> None:
    scene_id = str(scene["id"])
    source = PROJECT_DIR / RAW_IMAGES[scene_id]
    target = PROJECT_DIR / str(scene["image"])
    headline = str(scene["headline"])
    data_callout = str(scene["data_callout"])

    image = Image.open(source).convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    veil = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    veil_draw = ImageDraw.Draw(veil)
    for y in range(HEIGHT):
        if y < 260:
            alpha = 55
        elif y > 1280:
            alpha = int(30 + 145 * ((y - 1280) / (HEIGHT - 1280)))
        else:
            alpha = 22
        veil_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    image.alpha_composite(veil)

    draw = ImageDraw.Draw(image)
    tag_font = font(34, bold=True)
    main_font = fit_font(draw, headline.replace("DIVISAS COL | COLOMBIA - ", ""), 850, 70)
    data_font = fit_font(draw, data_callout, 850, 54)

    x = 64
    y = 96
    tag = "DIVISAS COL | COLOMBIA"
    tag_box = draw.textbbox((0, 0), tag, font=tag_font)
    rounded(draw, (x, y, x + tag_box[2] + 34, y + 58), RED)
    draw.text((x + 17, y + 11), tag, font=tag_font, fill=WHITE)

    main = headline.replace("DIVISAS COL | COLOMBIA - ", "").upper()
    main_lines = wrap_text(draw, main, main_font, 850)[:2]
    data_lines = wrap_text(draw, data_callout.upper(), data_font, 850)[:2]
    line_gap = 8
    main_height = sum(draw.textbbox((0, 0), line, font=main_font)[3] for line in main_lines)
    data_height = sum(draw.textbbox((0, 0), line, font=data_font)[3] for line in data_lines)
    box_top = 150
    box_bottom = box_top + main_height + data_height + 86 + line_gap * (len(main_lines) + len(data_lines))
    rounded(draw, (48, box_top, 910, box_bottom), BLACK)

    text_y = box_top + 28
    for line in main_lines:
        draw.text((66, text_y), line, font=main_font, fill=WHITE)
        text_y += draw.textbbox((0, 0), line, font=main_font)[3] + line_gap
    for line in data_lines:
        draw.text((66, text_y), line, font=data_font, fill=GOLD)
        text_y += draw.textbbox((0, 0), line, font=data_font)[3] + line_gap

    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(target, quality=95)


def main() -> None:
    data = json.loads((PROJECT_DIR / "reel.json").read_text(encoding="utf-8"))
    for scene in data["scenes"]:
        draw_overlay(scene)


if __name__ == "__main__":
    main()
