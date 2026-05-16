from pathlib import Path
import html as html_lib
import json
import re
import shutil
import unicodedata


ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
RESULT_FILE = HTML_DIR / "result.json"
DEFAULT_COUNTRY = "colombia"
DEFAULT_CITY = "Bogotá"
SITE_NAME = "Divisas COL"
SITE_URL = "https://divisascol.com"
SITE_LOGO = f"{SITE_URL}/assets/logo.svg"


COUNTRY_COPY = {
    "colombia": {
        "name": "Colombia",
        "title": "Casas de cambio en Colombia | Divisas COL",
        "description": "Consulta las ciudades de Colombia donde Divisas COL compara tasas de cambio y las casas de cambio disponibles por ciudad.",
        "intro": "Divisas COL organiza referencias publicadas por casas de cambio en Colombia para comparar monedas extranjeras frente al peso colombiano por ciudad.",
        "footer": "Comparador de casas de cambio en Colombia con foco en contexto de mercado, tasas por ciudad y detalle por sede.",
    }
}


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


def country_name(country):
    return COUNTRY_COPY.get(country, {}).get("name", country.title())


def site_social_image(country):
    return f"{SITE_URL}/{country}/assets/social-card.png"


def read_result(html_dir=HTML_DIR):
    return json.loads((html_dir / "result.json").read_text(encoding="utf-8"))


def grouped_by_country(result):
    compact = result.get("countries")
    if compact:
        return expand_compact_countries(compact)

    grouped = result.get("grouped_by_country")
    if grouped:
        return grouped
    legacy = result.get("grouped_by_city") or {}
    return {DEFAULT_COUNTRY: legacy}


def expand_compact_countries(countries):
    expanded = {}

    for country, cities in (countries or {}).items():
        expanded[country] = {}
        for city, houses in (cities or {}).items():
            expanded[country][city] = {}
            for house, locations in (houses or {}).items():
                expanded[country][city][house] = [
                    expand_compact_location(country, city, house, location)
                    for location in (locations or [])
                ]

    return expanded


def expand_compact_location(country, city, house, location):
    if "data" in location:
        return location

    rates = {}
    for currency_id, rate in (location.get("rates") or {}).items():
        rates[rate.get("label") or currency_id] = {
            "buy": rate.get("buy"),
            "sell": rate.get("sell"),
            "id": currency_id,
        }

    return {
        "id": location.get("id") or house,
        "data": rates,
        "city": city,
        "exchange_house": house,
        "source_url": location.get("url") or "",
        "country": country,
    }


def read_template(html_dir=HTML_DIR, country=DEFAULT_COUNTRY):
    candidates = [
        html_dir / country / slugify(DEFAULT_CITY) / "index.html",
        html_dir / slugify(DEFAULT_CITY) / "index.html",
        html_dir / "index.html",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError("No city page template found")


def replace_tag(html, pattern, replacement):
    return re.sub(pattern, replacement, html, count=1, flags=re.IGNORECASE | re.DOTALL)


def json_ld(data):
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{payload}\n  </script>'


def write_text_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\r\n")


def city_head(country, city, slug, copy):
    country_slug = slugify(country)
    canonical = f"{SITE_URL}/{country_slug}/{slug}/"
    country_url = f"{SITE_URL}/{country_slug}/"
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
            "about": {"@type": "Thing", "name": f"Tasas de cambio en {city}"},
            "inLanguage": "es-CO",
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL},
                {"@type": "ListItem", "position": 2, "name": country_name(country), "item": country_url},
                {"@type": "ListItem", "position": 3, "name": f"Tasas de cambio en {city}", "item": canonical},
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
  <meta property="og:image" content="{site_social_image(country)}">
  <meta property="og:image:alt" content="{SITE_NAME}: comparador de tasas de cambio en Colombia">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{copy["title"]}">
  <meta name="twitter:description" content="{copy["description"]}">
  <meta name="twitter:image" content="{site_social_image(country)}">
  {json_ld(structured_data)}
