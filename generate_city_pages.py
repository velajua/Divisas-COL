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
ADSENSE_CLIENT_ID = "ca-pub-8147047207612128"
ADSENSE_ACCOUNT_META_TAG = f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT_ID}">'
ADSENSE_SCRIPT_TAG = (
    f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}"\n'
    '     crossorigin="anonymous"></script>'
)
LOCALES = {
    "es": {"label": "Español", "html_lang": "es"},
    "en": {"label": "English", "html_lang": "en"},
}
COUNTRY_DEFAULT_LOCALE = {"colombia": "es"}
DEFAULT_EXCLUDED_COUNTRY_DIRS = {"assets", *LOCALES}


COUNTRY_COPY = {
    "colombia": {
        "name": "Colombia",
        "title": "Casas de cambio en Colombia | Divisas COL",
        "description": "Consulta las ciudades de Colombia donde Divisas COL compara tasas de cambio y las casas de cambio disponibles por ciudad.",
        "intro": "Divisas COL organiza referencias publicadas por casas de cambio en Colombia para comparar monedas extranjeras frente al peso colombiano por ciudad.",
        "footer": "Comparador de casas de cambio en Colombia con foco en contexto de mercado, tasas por ciudad y detalle por sede.",
    }
}

COUNTRY_COPY_BY_LOCALE = {
    "es": COUNTRY_COPY,
    "en": {
        "colombia": {
            "name": "Colombia",
            "title": "Currency exchange houses in Colombia | Divisas COL",
            "description": "Browse Colombian cities where Divisas COL compares exchange rates and exchange houses by city.",
            "intro": "Divisas COL organizes rates published by exchange houses in Colombia so you can compare foreign currencies against the Colombian peso by city.",
            "footer": "Exchange-house comparison for Colombia with market context, city-level rates, and branch-level detail.",
        }
    },
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

CITY_COPY_BY_LOCALE = {
    "es": CITY_COPY,
    "en": {
        "Bogotá": {
            "title": "Exchange rates in Bogotá | Divisas COL",
            "description": "Compare buy and sell rates for dollars, euros, and other currencies at exchange houses in Bogotá, with data by currency, branch, and source.",
            "intro": "Quick market references for foreign currencies against the Colombian peso, comparing rates published by exchange houses in Bogotá.",
        },
        "Medellín": {
            "title": "Exchange rates in Medellín | Divisas COL",
            "description": "Compare buy and sell rates for dollars, euros, and other currencies at exchange houses in Medellín, with data by currency, branch, and source.",
            "intro": "Quick market references for foreign currencies against the Colombian peso, comparing rates published by exchange houses in Medellín.",
        },
        "Cali": {
            "title": "Exchange rates in Cali | Divisas COL",
            "description": "Compare buy and sell rates for dollars, euros, and other currencies at exchange houses in Cali, with data by currency, branch, and source.",
            "intro": "Quick market references for foreign currencies against the Colombian peso, comparing rates published by exchange houses in Cali.",
        },
        "Barranquilla": {
            "title": "Exchange rates in Barranquilla | Divisas COL",
            "description": "Compare buy and sell rates for dollars, euros, and other currencies at exchange houses in Barranquilla, with data by currency, branch, and source.",
            "intro": "Quick market references for foreign currencies against the Colombian peso, comparing rates published by exchange houses in Barranquilla.",
        },
        "Cartagena": {
            "title": "Exchange rates in Cartagena | Divisas COL",
            "description": "Compare buy and sell rates for dollars, euros, and other currencies at exchange houses in Cartagena, with data by currency, branch, and source.",
            "intro": "Quick market references for foreign currencies against the Colombian peso, comparing rates published by exchange houses in Cartagena.",
        },
    },
}


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "ciudad"


def country_name(country, locale="es"):
    locale_copy = COUNTRY_COPY_BY_LOCALE.get(locale, COUNTRY_COPY_BY_LOCALE["es"])
    return locale_copy.get(country, {}).get("name", COUNTRY_COPY.get(country, {}).get("name", country.title()))


def country_default_locale(country):
    return COUNTRY_DEFAULT_LOCALE.get(country, "es")


def locale_route(locale, country, city=None):
    base = f"/{locale}/{slugify(country)}/"
    if city:
        return f"{base}{slugify(city)}/"
    return base


def default_country_route(country):
    return locale_route(country_default_locale(country), country)


def site_social_image(country, locale=None):
    locale = locale or country_default_locale(country)
    return f"{SITE_URL}{locale_route(locale, country)}assets/social-card.png"


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
        html_dir / country_default_locale(country) / slugify(country) / slugify(DEFAULT_CITY) / "index.html",
        html_dir / slugify(country) / slugify(DEFAULT_CITY) / "index.html",
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


def country_records_from_folders(html_dir, excluded_dirs=None):
    excluded = set(DEFAULT_EXCLUDED_COUNTRY_DIRS if excluded_dirs is None else excluded_dirs)
    records = []

    for path in html_dir.iterdir():
        if not path.is_dir() or path.name in excluded:
            continue
        records.append(
            {
                "slug": path.name,
                "name": country_name(path.name),
                "url": default_country_route(path.name),
            }
        )

    return sorted(records, key=lambda item: item["name"])


def countries_json(countries):
    return json.dumps(countries, ensure_ascii=False, indent=2) + "\n"


def country_records(country_names):
    records = []
    for country in sorted(country_names, key=country_name):
        records.append(
            {
                "slug": slugify(country),
                "name": country_name(country),
                "url": default_country_route(country),
            }
        )
    return records


def translations_json():
    payload = {
        "languages": [
            {"code": code, "label": config["label"]}
            for code, config in LOCALES.items()
        ],
        "countryDefaults": COUNTRY_DEFAULT_LOCALE,
        "countries": {
            country: {
                locale: country_name(country, locale)
                for locale in LOCALES
            }
            for country in sorted({country for copy in COUNTRY_COPY_BY_LOCALE.values() for country in copy})
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def city_head(country, city, slug, copy, locale):
    country_slug = slugify(country)
    canonical = f"{SITE_URL}{locale_route(locale, country, city)}"
    country_url = f"{SITE_URL}{locale_route(locale, country)}"
    html_lang = LOCALES.get(locale, LOCALES["es"])["html_lang"]
    page_about = f"Exchange rates in {city}" if locale == "en" else f"Tasas de cambio en {city}"
    og_locale = "en_US" if locale == "en" else "es_CO"
    image_alt = (
        f"{SITE_NAME}: exchange-rate comparison in {country_name(country, locale)}"
        if locale == "en"
        else f"{SITE_NAME}: comparador de tasas de cambio en {country_name(country, locale)}"
    )
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
            "inLanguage": html_lang,
        },
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": f"{canonical}#webpage",
            "url": canonical,
            "name": copy["title"],
            "description": copy["description"],
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "about": {"@type": "Thing", "name": page_about},
            "inLanguage": html_lang,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL},
                {"@type": "ListItem", "position": 2, "name": country_name(country, locale), "item": country_url},
                {"@type": "ListItem", "position": 3, "name": page_about, "item": canonical},
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
  <meta property="og:locale" content="{og_locale}">
  <meta property="og:image" content="{site_social_image(country, locale)}">
  <meta property="og:image:alt" content="{image_alt}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{copy["title"]}">
  <meta name="twitter:description" content="{copy["description"]}">
  <meta name="twitter:image" content="{site_social_image(country, locale)}">
  {ADSENSE_ACCOUNT_META_TAG}
  {ADSENSE_SCRIPT_TAG}
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
        'href="newsletter.html"': 'href="../../newsletter/"',
        'href="about.html"': 'href="../../about.html"',
        'href="privacy.html"': 'href="../../privacy.html"',
        'href="index.html"': f'href="../"',
        'href="./index.html"': f'href="../"',
        'href="./newsletter.html"': 'href="../../newsletter/"',
        'href="./aurum-gold.css"': 'href="../../../aurum-gold.css"',
        'href="aurum-gold.css"': 'href="../../../aurum-gold.css"',
        'href="/newsletter.html"': 'href="../newsletter/"',
        'href="/about.html"': 'href="../../about.html"',
        'href="/privacy.html"': 'href="../../privacy.html"',
        'href="/aurum-gold.css"': 'href="../../../aurum-gold.css"',
        'src="aurum-script.js"': 'src="../../../aurum-script.js"',
        'src="/aurum-script.js"': 'src="../../../aurum-script.js"',
        'src="newsletter-capture.js"': 'src="../../../newsletter-capture.js"',
        'src="/newsletter-capture.js"': 'src="../../../newsletter-capture.js"',
    }

    for old, new in replacements.items():
        html = html.replace(old, new)

    html = re.sub(r'href="(?:/)?(?:\.\./)*aurum-gold\.css"', 'href="../../../aurum-gold.css"', html)
    html = re.sub(r'src="(?:/)?(?:\.\./)*aurum-script\.js"', 'src="../../../aurum-script.js"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*newsletter\.html"', 'href="../../newsletter/"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*about\.html"', 'href="../../about.html"', html)
    html = re.sub(r'href="(?:/)?(?:\.\./)*privacy\.html"', 'href="../../privacy.html"', html)
    html = re.sub(r'src="(?:/)?(?:\.\./)*newsletter-capture\.js"', 'src="../../../newsletter-capture.js"', html)

    return html


