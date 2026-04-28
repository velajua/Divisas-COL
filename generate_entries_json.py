import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path


DEFAULT_ENTRY_HASHTAGS = [
    "#DivisasCOL",
    "#DolarColombia",
    "#PesoColombiano",
    "#MercadoCambiario",
    "#FinanzasPersonales",
]

HASHTAG_STOPWORDS = {
    "actual",
    "alta",
    "altas",
    "ante",
    "bajo",
    "como",
    "con",
    "contra",
    "del",
    "desde",
    "dia",
    "donde",
    "entre",
    "esta",
    "este",
    "estos",
    "impacto",
    "las",
    "los",
    "mas",
    "para",
    "por",
    "que",
    "sobre",
    "sus",
    "una",
}

MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_hashtag(value):
    text = strip_accents(str(value or "").strip())
    text = re.sub(r"^#+", "", text)
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not words:
        return ""
    return "#" + "".join(word[:1].upper() + word[1:] for word in words)


def unique_hashtags(values, limit=20):
    hashtags = []
    seen = set()
    for value in values:
        hashtag = normalize_hashtag(value)
        if not hashtag:
            continue
        key = hashtag.lower()
        if key in seen:
            continue
        hashtags.append(hashtag)
        seen.add(key)
        if len(hashtags) >= limit:
            break
    return hashtags


def extract_meta_keywords(html):
    content = extract(
        r'<meta\s+name=["\']keywords["\']\s+content=["\'](.*?)["\']\s*/?>',
        html,
        "",
    )
    if not content:
        return []
    return [item.strip() for item in content.split(",") if item.strip()]


def extract_article_tags(html):
    return re.findall(
        r'<meta\s+property=["\']article:tag["\']\s+content=["\'](.*?)["\']\s*/?>',
        html,
        re.IGNORECASE,
    )


def content_hashtag_candidates(*values):
    text = strip_accents(" ".join(str(value or "") for value in values)).lower()
    candidates = []
    for word in re.findall(r"[a-z0-9]{4,}", text):
        if word in HASHTAG_STOPWORDS:
            continue
        candidates.append(word)
    return candidates


def build_hashtags(title, description, html):
    editorial_tags = [
        "#AnalisisEconomico",
        "#NoticiasColombia",
    ]
    source_tags = extract_article_tags(html) + extract_meta_keywords(html)
    topic_tags = content_hashtag_candidates(title, description)
    return unique_hashtags(DEFAULT_ENTRY_HASHTAGS + editorial_tags + source_tags + topic_tags)


def extract(pattern, text, default=""):
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else default


def clean_html(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_spanish_date(date_text):
    value = (date_text or "").strip().lower()
    match = re.match(r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", value)
    if not match:
        return datetime.min

    day = int(match.group(1))
    month_txt = (
        match.group(2)
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )[:3]
    year = int(match.group(3))

    month = MONTHS.get(month_txt)
    if not month:
        return datetime.min

    return datetime(year, month, day)


def build_entry(path):
    html = path.read_text(encoding="utf-8")

    title = extract(r"<title>(.*?)</title>", html, path.stem)
    description = extract(
        r'<meta\s+name="description"\s+content="(.*?)"\s*/?>',
        html,
        "",
    )
    date = extract(
        r'<div class="hero-badge"><span class="dot"></span>\s*(.*?)\s*</div>',
        html,
        "",
    )

    if not description:
        first_desc = extract(r'<p class="hero-desc"[^>]*>(.*?)</p>', html, "")
        description = clean_html(first_desc)

    title = clean_html(title).replace(" | Divisas COL", "").strip()

    return {
        "date": date,
        "title": title,
        "summary": description,
        "hashtags": build_hashtags(title, description, html),
        "url": f"entries/{path.name}",
        "_sort_date": parse_spanish_date(date),
    }


def generate_entries_json(entries_dir, output_file):
    entries = []

    if entries_dir.is_dir():
        for path in sorted(entries_dir.glob("*.html")):
            entries.append(build_entry(path))

    entries.sort(key=lambda entry: (entry["url"], entry["title"], entry["summary"]))
    entries.sort(key=lambda entry: entry["_sort_date"], reverse=True)

    for entry in entries:
        entry.pop("_sort_date", None)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="\r\n") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write("\r\n")

    return len(entries)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate html/entries.json from HTML files in html/entries."
    )
    parser.add_argument(
        "--entries-dir",
        default="html/entries",
        type=Path,
        help="Directory containing entry HTML files.",
    )
    parser.add_argument(
        "--output",
        default="html/entries.json",
        type=Path,
        help="Path to write the generated JSON file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    count = generate_entries_json(args.entries_dir, args.output)
    print(f"Generated {args.output} with {count} entries")


if __name__ == "__main__":
    main()