"""


def replace_head_intro(html, replacement):
    pattern = r"<head>\s*.*?(?=<link rel=\"preconnect\" href=\"https://fonts\.googleapis\.com\">)"
    return re.sub(
        pattern,
        "<head>\n" + replacement.rstrip() + "\n",
        html,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def make_city_relative(html, country):
    country_slug = slugify(country)
    replacements = {
        'href="newsletter.html"': 'href="../newsletter/"',
        'href="about.html"': 'href="../../about.html"',
        'href="privacy.html"': 'href="../../privacy.html"',
        'href="index.html"': f'href="../../{country_slug}/"',
        'href="./index.html"': f'href="../../{country_slug}/"',
        'href="./newsletter.html"': 'href="../newsletter/"',
        'href="./aurum-gold.css"': 'href="../../aurum-gold.css"',
        'href="aurum-gold.css"': 'href="../../aurum-gold.css"',
        'href="/newsletter.html"': 'href="../newsletter/"',
        'href="/about.html"': 'href="../../about.html"',
        'href="/privacy.html"': 'href="../../privacy.html"',
        'href="/aurum-gold.css"': 'href="../../aurum-gold.css"',
        'src="aurum-script.js"': 'src="../../aurum-script.js"',
        'src="/aurum-script.js"': 'src="../../aurum-script.js"',
        'src="newsletter-capture.js"': 'src="../../newsletter-capture.js"',
        'src="/newsletter-capture.js"': 'src="../../newsletter-capture.js"',
    }

    for old, new in replacements.items():
        html = html.replace(old, new)

    html = re.sub(r'href="(?:/)?(?:\.\./)*aurum-gold\.css"', 'href="../../aurum-gold.css"', html)
    html = re.sub(r'src="(?:/)?(?:\.\./)*aurum-script\.js"', 'src="../../aurum-script.js"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*newsletter\.html"', 'href="../newsletter/"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*about\.html"', 'href="../../about.html"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*privacy\.html"', 'href="../../privacy.html"', html)
    html = re.sub(r'src="(?:/)?(?:\.\./)*newsletter-capture\.js"', 'src="../../newsletter-capture.js"', html)

    return html


def city_page_html(template, country, city):
    copy = CITY_COPY.get(city, {
        "title": f"Tasas de cambio en {city} | Divisas COL",
        "description": f"Compara tasas de compra y venta de divisas en casas de cambio de {city}, con datos por moneda, sede y fuente.",
        "intro": f"Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en {city}.",
    })
    slug = slugify(city)
    escaped_city = html_lib.escape(city)
    hero_city_dropdown = f'''<h1 class="hero-title">
            Tasas de cambio en
            <span class="hero-city-select-wrap">
              <label for="heroCitySelector" class="sr-only">Seleccionar ciudad</label>
              <select id="heroCitySelector" class="hero-city-selector gold" aria-label="Seleccionar ciudad desde el título">
                <option value="{escaped_city}" selected>{escaped_city}</option>
              </select>
            </span>
          </h1>'''

    html = make_city_relative(template, country)
    html = html.replace("DiviSAS COL", SITE_NAME)
    html = html.replace("DiviSAS <span>COL</span>", "Divisas <span>COL</span>")
    html = replace_tag(html, r"<html([^>]*)>", f'<html lang="es" data-country="{country}" data-city="{city}">')
    html = replace_head_intro(html, city_head(country, city, slug, copy))
    html = replace_tag(
        html,
        r'<h1 class="hero-title">\s*Tasas de cambio en <span class="gold" id="heroCityName">.*?</span>\s*</h1>',
        hero_city_dropdown,
    )
    html = replace_tag(
        html,
        r'<p class="hero-desc" style="margin-bottom: 20px;">.*?</p>',
        f'<p class="hero-desc" style="margin-bottom: 20px;">\n            {copy["intro"]}\n          </p>',
    )
    return html


def exchange_names(groups):
    names = []
    seen = set()
    for house_name, rows in sorted((groups or {}).items()):
        display = house_name
        for row in rows or []:
            display = row.get("id") or row.get("exchange_house") or house_name
            break
        if display not in seen:
            names.append(display)
            seen.add(display)
    return names


def country_landing_html(country, cities):
    copy = COUNTRY_COPY.get(country, {
        "name": country_name(country),
        "title": f"Casas de cambio en {country_name(country)} | Divisas COL",
        "description": f"Consulta las ciudades donde Divisas COL compara tasas de cambio en {country_name(country)}.",
        "intro": f"Divisas COL organiza referencias publicadas por casas de cambio en {country_name(country)}.",
        "footer": f"Comparador de casas de cambio en {country_name(country)} con foco en contexto de mercado, tasas por ciudad y detalle por sede.",
    })
    canonical = f"{SITE_URL}/{slugify(country)}/"
    city_cards = []

    for city, groups in sorted(cities.items(), key=lambda item: item[0]):
        names = exchange_names(groups)
        house_items = "\n".join(f"          <li>{html_lib.escape(name)}</li>" for name in names)
        city_cards.append(
            f"""      <article class="country-city-card">
        <h2><a href="/{slugify(country)}/{slugify(city)}/">{html_lib.escape(city)}</a></h2>
        <p>{len(names)} casas o sedes con datos disponibles.</p>
        <ul>
{house_items}
        </ul>
      </article>"""
        )

    return f"""<!DOCTYPE html>