def language_selector_inline_html(country, city, locale):
    options = []
    for code, config in LOCALES.items():
        selected = " selected" if code == locale else ""
        options.append(
            f'                <option value="{locale_route(code, country, city)}"{selected}>{html_lib.escape(config["label"])}</option>'
        )

    return f'''<span class="hero-city-select-wrap">
              <label for="languageSelector" class="sr-only">{"Seleccionar idioma" if locale == "es" else "Select language"}</label>
              <select id="languageSelector" class="hero-city-selector gold" aria-label="{"Seleccionar idioma" if locale == "es" else "Select language"}">
{chr(10).join(options)}
              </select>
            </span>'''


def language_selector_nav_html(country, city, locale):
    options = []
    for code, config in LOCALES.items():
        selected = " selected" if code == locale else ""
        options.append(
            f'              <option value="{locale_route(code, country, city)}"{selected}>{html_lib.escape(config["label"])}</option>'
        )

    return f'''          <span class="hero-city-select-wrap nav-language-selector-wrap">
            <label for="languageSelector" class="sr-only">{"Seleccionar idioma" if locale == "es" else "Select language"}</label>
            <select id="languageSelector" class="hero-city-selector nav-language-selector" aria-label="{"Seleccionar idioma" if locale == "es" else "Select language"}">
{chr(10).join(options)}
            </select>
          </span>'''


