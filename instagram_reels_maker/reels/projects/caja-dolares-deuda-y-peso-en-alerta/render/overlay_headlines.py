from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "images"
W, H = 1080, 1920

SCENES = [
    ("raw_001_hook.png", "001_hook.png", "DOLAR Y DEUDA", "PONEN AL PESO EN ALERTA"),
    ("raw_002_caja.png", "002_caja.png", "HACIENDA COMPRA", "DOLARES PARA CAJA"),
    ("raw_003_deuda.png", "003_deuda.png", "DEUDA EXTERNA", "US$246.801 MILLONES"),
    ("raw_004_banrep.png", "004_banrep.png", "BANREP AUN VE", "INFLACION INCOMODA"),
    ("raw_005_fiscal.png", "005_fiscal.png", "RIESGO FISCAL", "GASTO ALTO"),
    ("raw_006_cta.png", "006_cta.png", "MERCADO MIRA", "MAS COBERTURA"),
]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for path in [
        Path(r"C:\Windows\Fonts") / name,
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TAG = font("arialbd.ttf", 28)
FONT_HEAD = font("arialbd.ttf", 70)
FONT_SUB = font("arialbd.ttf", 54)


def cover_crop(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    new_size = (round(img.width * scale), round(img.height * scale))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    left = (img.width - W) // 2
    top = (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


def rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def add_gradient(base: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(H):
        top_alpha = max(0, int(120 * (1 - y / 520))) if y < 520 else 0
        bottom_alpha = max(0, int(210 * ((y - 1240) / (H - 1240)))) if y > 1240 else 0
        alpha = max(top_alpha, bottom_alpha)
        if alpha:
            for x in range(W):
                px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(base.convert("RGBA"), overlay)


def draw_text_with_shadow(draw, position, text, font_obj, fill):
    x, y = position
    for dx, dy in [(-2, 2), (2, 2), (0, 3)]:
        draw.text((x + dx, y + dy), text, font=font_obj, fill=(0, 0, 0, 190))
    draw.text((x, y), text, font=font_obj, fill=fill)


def add_headline(img: Image.Image, line1: str, line2: str) -> Image.Image:
    img = add_gradient(img)
    draw = ImageDraw.Draw(img)

    x, y = 64, 96
    tag = "DIVISAS COL | COLOMBIA"
    tag_bbox = draw.textbbox((0, 0), tag, font=FONT_TAG)
    rounded_rect(draw, (x, y, x + tag_bbox[2] + 34, y + 46), 10, (184, 22, 34, 230))
    draw.text((x + 17, y + 8), tag, font=FONT_TAG, fill=(255, 255, 255, 255))

    y += 72
    b1 = draw.textbbox((0, 0), line1, font=FONT_HEAD)
    b2 = draw.textbbox((0, 0), line2, font=FONT_SUB)
    box_w = min(W - 96, max(b1[2], b2[2]) + 56)
    box_h = 194
    rounded_rect(draw, (x - 18, y - 18, x - 18 + box_w, y - 18 + box_h), 14, (0, 0, 0, 170))
    draw_text_with_shadow(draw, (x, y), line1, FONT_HEAD, (255, 255, 255, 255))
    draw_text_with_shadow(draw, (x, y + 82), line2, FONT_SUB, (255, 231, 156, 255))

    return img.convert("RGB")


def main():
    for raw_name, out_name, line1, line2 in SCENES:
        img = cover_crop(Image.open(IMAGES / raw_name))
        img = add_headline(img, line1, line2)
        img.save(IMAGES / out_name, quality=95)


if __name__ == "__main__":
    main()