<html lang="es" data-country="{country}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{copy["title"]}</title>
  <meta name="description" content="{copy["description"]}">
  <meta name="robots" content="index, follow">
  <meta name="theme-color" content="#0f0e0c">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="alternate icon" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/assets/logo.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Libre+Franklin:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../aurum-gold.css">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{copy["title"]}">
  <meta property="og:description" content="{copy["description"]}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{site_social_image(country)}">
</head>
<body>
  <nav class="nav" id="navbar">
    <div class="container">
      <div class="nav-inner">
        <div style="display:flex; align-items:center; gap:14px;">
          <a href="newsletter/" class="back-to-top" style="padding:8px 14px;">Newsletter</a>
          <a href="/{slugify(country)}/" class="logo">Divisas <span>COL</span></a>
        </div>
        <ul class="nav-links">
          <li><a href="#ciudades">Ciudades</a></li>
          <li><a href="../about.html">Acerca de</a></li>
          <li><a href="../privacy.html">Privacidad</a></li>
        </ul>
      </div>
    </div>
  </nav>
  <main class="country-page">
    <section class="hero" id="inicio">
      <div class="container">
        <div class="hero-content">
          <div class="hero-badge"><span class="dot"></span> Divisas en {copy["name"]}</div>
          <h1 class="hero-title">Casas de cambio en {copy["name"]}</h1>
          <p class="hero-desc">{copy["intro"]}</p>
        </div>
      </div>
    </section>
    <section class="services" id="ciudades">
      <div class="container">
        <div class="section-header">
          <div class="section-label">Cobertura actual</div>
          <h2 class="section-title">Casas de cambio por ciudad</h2>
          <p class="section-desc">Ciudades con datos disponibles y casas o sedes incluidas en el comparador.</p>
        </div>
        <div class="country-city-grid">
{chr(10).join(city_cards)}
        </div>
      </div>
    </section>
  </main>
  <footer class="footer">
    <div class="container footer-inner">
      <div>
        <div class="logo footer-logo">Divisas <span>COL</span></div>
        <p class="footer-text">{copy["footer"]}</p>
      </div>
      <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:center; justify-content:flex-end;">
        <a href="../about.html" class="back-to-top">Acerca de</a>
        <a href="../privacy.html" class="back-to-top">Privacidad</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def root_country_index_html(countries):
    country_items = sorted(countries.items(), key=lambda item: country_name(item[0]))

    if len(country_items) == 1:
        country, _cities = country_items[0]
        route = f"/{slugify(country)}/"
        canonical = f"{SITE_URL}{route}"
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Casas de cambio en {country_name(country)} | Divisas COL</title>
  <meta name="description" content="Consulta ciudades y casas de cambio disponibles en {country_name(country)}.">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <meta http-equiv="refresh" content="0; url={route}">
  <script>window.location.replace("{route}");</script>
  <meta property="og:url" content="{canonical}">