def strip_existing_language_selectors(html):
    html = re.sub(
        r'\s*<div class="city-selector-wrap fancy-select language-selector-wrap">.*?</div>',
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r'\s*<span class="hero-city-select-wrap nav-language-selector-wrap">.*?</span>',
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r'\s*<span class="hero-city-select-wrap">\s*<label for="languageSelector".*?</span>',
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html


def localize_city_body(html, locale):
    if locale != "en":
        return html

    replacements = {
        "Tasas de cambio en": "Exchange rates in",
        "Seleccionar ciudad desde el título": "Select city from heading",
        "Seleccionar ciudad": "Select city",
        "Seleccionar idioma": "Select language",
        "Cerrar menú": "Close menu",
        "Abrir menú": "Open menu",
        "Open menú": "Open menu",
        "Resumen": "Overview",
        "Casas": "Houses",
        "Monedas": "Currencies",
        "Detalle": "Details",
        "Acerca de": "About",
        "Privacidad": "Privacy",
        "Referencia de mercado y casas de cambio": "Market reference and exchange houses",
        "Casas de cambio": "Exchange houses",
        "Casas y sedes destacadas": "Featured exchange houses and branches",
        "Detalle completo": "Full details",
        "Monedas detectadas": "Currencies found",
        "Monedas por casa de cambio": "Currencies by exchange house",
        "Casas de cambio": "Exchange houses",
        "Explorar casas": "Explore houses",
        "Ver detalle completo": "View full details",
        "Puntos / sedes": "Locations",
        "Última carga": "Last update",
        "Referencia general": "General reference",
        "Seleccionar primera moneda": "Select first currency",
        "Seleccionar segunda moneda": "Select second currency",
        "Cargando referencia general…": "Loading general reference...",
        "Lectura rápida de oportunidades": "Quick opportunity read",
        "Mejor compra y menor venta para cada moneda, diferencia entre ambas en la ciudad.": "Best buy and lowest sell for each currency, plus the spread between them in the city.",
        "Best buy y menor venta para cada moneda, diferencia entre ambas en la ciudad.": "Best buy and lowest sell for each currency, plus the spread between them in the city.",
        "Datos por sede según las monedas seleccionadas en el comparador superior y acceso a la fuente.": "Branch-level data for the currencies selected above, with source access.",
        "Currencies por casa de cambio": "Currencies by exchange house",
        "Comparativo por moneda": "Currency comparison",
        "Comparación por moneda: mejor compra, menor venta y diferencia entre casas en la ciudad.": "Currency-by-currency comparison: best buy, lowest sell, and spread between exchange houses in the city.",
        "Houses de cambio": "Exchange houses",
        "Houses y sedes destacadas": "Featured exchange houses and branches",
        "Details completo": "Full details",
        "Currencies detectadas": "Currencies found",
        "Vista completa del panorama.": "Complete view of the available rates.",
        "Ciudad": "City",
        "Casa": "House",
        "Sede / ID": "Branch / ID",
        "Moneda": "Currency",
        "Compra": "Buy",
        "Venta": "Sell",
        "Fuente": "Source",
        "Contacto": "Contact",
        "¿Falta una casa de cambio?": "Missing an exchange house?",
        "Si conoces una casa de cambio o sede que debería aparecer aquí, envíala por el formulario para revisarla y agregarla.": "If you know an exchange house or branch that should appear here, send it through the form so it can be reviewed and added.",
        "El enlace abre un formulario de Google para enviar la información.": "The link opens a Google Form to submit the information.",
        "Abrir formulario": "Open form",
        "Comparador de Exchange houses en Colombia con foco en contexto de mercado, tasas por ciudad y detalle por sede.": "Exchange-house comparison for Colombia with market context, city-level rates, and branch-level detail.",
        "Comparador de casas de cambio en Colombia con foco en contexto de mercado, tasas por ciudad y detalle por sede.": "Exchange-house comparison for Colombia with market context, city-level rates, and branch-level detail.",
        "Sugerir casa": "Suggest house",
        "Volver arriba": "Back to top",
        "Mejor compra": "Best buy",
        "Menor venta": "Lowest sell",
        "Lectura del mercado": "Market read",
        "Ver fuente": "View source",
        "Abrir": "Open",
    }

    for old, new in replacements.items():
        html = html.replace(old, new)

    return html


def city_page_html(template, country, city, locale="es"):
    city_copy = CITY_COPY_BY_LOCALE.get(locale, CITY_COPY_BY_LOCALE["es"])
    copy = city_copy.get(city, {
        "title": f"Tasas de cambio en {city} | Divisas COL" if locale == "es" else f"Exchange rates in {city} | Divisas COL",
        "description": f"Compara tasas de compra y venta de divisas en casas de cambio de {city}, con datos por moneda, sede y fuente." if locale == "es" else f"Compare buy and sell rates for currencies at exchange houses in {city}, with data by currency, branch, and source.",
        "intro": f"Referencias rápidas del mercado para monedas extranjeras frente al peso colombiano, con comparación de tasas publicadas por casas de cambio en {city}." if locale == "es" else f"Quick market references for foreign currencies, comparing rates published by exchange houses in {city}.",
    })
    slug = slugify(city)
    escaped_city = html_lib.escape(city)
    html_lang = LOCALES.get(locale, LOCALES["es"])["html_lang"]
    heading_prefix = "Tasas de cambio en" if locale == "es" else "Exchange rates in"
    city_label = "Seleccionar ciudad" if locale == "es" else "Select city"
    city_heading_label = "Seleccionar ciudad desde el título" if locale == "es" else "Select city from heading"
    hero_city_dropdown = f'''<h1 class="hero-title">
            {heading_prefix}
            <span class="hero-city-select-wrap">
              <label for="heroCitySelector" class="sr-only">{city_label}</label>
              <select id="heroCitySelector" class="hero-city-selector gold" aria-label="{city_heading_label}">
                <option value="{escaped_city}" selected>{escaped_city}</option>
              </select>
            </span>
          </h1>'''

    html = strip_existing_language_selectors(make_city_relative(template, country))
    html = html.replace("DiviSAS COL", SITE_NAME)
    html = html.replace("DiviSAS <span>COL</span>", "Divisas <span>COL</span>")
    html = html.replace('href="#inicio" class="logo"', f'href="{locale_route(locale, country)}" class="logo"')
    html = re.sub(
        r'href="/(?:' + "|".join(re.escape(code) for code in LOCALES) + r')/' + re.escape(slugify(country)) + r'/" class="logo"',
        f'href="{locale_route(locale, country)}" class="logo"',
        html,
    )
    html = replace_tag(html, r"<html([^>]*)>", f'<html lang="{html_lang}" data-locale="{locale}" data-country="{country}" data-city="{city}">')
    html = replace_head_intro(html, city_head(country, city, slug, copy, locale))
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
    if 'id="citySelector"' in html:
        html = html.replace(
            '          </div>\n        </div>\n        <button class="mobile-menu-btn"',
            f'          </div>\n{language_selector_nav_html(country, city, locale)}\n        </div>\n        <button class="mobile-menu-btn"',
            1,
        )
    else:
        html = html.replace("</h1>", f"\n            {language_selector_inline_html(country, city, locale)}\n          </h1>", 1)
    html = localize_city_body(html, locale)
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


def country_selector_html(country, locale):
    route = locale_route(locale, country)
    label = "Select country" if locale == "en" else "Seleccionar país"
    return f'''<span class="hero-city-select-wrap">
              <label for="countrySelector" class="sr-only">{label}</label>
              <select id="countrySelector" class="hero-city-selector gold" aria-label="{label}">
                <option value="{route}" selected>{html_lib.escape(country_name(country, locale))}</option>
              </select>
            </span>'''


def country_selector_script(locale):
    return """  <script>
    (function () {
      const selector = document.getElementById("countrySelector");
      if (!selector) return;
      const locale = document.documentElement.dataset.locale || "es";

      const escapeHtml = (value) => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");

      fetch("/countries.json", { cache: "no-store" })
        .then((response) => response.ok ? response.json() : [])
        .then((countries) => {
          if (!Array.isArray(countries) || !countries.length) return;

          const current = selector.value;
          selector.innerHTML = countries
            .map((country) => {
              const url = country.slug ? `/${locale}/${country.slug}/` : country.url;
              const selected = url === current ? " selected" : "";
              return `<option value="${escapeHtml(url)}"${selected}>${escapeHtml(country.name || country.slug)}</option>`;
            })
            .join("");
          selector.value = current;
        })
        .catch(() => {});

      selector.addEventListener("change", () => {
        if (selector.value) {
          window.location.href = selector.value;
        }
      });
    })();
  </script>"""


def language_selector_html(country, locale):
    options = []
    for code, config in LOCALES.items():
        selected = " selected" if code == locale else ""
        options.append(f'                <option value="{locale_route(code, country)}"{selected}>{html_lib.escape(config["label"])}</option>')

    label = "Select language" if locale == "en" else "Seleccionar idioma"
    return f'''<span class="hero-city-select-wrap">
              <label for="languageSelector" class="sr-only">{label}</label>
              <select id="languageSelector" class="hero-city-selector gold" aria-label="{label}">
{chr(10).join(options)}
              </select>
            </span>'''


def language_selector_script():
    return """  <script>
    (function () {
      const selector = document.getElementById("languageSelector");
      if (!selector) return;
      const country = document.documentElement.dataset.country || "colombia";

      const escapeHtml = (value) => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");

      fetch("/translations.json", { cache: "no-store" })
        .then((response) => response.ok ? response.json() : null)
        .then((translations) => {
          const languages = translations?.languages;
          if (!Array.isArray(languages) || !languages.length) return;

          const current = selector.value;
          selector.innerHTML = languages
            .map((language) => {
              const url = `/${language.code}/${country}/`;
              const selected = url === current ? " selected" : "";
              return `<option value="${escapeHtml(url)}"${selected}>${escapeHtml(language.label || language.code)}</option>`;
            })
            .join("");
          selector.value = current;
        })
        .catch(() => {});

      selector.addEventListener("change", () => {
        if (selector.value) {
          window.location.href = selector.value;
        }
      });
    })();
  </script>"""


def country_landing_html(country, cities, locale="es"):
    locale_copy = COUNTRY_COPY_BY_LOCALE.get(locale, COUNTRY_COPY_BY_LOCALE["es"])
    copy = locale_copy.get(country, {
        "name": country_name(country, locale),
        "title": f"Casas de cambio en {country_name(country, locale)} | Divisas COL" if locale == "es" else f"Currency exchange houses in {country_name(country, locale)} | Divisas COL",
        "description": f"Consulta las ciudades donde Divisas COL compara tasas de cambio en {country_name(country, locale)}." if locale == "es" else f"Browse cities where Divisas COL compares exchange rates in {country_name(country, locale)}.",
        "intro": f"Divisas COL organiza referencias publicadas por casas de cambio en {country_name(country, locale)}." if locale == "es" else f"Divisas COL organizes rates published by exchange houses in {country_name(country, locale)}.",
        "footer": f"Comparador de casas de cambio en {country_name(country, locale)} con foco en contexto de mercado, tasas por ciudad y detalle por sede." if locale == "es" else f"Exchange-house comparison for {country_name(country, locale)} with market context, city-level rates, and branch-level detail.",
    })
    canonical = f"{SITE_URL}{locale_route(locale, country)}"
    html_lang = LOCALES.get(locale, LOCALES["es"])["html_lang"]
    nav_cities = "Cities" if locale == "en" else "Ciudades"
    country_badge = f"Currencies in {copy['name']}" if locale == "en" else f"Divisas en {copy['name']}"
    hero_heading = "Exchange houses in" if locale == "en" else "Casas de cambio en"
    coverage_label = "Current coverage" if locale == "en" else "Cobertura actual"
    section_title = "Exchange houses by city" if locale == "en" else "Casas de cambio por ciudad"
    section_desc = (
        "Cities with available data and exchange houses or branches included in the comparison."
        if locale == "en"
        else "Ciudades con datos disponibles y casas o sedes incluidas en el comparador."
    )
    image_alt = (
        f"{SITE_NAME}: exchange-house coverage in {copy['name']}"
        if locale == "en"
        else f"{SITE_NAME}: cobertura de casas de cambio en {copy['name']}"
    )
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
            "inLanguage": html_lang,
        },
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "@id": f"{canonical}#webpage",
            "url": canonical,
            "name": copy["title"],
            "description": copy["description"],
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "about": {"@type": "Country", "name": copy["name"]},
            "inLanguage": html_lang,
        },
    ]
    city_cards = []

    for city, groups in sorted(cities.items(), key=lambda item: item[0]):
        names = exchange_names(groups)
        house_items = "\n".join(f"          <li>{html_lib.escape(name)}</li>" for name in names)
        count_label = (
            f"{len(names)} exchange houses or branches with available data."
            if locale == "en"
            else f"{len(names)} casas o sedes con datos disponibles."
        )
        city_cards.append(
            f"""      <article class="country-city-card">
        <h2><a href="{locale_route(locale, country, city)}">{html_lib.escape(city)}</a></h2>
        <p>{count_label}</p>
        <ul>
{house_items}
        </ul>
      </article>"""
        )

    return f"""<!DOCTYPE html>
<html lang="{html_lang}" data-locale="{locale}" data-country="{country}">
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
  <link rel="stylesheet" href="../../aurum-gold.css">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{copy["title"]}">
  <meta property="og:description" content="{copy["description"]}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{site_social_image(country, locale)}">
  <meta property="og:image:alt" content="{image_alt}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{copy["title"]}">
  <meta name="twitter:description" content="{copy["description"]}">
  <meta name="twitter:image" content="{site_social_image(country, locale)}">
  {ADSENSE_ACCOUNT_META_TAG}
  {ADSENSE_SCRIPT_TAG}
  {json_ld(structured_data)}
</head>
<body>
  <nav class="nav" id="navbar">
    <div class="container">
      <div class="nav-inner">
        <div style="display:flex; align-items:center; gap:14px;">
          <a href="newsletter/" class="back-to-top" style="padding:8px 14px;">Newsletter</a>
          <a href="{locale_route(locale, country)}" class="logo">Divisas <span>COL</span></a>
        </div>
        <ul class="nav-links">
          <li><a href="#ciudades">{nav_cities}</a></li>
          <li><a href="../about.html">{"Acerca de" if locale == "es" else "About"}</a></li>
          <li><a href="../privacy.html">{"Privacidad" if locale == "es" else "Privacy"}</a></li>
          <li>{language_selector_html(country, locale)}</li>
        </ul>
      </div>
    </div>
  </nav>
  <main class="country-page">
    <section class="hero" id="inicio">
      <div class="container">
        <div class="hero-content">
          <div class="hero-badge"><span class="dot"></span> {country_badge}</div>
          <h1 class="hero-title">
            {hero_heading}
            {country_selector_html(country, locale)}
          </h1>
          <p class="hero-desc">{copy["intro"]}</p>
        </div>
      </div>
    </section>
    <section class="services" id="ciudades">
      <div class="container">
        <div class="section-header">
          <div class="section-label">{coverage_label}</div>
          <h2 class="section-title">{section_title}</h2>
          <p class="section-desc">{section_desc}</p>
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
        <a href="../about.html" class="back-to-top">{"Acerca de" if locale == "es" else "About"}</a>
        <a href="../privacy.html" class="back-to-top">{"Privacidad" if locale == "es" else "Privacy"}</a>
      </div>
    </div>
  </footer>
{country_selector_script(locale)}
{language_selector_script()}
</body>
</html>
"""


