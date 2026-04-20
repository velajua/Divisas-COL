from pathlib import Path
import json
import re
import unicodedata


ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
RESULT_FILE = HTML_DIR / "result.json"
DEFAULT_CITY = "Bogotá"


CITY_COPY = {
    "Bogotá": {
        "title": "Tasas de cambio en Bogotá | Casas de cambio en Colombia",
        "description": "Compara tasas de compra y venta de dólar, euro y otras monedas en casas de cambio de Bogotá.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Bogotá.",
    },
    "Medellín": {
        "title": "Tasas de cambio en Medellín | Casas de cambio en Colombia",
        "description": "Compara tasas de compra y venta de dólar, euro y otras monedas en casas de cambio de Medellín.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Medellín.",
    },
    "Cali": {
        "title": "Tasas de cambio en Cali | Casas de cambio en Colombia",
        "description": "Compara tasas de compra y venta de dólar, euro y otras monedas en casas de cambio de Cali.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Cali.",
    },
    "Barranquilla": {
        "title": "Tasas de cambio en Barranquilla | Casas de cambio en Colombia",
        "description": "Compara tasas de compra y venta de dólar, euro y otras monedas en casas de cambio de Barranquilla.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Barranquilla.",
    },
    "Cartagena": {
        "title": "Tasas de cambio en Cartagena | Casas de cambio en Colombia",
        "description": "Compara tasas de compra y venta de dólar, euro y otras monedas en casas de cambio de Cartagena.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Cartagena.",
    },
}


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "ciudad"


def read_cities():
    data = json.loads(RESULT_FILE.read_text(encoding="utf-8"))
    return list((data.get("grouped_by_city") or {}).keys())


def read_template():
    city_template = HTML_DIR / slugify(DEFAULT_CITY) / "index.html"
    if city_template.exists():
        return city_template.read_text(encoding="utf-8")
    return (HTML_DIR / "index.html").read_text(encoding="utf-8")


def replace_tag(html, pattern, replacement):
    return re.sub(pattern, replacement, html, count=1, flags=re.IGNORECASE | re.DOTALL)


def make_root_relative(html):
    replacements = {
        'href="newsletter.html"': 'href="../newsletter.html"',
        'href="about.html"': 'href="../about.html"',
        'href="privacy.html"': 'href="../privacy.html"',
        'href="index.html"': 'href="../bogota/"',
        'href="./index.html"': 'href="../bogota/"',
        'href="./newsletter.html"': 'href="../newsletter.html"',
        'href="./aurum-gold.css"': 'href="../aurum-gold.css"',
        'href="aurum-gold.css"': 'href="../aurum-gold.css"',
        'href="/newsletter.html"': 'href="../newsletter.html"',
        'href="/about.html"': 'href="../about.html"',
        'href="/privacy.html"': 'href="../privacy.html"',
        'href="/aurum-gold.css"': 'href="../aurum-gold.css"',
        'src="aurum-script.js"': 'src="../aurum-script.js"',
        'src="/aurum-script.js"': 'src="../aurum-script.js"',
    }

    for old, new in replacements.items():
        html = html.replace(old, new)

    html = re.sub(r'href="(?:/)?(?:\.\./)*aurum-gold\.css"', 'href="../aurum-gold.css"', html)
    html = re.sub(r'src="(?:/)?(?:\.\./)*aurum-script\.js"', 'src="../aurum-script.js"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*newsletter\.html"', 'href="../newsletter.html"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*about\.html"', 'href="../about.html"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*privacy\.html"', 'href="../privacy.html"', html)

    return html


def city_page_html(template, city):
    copy = CITY_COPY.get(city, {
        "title": f"Tasas de cambio en {city} | Casas de cambio en Colombia",
        "description": f"Compara tasas de compra y venta de monedas extranjeras en casas de cambio de {city}.",
        "intro": f"Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en {city}.",
    })

    html = make_root_relative(template)
    html = replace_tag(html, r"<html([^>]*)>", f'<html lang="es" data-city="{city}">')
    html = replace_tag(html, r"<title>.*?</title>", f"<title>{copy['title']}</title>")
    html = replace_tag(
        html,
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        f'<meta name="description" content="{copy["description"]}">',
    )
    html = replace_tag(
        html,
        r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:title" content="{copy["title"]}">',
    )
    html = replace_tag(
        html,
        r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:description" content="{copy["description"]}">',
    )
    html = replace_tag(
        html,
        r'<h1 class="hero-title">\s*Tasas de cambio en <span class="gold" id="heroCityName">.*?</span>\s*</h1>',
        f'<h1 class="hero-title">\n            Tasas de cambio en <span class="gold" id="heroCityName">{city}</span>\n          </h1>',
    )
    html = replace_tag(
        html,
        r'<p class="hero-desc" style="margin-bottom: 20px;">.*?</p>',
        f'<p class="hero-desc" style="margin-bottom: 20px;">\n            {copy["intro"]}\n          </p>',
    )
    return html


def root_redirect_html():
    return """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DiviSAS COL | Tasas de cambio en Bogotá</title>
  <meta name="description" content="Compara tasas de compra y venta de dólar, euro y otras monedas en casas de cambio de Bogotá.">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="https://cedar-setup-376217.web.app/bogota/">
  <meta http-equiv="refresh" content="0; url=/bogota/">
  <script>window.location.replace("/bogota/");</script>
</head>
<body>
  <p>Redirigiendo a <a href="/bogota/">tasas de cambio en Bogotá</a>.</p>
</body>
</html>
"""


def main():
    cities = read_cities()
    template = read_template()

    for city in cities:
        slug = slugify(city)
        city_dir = HTML_DIR / slug
        city_dir.mkdir(parents=True, exist_ok=True)
        (city_dir / "index.html").write_text(
            city_page_html(template, city),
            encoding="utf-8",
        )

    (HTML_DIR / "index.html").write_text(
        root_redirect_html(),
        encoding="utf-8",
    )

    print(f"Generated {len(cities)} city pages")


if __name__ == "__main__":
    main()
