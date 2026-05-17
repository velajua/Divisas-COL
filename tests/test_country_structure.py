import json
import tempfile
import unittest
from pathlib import Path

import generate_city_pages
import generate_entries_json
import helpers
import main
import update_site_domain


ADSENSE_SCRIPT = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8147047207612128"
ADSENSE_ACCOUNT_META = '<meta name="google-adsense-account" content="ca-pub-8147047207612128">'


class CountryConfigTests(unittest.TestCase):
    def test_iter_scraper_configs_reads_country_city_url_specs(self):
        conf = {
            "function_dicto": {
                "colombia": {
                    "Bogotá": {
                        "https://example.com/bogota": {
                            "fn": "puntoDollar",
                            "args": "Unicentro",
                        }
                    }
                }
            }
        }

        configs = list(helpers.iter_scraper_configs(conf))

        self.assertEqual(
            configs,
            [
                (
                    "colombia",
                    "Bogotá",
                    "https://example.com/bogota",
                    {"fn": "puntoDollar", "args": "Unicentro"},
                )
            ],
        )

    def test_group_by_country_city_keeps_country_as_parent_key(self):
        rows = [
            {
                "country": "colombia",
                "city": "Bogotá",
                "exchange_house": "puntoDollar",
                "data": {},
            }
        ]

        grouped = helpers._group_by_country_city(rows)

        self.assertEqual(rows, grouped["colombia"]["Bogotá"]["puntoDollar"])