def redirect_html(title, route):
    canonical = f"{SITE_URL}{route}"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{canonical}">
  <meta http-equiv="refresh" content="0; url={route}">
  {ADSENSE_ACCOUNT_META_TAG}
  {ADSENSE_SCRIPT_TAG}
  <script>window.location.replace("{route}");</script>
</head>
<body>
  <p>Redirigiendo a <a href="{route}">{html_lib.escape(title)}</a>.</p>
</body>
</html>
"""


def root_country_index_html(countries):
    country_items = sorted(countries.items(), key=lambda item: country_name(item[0]))
    default_country = country_items[0][0] if country_items else DEFAULT_COUNTRY

    cards = []
    for country, cities in country_items:
        route = default_country_route(country)
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
  <title>Divisas COL</title>
  <meta name="description" content="Selecciona país e idioma para consultar ciudades y casas de cambio disponibles en Divisas COL.">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{SITE_URL}/">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="alternate icon" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/assets/logo.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Libre+Franklin:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="aurum-gold.css">
  <meta property="og:url" content="{SITE_URL}/">
  {ADSENSE_ACCOUNT_META_TAG}
  {ADSENSE_SCRIPT_TAG}
</head>
<body>
  <nav class="nav" id="navbar">
    <div class="container">
      <div class="nav-inner">
        <a href="/" class="logo">Divisas <span>COL</span></a>
        <ul class="nav-links">
          <li><a href="#paises">Países</a></li>
          <li><a href="/es/about.html">Acerca de</a></li>
          <li><a href="/es/privacy.html">Privacidad</a></li>
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
  <script>
    (function () {{
      const defaultCountry = "{slugify(default_country)}";
      const supportedLocales = {json.dumps(list(LOCALES.keys()))};
      const languages = navigator.languages || [navigator.language || "es"];
      const locale = languages
        .map((language) => String(language || "").slice(0, 2).toLowerCase())
        .find((language) => supportedLocales.includes(language)) || "{country_default_locale(default_country)}";
      const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      const country = timeZone.includes("Bogota") ? "colombia" : defaultCountry;
      window.location.replace(`/${{locale}}/${{country}}/`);
    }})();
  </script>
</body>
</html>
"""


