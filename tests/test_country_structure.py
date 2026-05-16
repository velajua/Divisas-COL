import json
import tempfile
import unittest
from pathlib import Path

import generate_city_pages
import generate_entries_json
import helpers
import main
import update_site_domain


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
            country_index = (html_dir / "colombia" / "index.html").read_text(encoding="utf-8")
            city_index = (html_dir / "colombia" / "bogota" / "index.html").read_text(encoding="utf-8")

            self.assertIn("url=/colombia/", root_index)
            self.assertIn("window.location.replace(\"/colombia/\")", root_index)
            self.assertNotIn("url=/bogota/", root_index)
            self.assertNotIn("window.location.replace(\"/bogota/\")", root_index)
            self.assertIn('class="nav"', country_index)
            self.assertIn('class="container"', country_index)
            self.assertIn('class="section-header"', country_index)
            self.assertIn('class="footer"', country_index)
            self.assertIn("Comparador de casas de cambio en Colombia", country_index)
            self.assertIn('href="../about.html"', country_index)
            self.assertIn('href="../privacy.html"', country_index)
            self.assertIn("Casas de cambio por ciudad", country_index)
            self.assertIn("/colombia/bogota/", country_index)
            self.assertIn("PuntoDollar Unicentro", country_index)
            self.assertIn('href="../../aurum-gold.css"', city_index)
            self.assertIn('src="../../aurum-script.js"', city_index)
            self.assertIn("https://divisascol.com/colombia/bogota/", city_index)
            self.assertTrue((html_dir / "colombia" / "assets" / "social-card.png").exists())
            self.assertTrue((html_dir / "assets" / "logo.svg").exists())
            self.assertFalse((html_dir / "assets" / "social-card.png").exists())
            self.assertFalse((html_dir / "entries").exists())


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


class CountryEntriesTests(unittest.TestCase):
    def test_entries_json_urls_include_country_prefix(self):
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
    def test_newsletter_capture_payload_includes_country(self):
        script = (Path("html") / "newsletter-capture.js").read_text(encoding="utf-8")
        newsletter = (Path("html") / "colombia" / "newsletter" / "index.html").read_text(encoding="utf-8")

        self.assertIn('data-country="colombia"', newsletter)
        self.assertIn("country: context.country", script)
        self.assertIn("document.documentElement.dataset.country", script)

    def test_global_about_page_is_country_neutral(self):
        about = (Path("html") / "about.html").read_text(encoding="utf-8")

        self.assertNotIn("Colombia", about)
        self.assertNotIn("/colombia/assets/", about)
        self.assertIn("por país, ciudad, moneda y sede", about)


if __name__ == "__main__":
    unittest.main()