class CountryPageGenerationTests(unittest.TestCase):
    def test_generates_country_landing_and_nested_city_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            html_dir = Path(temp_dir) / "html"
            (html_dir / "bogota").mkdir(parents=True)
            (html_dir / "assets").mkdir()
            (html_dir / "assets" / "logo.svg").write_text("<svg></svg>", encoding="utf-8")
            (html_dir / "assets" / "logo_png.png").write_text("png", encoding="utf-8")
            (html_dir / "assets" / "social-card.png").write_text("card", encoding="utf-8")
            (html_dir / "assets" / "social-card2.png").write_text("card2", encoding="utf-8")
            (html_dir / "assets" / "social-card3.png").write_text("card3", encoding="utf-8")
            (html_dir / "index.html").write_text(
                """<!DOCTYPE html>
<html lang="es" data-city="Bogotá">
<head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="aurum-gold.css">
</head>
<body>
<a href="newsletter.html">Newsletter</a>
<h1 class="hero-title">Tasas de cambio en <span class="gold" id="heroCityName">Bogotá</span></h1>
<p class="hero-desc" style="margin-bottom: 20px;">Old intro</p>
<script src="aurum-script.js"></script>
</body>
</html>
""",
                encoding="utf-8",
            )
            (html_dir / "result.json").write_text(
                json.dumps(
                    {
                        "countries": {
                            "colombia": {
                                "Bogotá": {
                                    "puntoDollar": [
                                        {
                                            "id": "PuntoDollar Unicentro",
                                            "url": "https://example.com",
                                            "rates": {
                                                "AmericanDollar": {
                                                    "label": "Dólar",
                                                    "buy": "4000",
                                                    "sell": "4100",
                                                }
                                            },
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            generate_city_pages.generate_pages(html_dir)

            root_index = (html_dir / "index.html").read_text(encoding="utf-8")
            es_index = (html_dir / "es" / "index.html").read_text(encoding="utf-8")
            en_index = (html_dir / "en" / "index.html").read_text(encoding="utf-8")
            country_index = (html_dir / "es" / "colombia" / "index.html").read_text(encoding="utf-8")
            city_index = (html_dir / "es" / "colombia" / "bogota" / "index.html").read_text(encoding="utf-8")

            self.assertIn("navigator.languages", root_index)
            self.assertIn(ADSENSE_SCRIPT, root_index)
            self.assertIn(ADSENSE_SCRIPT, es_index)
            self.assertIn(ADSENSE_SCRIPT, en_index)
            self.assertIn(ADSENSE_SCRIPT, country_index)
            self.assertIn(ADSENSE_SCRIPT, city_index)
            self.assertIn(ADSENSE_ACCOUNT_META, root_index)
            self.assertIn(ADSENSE_ACCOUNT_META, es_index)
            self.assertIn(ADSENSE_ACCOUNT_META, en_index)
            self.assertIn(ADSENSE_ACCOUNT_META, country_index)
            self.assertIn(ADSENSE_ACCOUNT_META, city_index)
            self.assertIn('const defaultCountry = "colombia";', root_index)
            self.assertIn("window.location.replace(`/${locale}/${country}/`)", root_index)
            self.assertIn('const locale = "es";', es_index)
            self.assertIn("window.location.replace(`/${locale}/${country}/`)", es_index)
            self.assertIn('const locale = "en";', en_index)
            self.assertIn("window.location.replace(`/${locale}/${country}/`)", en_index)
            self.assertNotIn("url=/bogota/", root_index)
            self.assertNotIn("window.location.replace(\"/bogota/\")", root_index)
            self.assertFalse((html_dir / "colombia").exists())
            self.assertIn('class="nav"', country_index)
            self.assertIn('class="container"', country_index)
            self.assertIn('class="section-header"', country_index)
            self.assertIn('class="footer"', country_index)
            self.assertIn("Comparador de casas de cambio en Colombia", country_index)
            self.assertIn('href="../about.html"', country_index)
            self.assertIn('href="../privacy.html"', country_index)
            self.assertIn("Casas de cambio por ciudad", country_index)
            self.assertIn("/es/colombia/bogota/", country_index)
            self.assertIn("PuntoDollar Unicentro", country_index)
            self.assertIn('href="../../../aurum-gold.css"', city_index)
            self.assertIn('src="../../../aurum-script.js"', city_index)
            self.assertIn("https://divisascol.com/es/colombia/bogota/", city_index)
            self.assertIn('id="languageSelector"', city_index)
            self.assertTrue((html_dir / "es" / "colombia" / "assets" / "social-card.png").exists())
            self.assertTrue((html_dir / "en" / "colombia" / "assets" / "social-card.png").exists())
            self.assertTrue((html_dir / "assets" / "logo.svg").exists())
            self.assertFalse((html_dir / "assets" / "social-card.png").exists())
            self.assertFalse((html_dir / "entries").exists())

    def test_generates_countries_json_and_country_landing_selector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            html_dir = Path(temp_dir) / "html"
            (html_dir / "bogota").mkdir(parents=True)
            (html_dir / "assets").mkdir()
            (html_dir / "assets" / "social-card.png").write_text("card", encoding="utf-8")
            (html_dir / "index.html").write_text(
                """<!DOCTYPE html>
<html lang="es" data-city="Bogotá">
<head>
<link rel="preconnect" href="https://fonts.googleapis.com">
</head>
<body>
<h1 class="hero-title">Tasas de cambio en <span class="gold" id="heroCityName">Bogotá</span></h1>
<p class="hero-desc" style="margin-bottom: 20px;">Old intro</p>
</body>
</html>
""",
                encoding="utf-8",
            )
            (html_dir / "result.json").write_text(
                json.dumps(
                    {
                        "countries": {
                            "colombia": {
                                "Bogotá": {
                                    "puntoDollar": [
                                        {
                                            "id": "PuntoDollar Unicentro",
                                            "url": "https://example.com",
                                            "rates": {
                                                "AmericanDollar": {
                                                    "label": "Dólar",
                                                    "buy": "4000",
                                                    "sell": "4100",
                                                }
                                            },
                                        }
                                    ]
                                }
                            },
                            "peru": {
                                "Lima": {
                                    "casaCambio": [
                                        {
                                            "id": "Casa Cambio Lima",
                                            "url": "https://example.pe",
                                            "rates": {
                                                "AmericanDollar": {
                                                    "label": "Dólar",
                                                    "buy": "3.7",
                                                    "sell": "3.8",
                                                }
                                            },
                                        }
                                    ]
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            generate_city_pages.generate_pages(html_dir)

            countries = json.loads((html_dir / "countries.json").read_text(encoding="utf-8"))
            self.assertEqual(
                countries,
                [
                    {"slug": "colombia", "name": "Colombia", "url": "/es/colombia/"},
                    {"slug": "peru", "name": "Peru", "url": "/es/peru/"},
                ],
            )
            country_index = (html_dir / "es" / "colombia" / "index.html").read_text(encoding="utf-8")
            self.assertIn('<select id="countrySelector"', country_index)
            self.assertIn('<option value="/es/colombia/" selected>Colombia</option>', country_index)
            self.assertIn('fetch("/countries.json"', country_index)
            self.assertNotIn('"assets"', (html_dir / "countries.json").read_text(encoding="utf-8"))

    def test_generates_language_prefixed_pages_and_country_default_redirect(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            html_dir = Path(temp_dir) / "html"
            (html_dir / "bogota").mkdir(parents=True)
            (html_dir / "assets").mkdir()
            (html_dir / "assets" / "social-card.png").write_text("card", encoding="utf-8")
            (html_dir / "index.html").write_text(
                """<!DOCTYPE html>
<html lang="es" data-city="Bogotá">
<head>
<link rel="preconnect" href="https://fonts.googleapis.com">
</head>
<body>
<h1 class="hero-title">Tasas de cambio en <span class="gold" id="heroCityName">Bogotá</span></h1>
<p class="hero-desc" style="margin-bottom: 20px;">Old intro</p>
<script src="aurum-script.js"></script>
</body>
</html>
""",
                encoding="utf-8",
            )
            (html_dir / "result.json").write_text(
                json.dumps(
                    {
                        "countries": {
                            "colombia": {
                                "Bogotá": {
                                    "puntoDollar": [
                                        {
                                            "id": "PuntoDollar Unicentro",
                                            "url": "https://example.com",
                                            "rates": {
                                                "AmericanDollar": {
                                                    "label": "Dólar",
                                                    "buy": "4000",
                                                    "sell": "4100",
                                                }
                                            },
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            generate_city_pages.generate_pages(html_dir)
            generate_city_pages.generate_pages(html_dir)

            translations = json.loads((html_dir / "translations.json").read_text(encoding="utf-8"))
            es_country = (html_dir / "es" / "colombia" / "index.html").read_text(encoding="utf-8")
            en_country = (html_dir / "en" / "colombia" / "index.html").read_text(encoding="utf-8")
            en_city = (html_dir / "en" / "colombia" / "bogota" / "index.html").read_text(encoding="utf-8")

            self.assertEqual(translations["countryDefaults"]["colombia"], "es")
            self.assertIn('"code": "en"', (html_dir / "translations.json").read_text(encoding="utf-8"))
            self.assertIn('lang="es" data-locale="es" data-country="colombia"', es_country)
            self.assertIn('lang="en" data-locale="en" data-country="colombia"', en_country)
            self.assertIn('<select id="languageSelector"', es_country)
            self.assertIn('fetch("/translations.json"', es_country)
            self.assertIn('value="/en/colombia/"', es_country)
            self.assertIn('src="../../../aurum-script.js"', en_city)
            self.assertIn('id="languageSelector"', en_city)
            self.assertEqual(en_city.count('id="languageSelector"'), 1)
            self.assertIn("Exchange rates in", en_city)
            self.assertNotIn("Tasas de cambio en", en_city)
            self.assertIn("Exchange houses by city", en_country)
            self.assertNotIn("Casas de cambio por ciudad", en_country)
            self.assertNotIn("Referencia de mercado y casas de cambio", en_city)
            self.assertNotIn("Monedas por casa de cambio", en_city)
            self.assertNotIn("¿Falta una casa de cambio?", en_city)
            self.assertFalse((html_dir / "colombia").exists())


class CountryDomainMetadataTests(unittest.TestCase):
    def test_city_routes_are_nested_under_country(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            html_dir = Path(temp_dir) / "html"
            (html_dir / "colombia" / "bogota").mkdir(parents=True)
            (html_dir / "colombia" / "entries").mkdir(parents=True)
            (html_dir / "colombia" / "newsletter").mkdir(parents=True)
            (html_dir / "colombia" / "bogota" / "index.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "colombia" / "index.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "colombia" / "entries" / "sample.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "colombia" / "newsletter" / "index.html").write_text("<html></html>", encoding="utf-8")

            routes = update_site_domain.city_routes(html_dir)
            entries = update_site_domain.entry_routes(html_dir)
            static_pages = update_site_domain.static_routes(html_dir)

            self.assertIn(("colombia/index.html", "/colombia/", "daily", "1.0"), routes)
            self.assertIn(("colombia/bogota/index.html", "/colombia/bogota/", "daily", "0.9"), routes)
            self.assertIn(("colombia/entries/sample.html", "/colombia/entries/sample.html", "monthly", "0.7"), entries)
            self.assertIn(("colombia/newsletter/index.html", "/colombia/newsletter/", "weekly", "0.8"), static_pages)

    def test_city_routes_use_language_prefixes_when_locale_dirs_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            html_dir = Path(temp_dir) / "html"
            (html_dir / "es" / "colombia" / "bogota").mkdir(parents=True)
            (html_dir / "en" / "colombia" / "bogota").mkdir(parents=True)
            (html_dir / "colombia").mkdir(parents=True)
            (html_dir / "es" / "colombia" / "index.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "en" / "colombia" / "index.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "es" / "colombia" / "bogota" / "index.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "en" / "colombia" / "bogota" / "index.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "es" / "about.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "en" / "about.html").write_text("<html></html>", encoding="utf-8")
            (html_dir / "colombia" / "index.html").write_text("<html></html>", encoding="utf-8")

            routes = update_site_domain.city_routes(html_dir)
            static_pages = update_site_domain.static_routes(html_dir)

            self.assertIn(("es/colombia/index.html", "/es/colombia/", "daily", "1.0"), routes)
            self.assertIn(("en/colombia/index.html", "/en/colombia/", "daily", "1.0"), routes)
            self.assertIn(("es/colombia/bogota/index.html", "/es/colombia/bogota/", "daily", "0.9"), routes)
            self.assertIn(("en/colombia/bogota/index.html", "/en/colombia/bogota/", "daily", "0.9"), routes)
            self.assertIn(("es/about.html", "/es/about.html", "monthly", "0.7"), static_pages)
            self.assertIn(("en/about.html", "/en/about.html", "monthly", "0.7"), static_pages)
            self.assertNotIn(("colombia/index.html", "/colombia/", "daily", "1.0"), routes)


class CountryEntriesTests(unittest.TestCase):
    def test_entries_json_urls_include_locale_and_country_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entries_dir = Path(temp_dir) / "html" / "es" / "colombia" / "entries"
            entries_dir.mkdir(parents=True)
            output_file = entries_dir.parent / "entries.json"
            (entries_dir / "sample.html").write_text(
                """<html>
<head>
  <title>Sample entry | Divisas COL</title>
  <meta name="description" content="Sample description">
</head>
<body>
  <div class="hero-badge"><span class="dot"></span> 1 may 2026</div>
</body>
</html>""",
                encoding="utf-8",
            )

            generate_entries_json.generate_entries_json(entries_dir, output_file)
            entries = json.loads(output_file.read_text(encoding="utf-8"))

            self.assertEqual("es/colombia/entries/sample.html", entries[0]["url"])

    def test_entries_json_can_still_generate_legacy_country_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entries_dir = Path(temp_dir) / "html" / "colombia" / "entries"
            entries_dir.mkdir(parents=True)
            output_file = entries_dir.parent / "entries.json"
            (entries_dir / "sample.html").write_text(
                """<html>
<head>
  <title>Sample entry | Divisas COL</title>
  <meta name="description" content="Sample description">
</head>
<body>
  <div class="hero-badge"><span class="dot"></span> 1 may 2026</div>
</body>
</html>""",
                encoding="utf-8",
            )

            generate_entries_json.generate_entries_json(entries_dir, output_file)
            entries = json.loads(output_file.read_text(encoding="utf-8"))

            self.assertEqual("colombia/entries/sample.html", entries[0]["url"])


class CompactResultTests(unittest.TestCase):
    def test_compact_countries_remove_repeated_parent_fields(self):
        grouped = {
            "colombia": {
                "Bogotá": {
                    "puntoDollar": [
                        {
                            "id": "PuntoDollar Unicentro",
                            "country": "colombia",
                            "city": "Bogotá",
                            "exchange_house": "puntoDollar",
                            "source_url": "https://example.com",
                            "data": {
                                "Dólar": {
                                    "id": "AmericanDollar",
                                    "buy": "4000",
                                    "sell": "4100",
                                }
                            },
                        }
                    ]
                }
            }
        }

        compact = main._compact_countries(grouped)
        location = compact["colombia"]["Bogotá"]["puntoDollar"][0]

        self.assertEqual(
            location,
            {
                "id": "PuntoDollar Unicentro",
                "url": "https://example.com",
                "rates": {
                    "AmericanDollar": {
                        "label": "Dólar",
                        "buy": "4000",
                        "sell": "4100",
                    }
                },
            },
        )
        self.assertNotIn("country", location)
        self.assertNotIn("city", location)
        self.assertNotIn("exchange_house", location)

    def test_generated_result_json_uses_compact_schema(self):
        result = json.loads((Path("html") / "result.json").read_text(encoding="utf-8"))

        self.assertIn("countries", result)
        self.assertNotIn("grouped_by_city", result)
        self.assertNotIn("grouped_by_country", result)
        self.assertNotIn("comparison_data", result)
        self.assertNotIn("comparison_data_by_country", result)


class CountryNewsletterTests(unittest.TestCase):
    def test_ads_txt_contains_google_authorization(self):
        ads_txt = (Path("html") / "ads.txt").read_text(encoding="utf-8").strip()

        self.assertEqual("google.com, pub-8147047207612128, DIRECT, f08c47fec0942fa0", ads_txt)

    def test_html_pages_include_adsense_loader_once(self):
        for path in (Path("html")).rglob("*.html"):
            page = path.read_text(encoding="utf-8")

            self.assertEqual(1, page.count(ADSENSE_SCRIPT), path.as_posix())
            self.assertIn('crossorigin="anonymous"', page, path.as_posix())
            self.assertEqual(1, page.count(ADSENSE_ACCOUNT_META), path.as_posix())

    def test_static_pages_are_language_scoped(self):
        self.assertTrue((Path("html") / "es" / "about.html").exists())
        self.assertTrue((Path("html") / "en" / "about.html").exists())
        self.assertTrue((Path("html") / "es" / "privacy.html").exists())
        self.assertTrue((Path("html") / "en" / "privacy.html").exists())
        self.assertTrue((Path("html") / "es" / "404.html").exists())
        self.assertTrue((Path("html") / "en" / "404.html").exists())
        self.assertFalse((Path("html") / "about.html").exists())
        self.assertFalse((Path("html") / "privacy.html").exists())
        self.assertFalse((Path("html") / "404.html").exists())

    def test_static_about_and_privacy_home_links_use_language_bootstrap(self):
        for locale in ("es", "en"):
            for filename in ("about.html", "privacy.html"):
                page = (Path("html") / locale / filename).read_text(encoding="utf-8")
                self.assertIn(f'href="/{locale}/"', page)
                self.assertNotIn('href="index.html"', page)

    def test_newsletter_capture_payload_includes_country(self):
        script = (Path("html") / "newsletter-capture.js").read_text(encoding="utf-8")
        newsletter = (Path("html") / "es" / "colombia" / "newsletter" / "index.html").read_text(encoding="utf-8")

        self.assertIn('data-country="colombia"', newsletter)
        self.assertIn("country: context.country", script)
        self.assertIn("document.documentElement.dataset.country", script)

    def test_city_shared_scripts_are_locale_aware(self):
        city_script = (Path("html") / "aurum-script.js").read_text(encoding="utf-8")
        newsletter_script = (Path("html") / "newsletter-capture.js").read_text(encoding="utf-8")

        self.assertIn('const candidates = ["/result.json"]', city_script)
        self.assertIn('const languageSelector = document.getElementById("languageSelector")', city_script)
        self.assertIn("window.location.href = languageSelector.value", city_script)
        self.assertIn('locale === "en"', newsletter_script)
        self.assertIn("Want to stay up to date?", newsletter_script)
        self.assertIn("Get rate updates and the newsletter.", newsletter_script)

    def test_generated_city_header_links_and_language_selector(self):
        city = (Path("html") / "en" / "colombia" / "bogota" / "index.html").read_text(encoding="utf-8")

        self.assertIn('href="/en/colombia/" class="logo"', city)
        self.assertNotIn('href="#inicio" class="logo"', city)
        self.assertIn('class="hero-city-selector nav-language-selector"', city)

    def test_global_about_page_is_country_neutral(self):
        about = (Path("html") / "es" / "about.html").read_text(encoding="utf-8")

        self.assertNotIn("Colombia", about)
        self.assertNotIn("/colombia/assets/", about)
        self.assertIn("por país, ciudad, moneda y sede", about)

    def test_generated_english_city_pages_do_not_keep_spanish_ui_copy(self):
        spanish_fragments = [
            "Tasas de cambio",
            "Referencia de mercado",
            "casas de cambio",
            "Monedas por",
            "por casa",
            "Mejor compra",
            "menor venta",
            "Seleccionar",
            "Cargando",
            "Sugerir",
            "Volver",
            "¿Falta",
            "Comparador de",
            "Compra",
            "Venta",
            "Fuente",
            "Ciudad",
            "Moneda",
            "Detalle completo",
            "Vista completa",
            "formulario",
        ]

        for path in (Path("html") / "en" / "colombia").glob("*/index.html"):
            page = path.read_text(encoding="utf-8")
            for fragment in spanish_fragments:
                self.assertNotIn(fragment, page, f"{fragment!r} found in {path}")


if __name__ == "__main__":
    unittest.main()
