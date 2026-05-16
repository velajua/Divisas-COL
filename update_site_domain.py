from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
DOMAIN_FILE = ROOT / "domain_name.txt"

STATIC_PAGES = [
    ("about.html", "/about.html", "monthly", "0.7"),
    ("privacy.html", "/privacy.html", "monthly", "0.6"),
]
DEFAULT_COUNTRY_ROUTE = "/colombia/"


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


def city_routes(html_dir=HTML_DIR):
    routes = []
    for country_path in sorted(html_dir.iterdir()):
        if not country_path.is_dir() or country_path.name in {"assets", "entries"}:
            continue
        if (country_path / "index.html").exists():
            routes.append((f"{country_path.name}/index.html", f"/{country_path.name}/", "daily", "1.0"))

        for city_path in sorted(country_path.iterdir()):
            if not city_path.is_dir() or city_path.name in {"assets", "entries", "newsletter"}:
                continue
            if (city_path / "index.html").exists():
                routes.append((f"{country_path.name}/{city_path.name}/index.html", f"/{country_path.name}/{city_path.name}/", "daily", "0.9"))
    return routes


def static_routes(html_dir=HTML_DIR):
    routes = []
    for country_path in sorted(html_dir.iterdir()):
        newsletter = country_path / "newsletter" / "index.html"
        if country_path.is_dir() and newsletter.exists():
            routes.append((f"{country_path.name}/newsletter/index.html", f"/{country_path.name}/newsletter/", "weekly", "0.8"))
    return routes


def entry_routes(html_dir=HTML_DIR):
    routes = []
    for country_path in sorted(html_dir.iterdir()):
        entries_dir = country_path / "entries"
        if not country_path.is_dir() or not entries_dir.exists():
            continue
        routes.extend(
            (f"{country_path.name}/entries/{path.name}", f"/{country_path.name}/entries/{path.name}", "monthly", "0.7")
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
    pages = city_routes() + static_routes() + STATIC_PAGES + entry_routes()

    for filename, route, _, _ in pages:
        path = HTML_DIR / filename
        if path.exists():
            update_html_url_tags(path, page_url(base_url, route))

    not_found = HTML_DIR / "404.html"
    if not_found.exists():
        update_html_url_tags(not_found, page_url(base_url, "/404.html"))

    root_index = HTML_DIR / "index.html"
    if root_index.exists():
        update_html_url_tags(root_index, page_url(base_url, DEFAULT_COUNTRY_ROUTE))

    write_robots(base_url)
    write_sitemap(base_url, pages)
    print(f"Updated site domain metadata for {base_url}")


if __name__ == "__main__":
    main()
