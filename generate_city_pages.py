from pathlib import Path
import json
import re
import unicodedata


ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
RESULT_FILE = HTML_DIR / "result.json"
DEFAULT_CITY = "Bogotá"
SITE_NAME = "Divisas COL"
SITE_URL = "https://divisascol.com"
SITE_LOGO = f"{SITE_URL}/assets/logo.svg"
SITE_SOCIAL_IMAGE = f"{SITE_URL}/assets/social-card.png"


CITY_COPY = {
    "Bogotá": {
        "title": "Tasas de cambio en Bogotá | Divisas COL",
        "description": "Compara tasas de compra y venta de dólar, euro y otras divisas en casas de cambio de Bogotá, con datos por moneda, sede y fuente.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Bogotá.",
    },
    "Medellín": {
        "title": "Tasas de cambio en Medellín | Divisas COL",
        "description": "Compara tasas de compra y venta de dólar, euro y otras divisas en casas de cambio de Medellín, con datos por moneda, sede y fuente.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Medellín.",
    },
    "Cali": {
        "title": "Tasas de cambio en Cali | Divisas COL",
        "description": "Compara tasas de compra y venta de dólar, euro y otras divisas en casas de cambio de Cali, con datos por moneda, sede y fuente.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Cali.",
    },
    "Barranquilla": {
        "title": "Tasas de cambio en Barranquilla | Divisas COL",
        "description": "Compara tasas de compra y venta de dólar, euro y otras divisas en casas de cambio de Barranquilla, con datos por moneda, sede y fuente.",
        "intro": "Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en Barranquilla.",
    },
    "Cartagena": {
        "title": "Tasas de cambio en Cartagena | Divisas COL",
        "description": "Compara tasas de compra y venta de dólar, euro y otras divisas en casas de cambio de Cartagena, con datos por moneda, sede y fuente.",
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


def json_ld(data):
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{payload}\n  </script>'


def city_head(city, slug, copy):
    canonical = f"{SITE_URL}/{slug}/"
    structured_data = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": f"{SITE_URL}/#organization",
            "name": SITE_NAME,
            "url": SITE_URL,
            "logo": SITE_LOGO,
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": f"{SITE_URL}/#website",
            "name": SITE_NAME,
            "alternateName": ["Divisas Colombia", "DivisasCol"],
            "url": SITE_URL,
            "publisher": {"@id": f"{SITE_URL}/#organization"},
            "inLanguage": "es-CO",
        },
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": f"{canonical}#webpage",
            "url": canonical,
            "name": copy["title"],
            "description": copy["description"],
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "about": {
                "@type": "Thing",
                "name": f"Tasas de cambio en {city}",
            },
            "inLanguage": "es-CO",
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": SITE_NAME,
                    "item": SITE_URL,
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": f"Tasas de cambio en {city}",
                    "item": canonical,
                },
            ],
        },
    ]

    return f"""  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{copy["title"]}</title>
  <meta name="description" content="{copy["description"]}">
  <meta name="robots" content="index, follow">
  <meta name="theme-color" content="#0f0e0c">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="alternate icon" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/assets/logo.svg">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{copy["title"]}">
  <meta property="og:description" content="{copy["description"]}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:locale" content="es_CO">
  <meta property="og:image" content="{SITE_SOCIAL_IMAGE}">
  <meta property="og:image:alt" content="{SITE_NAME}: comparador de tasas de cambio en Colombia">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{copy["title"]}">
  <meta name="twitter:description" content="{copy["description"]}">
  <meta name="twitter:image" content="{SITE_SOCIAL_IMAGE}">
  {json_ld(structured_data)}
"""


def replace_head_intro(html, replacement):
    pattern = r"<head>\s*.*?(?=\s*<link rel=\"preconnect\" href=\"https://fonts\.googleapis\.com\">)"
    return re.sub(pattern, "<head>\n" + replacement, html, count=1, flags=re.IGNORECASE | re.DOTALL)


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
        "title": f"Tasas de cambio en {city} | Divisas COL",
        "description": f"Compara tasas de compra y venta de divisas en casas de cambio de {city}, con datos por moneda, sede y fuente.",
        "intro": f"Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en {city}.",
    })
    slug = slugify(city)

    html = make_root_relative(template)
    html = html.replace("DiviSAS COL", SITE_NAME)
    html = html.replace("DiviSAS <span>COL</span>", "Divisas <span>COL</span>")
    html = replace_tag(html, r"<html([^>]*)>", f'<html lang="es" data-city="{city}">')
    html = replace_head_intro(html, city_head(city, slug, copy))
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
  <title>Tasas de cambio en Bogotá | Divisas COL</title>
  <meta name="description" content="Compara tasas de compra y venta de dólar, euro y otras divisas en casas de cambio de Bogotá, con datos por moneda, sede y fuente.">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="https://divisascol.com/bogota/">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
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
