from pathlib import Path
import json
import re


REQUIRED_INDEXABLE = [
    "<title>",
    'name="description"',
    'name="robots"',
    'rel="canonical"',
    'rel="icon"',
    'rel="apple-touch-icon"',
    'property="og:title"',
    'property="og:description"',
    'property="og:url"',
    'property="og:image"',
    'name="twitter:card"',
    'name="twitter:title"',
    'name="twitter:description"',
    'name="twitter:image"',
    "application/ld+json",
]

REQUIRED_REDIRECT_OR_ERROR = [
    "<title>",
    'name="description"',
    'name="robots"',
    'rel="canonical"',
    'rel="icon"',
]


def head_of(text):
    return text.split("</head>", 1)[0] if "</head>" in text else text


def is_indexable(head):
    return 'name="robots" content="noindex' not in head.lower()


def json_ld_ok(head):
    marker = "application/ld+json"
    if marker not in head:
        return False
    try:
        i = head.index(marker)
        start = head.index(">", i) + 1
        end = head.index("</script>", start)
        json.loads(head[start:end])
        return True
    except Exception:
        return False


def main():
    failures = []
    sitemap_path = Path("html/sitemap.xml")
    sitemap_urls = set()
    if sitemap_path.exists():
        sitemap_urls = set(re.findall(r"<loc>(.*?)</loc>", sitemap_path.read_text(encoding="utf-8")))
    indexable_canonicals = []

    for path in sorted(Path("html").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        head = head_of(text)
        lowered = head.lower()
        required = REQUIRED_INDEXABLE if is_indexable(head) else REQUIRED_REDIRECT_OR_ERROR
        missing = [tag for tag in required if tag.lower() not in lowered]
        if not text.lstrip().lower().startswith("<!doctype html>"):
            missing.append("<!DOCTYPE html>")
        if '<html lang="es"' not in text.lower():
            missing.append('html lang="es"')
        if is_indexable(head) and "<h1" not in text.lower():
            missing.append("<h1>")
        if "application/ld+json" in required and not json_ld_ok(head):
            missing.append("valid JSON-LD")
        if "DiviSAS" in text:
            missing.append("stale DiviSAS casing")
        canonical = re.search(r'<link rel="canonical" href="(.*?)"', head)
        if canonical and is_indexable(head):
            indexable_canonicals.append(canonical.group(1))
        status = "OK" if not missing else "MISSING " + ", ".join(missing)
        print(f"{path}: {status}")
        if missing:
            failures.append(path)

    missing_from_sitemap = sorted(set(indexable_canonicals) - sitemap_urls)
    sitemap_only = sorted(sitemap_urls - set(indexable_canonicals))
    if missing_from_sitemap:
        print("sitemap: MISSING " + ", ".join(missing_from_sitemap))
        failures.append(sitemap_path)
    elif sitemap_only:
        print("sitemap: EXTRA " + ", ".join(sitemap_only))
    else:
        print("sitemap: OK")

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
