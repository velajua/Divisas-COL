from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
DOMAIN_FILE = ROOT / "domain_name.txt"

LOCALE_DIRS = {"es", "en"}
DEFAULT_COUNTRY_ROUTE = "/es/colombia/"


def read_base_url():
    base_url = DOMAIN_FILE.read_text(encoding="utf-8").strip().rstrip("/")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("domain_name.txt must start with https:// or http://")
    return base_url


def page_url(base_url, route):
    if route == "/":
        return f"{base_url}/"
    return f"{base_url}{route}"


def replace_or_insert_head_tag(html, pattern, replacement):
    if re.search(pattern, html, flags=re.IGNORECASE):
        return re.sub(pattern, replacement, html, count=1, flags=re.IGNORECASE)
    return html.replace("</head>", f"  {replacement}\n</head>", 1)


def write_text_file(path, content):
    path.write_text(content, encoding="utf-8", newline="\r\n")


def update_html_url_tags(path, url):
    html = path.read_text(encoding="utf-8")
    html = replace_or_insert_head_tag(
        html,
        r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>',
        f'<link rel="canonical" href="{url}">',
    )
    html = replace_or_insert_head_tag(
        html,
        r'<meta\s+property="og:url"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:url" content="{url}">',
    )
    write_text_file(path, html)


def has_locale_dirs(html_dir):
    return any((html_dir / locale).is_dir() for locale in LOCALE_DIRS)


def iter_country_roots(html_dir):
    if has_locale_dirs(html_dir):
        for locale_path in sorted(path for path in html_dir.iterdir() if path.is_dir() and path.name in LOCALE_DIRS):
            for country_path in sorted(path for path in locale_path.iterdir() if path.is_dir()):
                yield locale_path.name, country_path
        return

    for country_path in sorted(html_dir.iterdir()):
        if country_path.is_dir() and country_path.name not in {"assets", "entries"}:
            yield None, country_path


def route_parts(locale, country_path, child=None):
    prefix = f"{locale}/" if locale else ""
    filename = f"{prefix}{country_path.name}"
    route = f"/{prefix}{country_path.name}/"

    if child:
        filename = f"{filename}/{child.name}"
        route = f"{route}{child.name}/"

    return filename, route


def city_routes(html_dir=HTML_DIR):
    routes = []
    for locale, country_path in iter_country_roots(html_dir):
        if (country_path / "index.html").exists():
            filename, route = route_parts(locale, country_path)
            routes.append((f"{filename}/index.html", route, "daily", "1.0"))

        for city_path in sorted(country_path.iterdir()):
            if not city_path.is_dir() or city_path.name in {"assets", "entries", "newsletter"}:
                continue
            if (city_path / "index.html").exists():
                filename, route = route_parts(locale, country_path, city_path)
                routes.append((f"{filename}/index.html", route, "daily", "0.9"))
    return routes


def static_routes(html_dir=HTML_DIR):
    routes = []
    for locale in sorted(LOCALE_DIRS):
        for filename, changefreq, priority in [
            ("about.html", "monthly", "0.7"),
            ("privacy.html", "monthly", "0.6"),
            ("404.html", "monthly", "0.3"),
        ]:
            if (html_dir / locale / filename).exists():
                routes.append((f"{locale}/{filename}", f"/{locale}/{filename}", changefreq, priority))

    for locale, country_path in iter_country_roots(html_dir):
        newsletter = country_path / "newsletter" / "index.html"
        if country_path.is_dir() and newsletter.exists():
            filename, route = route_parts(locale, country_path, country_path / "newsletter")
            routes.append((f"{filename}/index.html", route, "weekly", "0.8"))
    return routes


def entry_routes(html_dir=HTML_DIR):
    routes = []
    for locale, country_path in iter_country_roots(html_dir):
        entries_dir = country_path / "entries"
        if not country_path.is_dir() or not entries_dir.exists():
            continue
        routes.extend(
            (
                f"{(locale + '/') if locale else ''}{country_path.name}/entries/{path.name}",
                f"/{(locale + '/') if locale else ''}{country_path.name}/entries/{path.name}",
                "monthly",
                "0.7",
            )
            for path in sorted(entries_dir.glob("*.html"))
        )
    return routes


def write_robots(base_url):
    write_text_file(
        HTML_DIR / "robots.txt",
        f"User-agent: *\n"
        f"Allow: /\n\n"
        f"Sitemap: {base_url}/sitemap.xml\n",
    )


def write_sitemap(base_url, pages):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for _, route, changefreq, priority in pages:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{page_url(base_url, route)}</loc>",
                f"    <changefreq>{changefreq}</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )

    lines.append("</urlset>")
    write_text_file(HTML_DIR / "sitemap.xml", "\n".join(lines) + "\n")


def main():
    base_url = read_base_url()
    pages = city_routes() + static_routes() + entry_routes()

    for filename, route, _, _ in pages:
        path = HTML_DIR / filename
        if path.exists():
            update_html_url_tags(path, page_url(base_url, route))

    root_index = HTML_DIR / "index.html"
    if root_index.exists():
        update_html_url_tags(root_index, page_url(base_url, "/"))

    for locale in sorted(LOCALE_DIRS):
        locale_index = HTML_DIR / locale / "index.html"
        if locale_index.exists():
            update_html_url_tags(locale_index, page_url(base_url, f"/{locale}/"))

    write_robots(base_url)
    write_sitemap(base_url, pages)
    print(f"Updated site domain metadata for {base_url}")


if __name__ == "__main__":
    main()
