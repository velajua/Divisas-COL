import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_DIR = Path(__file__).resolve().parents[1]
WIDTH = 1080
HEIGHT = 1920


CARDS = {
    "hook": {
        "label": "DIVISAS COL",
        "title": "Caja en\ndolares",
        "metric": "Peso en alerta",
        "accent": (223, 187, 94),
        "bg": (16, 18, 22),
    },
    "caja": {
        "label": "SENAL 1",
        "title": "El Gobierno\ncompra dolares",
        "metric": "Caja externa",
        "accent": (77, 160, 235),
        "bg": (12, 25, 34),
    },
    "deuda": {
        "label": "SENAL 2",
        "title": "Deuda externa",
        "metric": "USD 246.801M",
        "accent": (229, 83, 70),
        "bg": (34, 20, 22),
    },
    "banrep": {
        "label": "SENAL 3",
        "title": "BanRep no\ncanta victoria",
        "metric": "Inflacion 5,6%",
        "accent": (91, 189, 128),
        "bg": (16, 34, 29),
    },
    "fiscal": {
        "label": "SENAL 4",
        "title": "El fondo\nes fiscal",
        "metric": "Menos credibilidad",
        "accent": (237, 169, 65),
        "bg": (33, 30, 24),
    },
    "cta": {
        "label": "ESTA SEMANA",
        "title": "Cobertura\no calma?",
        "metric": "USD/COP",
        "accent": (238, 238, 230),
        "bg": (20, 22, 28),
    },
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    fonts_dir = Path("C:/Windows/Fonts")
    return ImageFont.truetype(str(fonts_dir / name), size=size)


FONT_BLACK = font("arialbd.ttf", 112)
FONT_TITLE = font("arialbd.ttf", 132)
FONT_METRIC = font("arialbd.ttf", 86)
FONT_SMALL = font("arialbd.ttf", 38)


def draw_wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font_obj, fill, width_chars: int, spacing: int = 14) -> None:
    x, y = xy
    for line in text.splitlines():
        for wrapped in textwrap.wrap(line, width=width_chars) or [""]:
            draw.text((x, y), wrapped, font=font_obj, fill=fill)
            y += font_obj.size + spacing


def make_card(scene: dict) -> None:
    card = CARDS[scene["id"]]
    image = Image.new("RGB", (WIDTH, HEIGHT), card["bg"])
    draw = ImageDraw.Draw(image)
    accent = card["accent"]
    white = (248, 248, 242)
    muted = (202, 204, 197)

    for y in range(HEIGHT):
        shade = int(24 * y / HEIGHT)
        draw.line([(0, y), (WIDTH, y)], fill=tuple(min(255, c + shade) for c in card["bg"]))

    draw.rectangle([0, 0, WIDTH, 34], fill=accent)
    draw.rectangle([76, 164, 420, 230], outline=accent, width=3)
    draw.text((104, 178), card["label"], font=FONT_SMALL, fill=accent)

    draw.line([(76, 530), (1004, 530)], fill=accent, width=6)
    draw.line([(76, 1460), (1004, 1460)], fill=accent, width=6)

    draw_wrapped(draw, (76, 622), card["title"].upper(), FONT_TITLE, white, width_chars=11, spacing=18)
    draw.text((76, 1188), card["metric"].upper(), font=FONT_METRIC, fill=accent)

    output_path = PROJECT_DIR / scene["image"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def main() -> None:
    data = json.loads((PROJECT_DIR / "reel.json").read_text(encoding="utf-8"))
    for scene in data["scenes"]:
        make_card(scene)


if __name__ == "__main__":
    main()