def locale_index_html(locale, countries):
    country_items = sorted(countries.items(), key=lambda item: country_name(item[0], locale))
    default_country = country_items[0][0] if country_items else DEFAULT_COUNTRY
    html_lang = LOCALES.get(locale, LOCALES["es"])["html_lang"]
    is_en = locale == "en"
    title = "Divisas COL | Choose country" if is_en else "Divisas COL | Elige país"
    description = (
        "Choose the country to view exchange houses and city-level exchange rates."
        if is_en
        else "Elige el país para consultar casas de cambio y tasas por ciudad."
    )
    badge = "Country selection" if is_en else "Selección de país"
    heading = "Choose a country" if is_en else "Elige un país"
    intro = (
        "We will send you to the country homepage for this language."
        if is_en
        else "Te llevamos al inicio del país para este idioma."
    )
    section_label = "Current coverage" if is_en else "Cobertura actual"
    section_title = "Available countries" if is_en else "Países disponibles"
    about_label = "About" if is_en else "Acerca de"
    privacy_label = "Privacy" if is_en else "Privacidad"
    available_label = "cities with available data" if is_en else "ciudades con datos disponibles"

    cards = []
    for country, cities in country_items:
        route = locale_route(locale, country)
        cards.append(
            f"""      <article class="country-city-card">
        <h2><a href="{route}">{country_name(country, locale)}</a></h2>
        <p>{len(cities or {})} {available_label}.</p>
      </article>"""
        )

    return f"""<!DOCTYPE html>
<html lang="{html_lang}" data-locale="{locale}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{SITE_URL}/{locale}/">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="alternate icon" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/assets/logo.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Libre+Franklin:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../aurum-gold.css">
  <meta property="og:url" content="{SITE_URL}/{locale}/">
  {ADSENSE_ACCOUNT_META_TAG}
  {ADSENSE_SCRIPT_TAG}
</head>
<body>
  <nav class="nav" id="navbar">
    <div class="container">
      <div class="nav-inner">
        <a href="/{locale}/" class="logo">Divisas <span>COL</span></a>
        <ul class="nav-links">
          <li><a href="/{locale}/about.html">{about_label}</a></li>
          <li><a href="/{locale}/privacy.html">{privacy_label}</a></li>
        </ul>
      </div>
    </div>
  </nav>
  <main class="country-page">
    <section class="hero" id="inicio">
      <div class="container">
        <div class="hero-content">
          <div class="hero-badge"><span class="dot"></span> {badge}</div>
          <h1 class="hero-title">{heading}</h1>
          <p class="hero-desc">{intro}</p>
        </div>
      </div>
    </section>
    <section class="services" id="paises">
      <div class="container">
        <div class="section-header">
          <div class="section-label">{section_label}</div>
          <h2 class="section-title">{section_title}</h2>
        </div>
        <div class="country-city-grid">
{chr(10).join(cards)}
        </div>
      </div>
    </section>
  </main>
  <script>
    (function () {{
      const locale = "{locale}";
      const defaultCountry = "{slugify(default_country)}";
      const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      const country = timeZone.includes("Bogota") ? "colombia" : defaultCountry;
      window.location.replace(`/${{locale}}/${{country}}/`);
    }})();
  </script>
</body>
</html>
"""