</head>
<body>
  <p>Redirigiendo a <a href="{route}">casas de cambio en {country_name(country)}</a>.</p>
</body>
</html>
"""

    cards = []
    for country, cities in country_items:
        route = f"/{slugify(country)}/"
        cards.append(
            f"""      <article class="country-city-card">
        <h2><a href="{route}">{country_name(country)}</a></h2>
        <p>{len(cities or {})} ciudades con datos disponibles.</p>
      </article>"""
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Selecciona país | Divisas COL</title>
  <meta name="description" content="Selecciona el país para consultar ciudades y casas de cambio disponibles en Divisas COL.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{SITE_URL}/">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="alternate icon" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/assets/logo.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Libre+Franklin:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="aurum-gold.css">
</head>
<body>
  <nav class="nav" id="navbar">
    <div class="container">
      <div class="nav-inner">
        <a href="/" class="logo">Divisas <span>COL</span></a>
        <ul class="nav-links">
          <li><a href="#paises">Países</a></li>
          <li><a href="/about.html">Acerca de</a></li>
          <li><a href="/privacy.html">Privacidad</a></li>
        </ul>
      </div>
    </div>
  </nav>
  <main class="country-page">
    <section class="hero" id="inicio">
      <div class="container">
        <div class="hero-content">
          <div class="hero-badge"><span class="dot"></span> Selección de país</div>
          <h1 class="hero-title">Elige un país</h1>
          <p class="hero-desc">Consulta las ciudades y casas de cambio disponibles por país.</p>
        </div>
      </div>
    </section>
    <section class="services" id="paises">
      <div class="container">
        <div class="section-header">
          <div class="section-label">Cobertura actual</div>
          <h2 class="section-title">Países disponibles</h2>
        </div>
        <div class="country-city-grid">
{chr(10).join(cards)}
        </div>
      </div>
    </section>
  </main>
</body>
</html>
"""


def move_country_social_assets(html_dir, country):
    assets_dir = html_dir / "assets"
    country_assets = html_dir / slugify(country) / "assets"
    country_assets.mkdir(parents=True, exist_ok=True)

    for path in assets_dir.glob("social-card*"):
        target = country_assets / path.name
        if target.exists():
            target.unlink()
        shutil.move(str(path), str(target))


def remove_legacy_city_dirs(html_dir, countries):
    country_slugs = {slugify(country) for country in countries}
    protected = {
        "assets",
        *country_slugs,
    }

    for path in html_dir.iterdir():
        if path.is_dir() and path.name not in protected:
            shutil.rmtree(path)


def generate_pages(html_dir=HTML_DIR):
    result = read_result(html_dir)
    countries = grouped_by_country(result)

    for country, cities in countries.items():
        template = read_template(html_dir, country)
        country_dir = html_dir / slugify(country)
        country_dir.mkdir(parents=True, exist_ok=True)
        move_country_social_assets(html_dir, country)

        landing_html = country_landing_html(country, cities)
        write_text_file(country_dir / "index.html", landing_html)

        for city in sorted(cities):
            city_dir = country_dir / slugify(city)
            write_text_file(city_dir / "index.html", city_page_html(template, country, city))

    remove_legacy_city_dirs(html_dir, countries.keys())
    write_text_file(html_dir / "index.html", root_country_index_html(countries))

    return sum(len(cities) for cities in countries.values())


def main():
    count = generate_pages(HTML_DIR)
    print(f"Generated {count} country-scoped city pages")


if __name__ == "__main__":
    main()