def move_country_social_assets(html_dir, country):
    assets_dir = html_dir / "assets"
    default_assets = html_dir / country_default_locale(country) / slugify(country) / "assets"
    default_assets.mkdir(parents=True, exist_ok=True)

    for path in assets_dir.glob("social-card*"):
        target = default_assets / path.name
        if target.exists():
            target.unlink()
        shutil.move(str(path), str(target))

    legacy_assets = html_dir / slugify(country) / "assets"
    if legacy_assets.exists():
        for path in legacy_assets.glob("social-card*"):
            target = default_assets / path.name
            if target.exists():
                target.unlink()
            shutil.move(str(path), str(target))

    for locale in LOCALES:
        locale_assets = html_dir / locale / slugify(country) / "assets"
        locale_assets.mkdir(parents=True, exist_ok=True)
        for path in default_assets.glob("social-card*"):
            target = locale_assets / path.name
            if target.resolve() == path.resolve():
                continue
            shutil.copy2(path, target)


def remove_legacy_city_dirs(html_dir, countries):
    protected = {
        "assets",
        *LOCALES,
    }

    for path in html_dir.iterdir():
        if path.is_dir() and path.name not in protected:
            shutil.rmtree(path)


def remove_default_country_city_dirs(country_dir):
    if not country_dir.exists():
        return

    for path in country_dir.iterdir():
        if path.is_dir():
            shutil.rmtree(path)


def generate_pages(html_dir=HTML_DIR):
    result = read_result(html_dir)
    countries = grouped_by_country(result)

    for country, cities in countries.items():
        template = read_template(html_dir, country)
        move_country_social_assets(html_dir, country)

        for locale in LOCALES:
            country_dir = html_dir / locale / slugify(country)
            country_dir.mkdir(parents=True, exist_ok=True)

            landing_html = country_landing_html(country, cities, locale)
            write_text_file(country_dir / "index.html", landing_html)

            for city in sorted(cities):
                city_dir = country_dir / slugify(city)
                write_text_file(city_dir / "index.html", city_page_html(template, country, city, locale))

    remove_legacy_city_dirs(html_dir, countries.keys())
    write_text_file(html_dir / "countries.json", countries_json(country_records(countries.keys())))
    write_text_file(html_dir / "translations.json", translations_json())
    write_text_file(html_dir / "index.html", root_country_index_html(countries))
    for locale in LOCALES:
        write_text_file(html_dir / locale / "index.html", locale_index_html(locale, countries))

    return sum(len(cities) for cities in countries.values()) * len(LOCALES)


def main():
    count = generate_pages(HTML_DIR)
    print(f"Generated {count} country-scoped city pages")


if __name__ == "__main__":
    main()
