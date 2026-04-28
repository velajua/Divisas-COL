import argparse
import json
import re
import textwrap
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unidecode import unidecode
from xml.sax.saxutils import escape


CARD_WIDTH = 1080
CARD_HEIGHT = 1350
BOGOTA_TZ = ZoneInfo("America/Bogota")

MONTHS_ES = {
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

CITY_SLUGS = {
    "Bogotá": "bogota",
    "Medellín": "medellin",
    "Cali": "cali",
    "Barranquilla": "barranquilla",
    "Cartagena": "cartagena",
}

CHEERS_BY_CITY = {
    "Bogotá": "Animo, Bogota.",
    "Medellín": "Animo, Medellin.",
    "Cali": "Arriba ese animo, Cali.",
    "Barranquilla": "Pilas y animo, Barranquilla.",
    "Cartagena": "Animo, Cartagena.",
}

CURRENCY_ORDER = [
    "AmericanDollar",
    "Euro",
    "BritishPound",
    "CanadianDollar",
    "AustralianDollar",
    "MexicanPeso",
    "BrasilianReal",
    "SwissFranc",
    "PeruveanNewSun",
    "ChileanPeso",
    "ArgentineanPeso",
    "JapaneseYen",
    "ChineseYuan",
    "DominicanPeso",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate daily Instagram SVG cards from html/result.json."
    )
    parser.add_argument("--html-dir", default="html", help="Folder containing result.json and entries.json.")
    parser.add_argument("--output-dir", default="instagram_cards", help="Root folder for dated card output.")
    parser.add_argument("--date", help="Run date in YYYY-MM-DD. Defaults to today in Bogota.")
    parser.add_argument("--max-rows", type=int, default=6, help="Currency rows per city card.")
    parser.add_argument(
        "--currencies",
        nargs="*",
        help="Optional currency IDs to include. Defaults to all currencies found, ordered for readability.",
    )
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_rate(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^\d,.-]", "", text)
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        rate = float(text)
    except ValueError:
        return None
    if rate <= 0:
        return None
    return rate


def format_rate(value):
    if value is None:
        return "N/D"
    if value >= 100:
        return f"${value:,.0f}".replace(",", ".")
    if value == int(value):
        return f"${value:,.0f}".replace(",", ".")
    return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def slugify(value):
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
    }
    text = value.lower()
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "card"


def display_place(item):
    source = item.get("exchange_house") or ""
    location = item.get("id") or ""
    if location and location != source:
        return f"{source} ({location})"
    return source or location or "N/D"


def collect_city_rankings(grouped_by_city):
    rankings = {}
    for city, groups in sorted(grouped_by_city.items()):
        currencies = {}
        for exchange_items in groups.values():
            for item in exchange_items:
                place = display_place(item)
                for currency_name, rate_data in item.get("data", {}).items():
                    currency_id = rate_data.get("id") or slugify(currency_name)
                    bucket = currencies.setdefault(
                        currency_id,
                        {"id": currency_id, "name": currency_name, "buy": [], "sell": []},
                    )
                    buy = parse_rate(rate_data.get("buy"))
                    sell = parse_rate(rate_data.get("sell"))
                    if buy is not None:
                        bucket["buy"].append({"place": place, "value": buy})
                    if sell is not None:
                        bucket["sell"].append({"place": place, "value": sell})

        city_rows = []
        for currency in sorted(currencies.values(), key=currency_sort_key):
            best_buy = max(currency["buy"], key=lambda row: row["value"], default=None)
            best_sell = min(currency["sell"], key=lambda row: row["value"], default=None)
            if not best_buy and not best_sell:
                continue
            city_rows.append(
                {
                    "id": currency["id"],
                    "name": currency["name"],
                    "best_buy": best_buy,
                    "best_sell": best_sell,
                    "spread": (
                        best_sell["value"] - best_buy["value"]
                        if best_buy and best_sell
                        else None
                    ),
                }
            )
        rankings[city] = city_rows
    return rankings


def currency_sort_key(row):
    try:
        return (CURRENCY_ORDER.index(row["id"]), row["name"])
    except ValueError:
        return (len(CURRENCY_ORDER), row["name"])


def choose_rows(rows, requested_currency_ids):
    if not requested_currency_ids:
        return rows
    wanted = set(requested_currency_ids)
    return [row for row in rows if row["id"] in wanted]


def chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def currency_label(row):
    text = row["name"].split("(")[0].strip()
    return " ".join([part.capitalize() for part in text.split()])


def load_hashtag_template(repo_root):
    path = repo_root / "hashtag_template.txt"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").strip()


def normalize_hashtag(value):
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    if not text.startswith("#"):
        text = "#" + text
    return text


def parse_hashtags(value):
    if not value:
        return []
    if isinstance(value, str):
        return [normalize_hashtag(item) for item in re.split(r"[\s,]+", value) if item.strip()]
    return [normalize_hashtag(item) for item in value if str(item or "").strip()]


def combine_hashtags(*sources, limit=30):
    hashtags = []
    seen = set()
    for source in sources:
        for hashtag in parse_hashtags(source):
            key = hashtag.lower()
            if key in seen:
                continue
            hashtags.append(hashtag)
            seen.add(key)
            if len(hashtags) >= limit:
                return hashtags
    return hashtags


def hidden_hashtag_block(hashtags):
    if not hashtags:
        return ""
    return "\n\n.\n.\n.\n.\n.\n.\n\n" + " ".join(parse_hashtags(hashtags))


def render_city_description(city, rows, date_label, hashtags):
    buy_rows = [row for row in rows if row.get("best_sell")]
    if not buy_rows:
        body = [
            f"{city} - mejores lugares para comprar divisas hoy ({date_label})",
            "",
            "No encontramos tasas de venta disponibles para esta ciudad en la corrida de hoy.",
        ]
    else:
        body = [
            f"{city} - donde conviene comprar divisas hoy ({date_label})",
            "",
            "Estas son las mejores tasas de venta encontradas para comprar monedas:",
            "",
        ]
        for row in buy_rows[:8]:
            best_sell = row["best_sell"]
            body.append(
                f"- {currency_label(row)}: {format_rate(best_sell['value'])} en {best_sell['place']}"
            )
        if len(buy_rows) > 8:
            body.append(f"- Y {len(buy_rows) - 8} monedas mas en el resumen del dia.")

    body.extend(
        [
            "",
            CHEERS_BY_CITY.get(city, "Animo, que hoy se compra mejor informado."),
            "Fuente: divisascol.com",
        ]
    )
    return "\n".join(body) + hidden_hashtag_block(hashtags)


def render_newsletter_description(entry, date_label, hashtags):
    post_hashtags = combine_hashtags(entry.get("hashtags"), hashtags)
    body = [
        f"Newsletter Divisas COL - {date_label}",
        "",
        entry.get("title", "Analisis cambiario del dia"),
    ]
    summary = str(entry.get("summary") or "").strip()
    if summary:
        body.extend(["", summary])
    body.extend(
        [
            "",
            "Animo, que entender el mercado tambien ayuda a comprar mejor.",
            f"Lee la nota completa: {entry.get('url', 'newsletter.html')}",
        ]
    )
    return "\n".join(body) + hidden_hashtag_block(post_hashtags)


def svg_text(x, y, text, size, weight=500, color="#f8fafc", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif" font-weight="{weight}" '
        f'text-anchor="{anchor}">{escape(str(text))}</text>'
    )


def wrapped_svg_text(x, y, text, width, size, line_height, color="#f8fafc", weight=500):
    max_chars = max(12, int(width / (size * 0.52)))
    lines = textwrap.wrap(str(text), width=max_chars)
    output = []
    for index, line in enumerate(lines):
        output.append(svg_text(x, y + index * line_height, line, size, weight, color))
    return "\n".join(output), len(lines)


def base_svg(title, subtitle, badge):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}">',
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">',
        '<stop offset="0%" stop-color="#0b1220"/>',
        '<stop offset="46%" stop-color="#17324d"/>',
        '<stop offset="100%" stop-color="#0f5132"/>',
        "</linearGradient>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">',
        '<feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#020617" flood-opacity="0.28"/>',
        "</filter>",
        "</defs>",
        '<rect width="1080" height="1350" fill="url(#bg)"/>',
        '<circle cx="950" cy="110" r="170" fill="#d9f99d" opacity="0.14"/>',
        '<circle cx="90" cy="1180" r="240" fill="#38bdf8" opacity="0.10"/>',
        svg_text(72, 102, "DIVISAS COL", 28, 800, "#d9f99d"),
        svg_text(1008, 102, badge, 28, 700, "#bfdbfe", "end"),
        svg_text(72, 185, title, 60, 800, "#ffffff"),
        svg_text(72, 238, subtitle, 30, 500, "#cbd5e1"),
        '<rect x="58" y="290" width="964" height="890" rx="34" fill="#f8fafc" opacity="0.96" filter="url(#shadow)"/>',
    ]


def render_city_card(city, rows, date_label, page, total_pages):
    title = f"{city}: mejores tasas"
    subtitle = f"Compra mas alta y venta mas baja por moneda - {date_label}"
    parts = base_svg(title, subtitle, f"{page}/{total_pages}")
    parts.extend(
        [
            svg_text(100, 360, "Moneda", 26, 800, "#334155"),
            svg_text(420, 360, "Mejor compra", 26, 800, "#166534"),
            svg_text(740, 360, "Mejor venta", 26, 800, "#075985"),
            '<line x1="96" y1="386" x2="984" y2="386" stroke="#cbd5e1" stroke-width="2"/>',
        ]
    )

    y = 456
    for index, row in enumerate(rows):
        if index:
            parts.append(
                f'<line x1="96" y1="{y - 46}" x2="984" y2="{y - 46}" stroke="#e2e8f0" stroke-width="2"/>'
            )
        best_buy = row["best_buy"]
        best_sell = row["best_sell"]
        tmp = row["name"].split('(')[0].strip()
        parts.append(svg_text(100, y, ' '.join([i.capitalize() for i in tmp.split()]), 24, 800, "#0f172a"))
        parts.append(svg_text(100, y + 38, row["id"], 19, 500, "#64748b"))

        parts.append(svg_text(420, y, format_rate(best_buy["value"]) if best_buy else "N/D", 34, 800, "#15803d"))
        buy_place = best_buy["place"] if best_buy else "Sin dato"
        buy_text, _ = wrapped_svg_text(420, y + 38, buy_place, 270, 19, 24, "#475569", 500)
        parts.append(buy_text)

        parts.append(svg_text(740, y, format_rate(best_sell["value"]) if best_sell else "N/D", 34, 800, "#0369a1"))
        sell_place = best_sell["place"] if best_sell else "Sin dato"
        sell_text, _ = wrapped_svg_text(740, y + 38, sell_place, 250, 19, 24, "#475569", 500)
        parts.append(sell_text)

        y += 126

    parts.append(svg_text(72, 1256, f"Fuente: divisascol.com/{unidecode(city.lower())}", 24, 600, "#cbd5e1"))
    parts.append(svg_text(1008, 1256, "@divisascol", 24, 700, "#d9f99d", "end"))
    parts.append("</svg>")
    return "\n".join(parts)


def parse_entry_date(value, year_fallback):
    text = str(value).strip().lower().replace(".", "")
    match = re.match(r"^(\d{1,2})\s+([a-záéíóúñ]{3})\s+(\d{4})$", text)
    if not match:
        return None
    day, month_text, year = match.groups()
    month = MONTHS_ES.get(month_text[:3])
    if not month:
        return None
    return datetime(int(year or year_fallback), month, int(day)).date()


def matching_newsletter(entries, run_date):
    matches = []
    for entry in entries:
        entry_date = parse_entry_date(entry.get("date"), run_date.year)
        if entry_date == run_date:
            matches.append(entry)
    if not matches:
        return None
    return matches[0]


def render_newsletter_card(entry, date_label):
    parts = base_svg("Newsletter de hoy", date_label, "Nuevo")
    title_text, title_lines = wrapped_svg_text(
        100,
        470,
        entry.get("title", "Ultima newsletter"),
        820,
        48,
        58,
        "#0f172a",
        800,
    )
    parts.extend(
        [
            svg_text(100, 390, "Analisis cambiario", 28, 800, "#166534"),
            title_text,
        ]
    )
    summary_y = 470 + title_lines * 58 + 52
    summary, line_count = wrapped_svg_text(
        100,
        summary_y,
        entry.get("summary", ""),
        820,
        34,
        48,
        "#334155",
        500,
    )
    parts.append(summary)
    cta_y = summary_y + line_count * 48 + 90
    parts.extend(
        [
            f'<rect x="100" y="{cta_y}" width="790" height="92" rx="24" fill="#0f5132"/>',
            svg_text(136, cta_y + 58, "Leer en divisascol.com", 32, 800, "#ffffff"),
            svg_text(100, 1088, entry.get("url", "newsletter.html"), 25, 600, "#475569"),
            svg_text(72, 1256, "Opinion y contexto para moverse mejor con el dolar", 24, 600, "#cbd5e1"),
            svg_text(1008, 1256, "@divisascol", 24, 700, "#d9f99d", "end"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def write_card(path, content):
    path.write_text(content, encoding="utf-8", newline="\r\n")


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    html_dir = Path(args.html_dir)
    output_root = Path(args.output_dir)
    if not html_dir.is_absolute():
        html_dir = repo_root / html_dir
    if not output_root.is_absolute():
        output_root = repo_root / output_root
    run_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date
        else datetime.now(BOGOTA_TZ).date()
    )
    date_label = run_date.strftime("%Y-%m-%d")
    day_dir = output_root / date_label
    day_dir.mkdir(parents=True, exist_ok=True)

    result = load_json(html_dir / "result.json")
    entries_path = html_dir / "entries.json"
    entries = load_json(entries_path) if entries_path.exists() else []
    hashtags = load_hashtag_template(repo_root)

    rankings = collect_city_rankings(result.get("grouped_by_city", {}))
    manifest = {
        "date": date_label,
        "generated_at": datetime.now(BOGOTA_TZ).isoformat(timespec="seconds"),
        "source": str((html_dir / "result.json").as_posix()),
        "cards": [],
        "descriptions": [],
        "newsletter": None,
    }

    for city in sorted(rankings):
        rows = rankings[city]
        selected_rows = choose_rows(rows, args.currencies)
        row_groups = list(chunks(selected_rows, max(1, args.max_rows)))
        total_pages = len(row_groups)
        city_slug = CITY_SLUGS.get(city, slugify(city))
        description_path = None
        if selected_rows:
            description_filename = f"{city_slug}-description.txt"
            description_path = str((day_dir / description_filename).as_posix())
            write_card(
                day_dir / description_filename,
                render_city_description(city, selected_rows, date_label, hashtags),
            )
            manifest["descriptions"].append(
                {
                    "type": "city_rates",
                    "city": city,
                    "path": description_path,
                }
            )
        for page, row_group in enumerate(row_groups, start=1):
            filename = f"{city_slug}-{page:02d}.svg"
            write_card(day_dir / filename, render_city_card(city, row_group, date_label, page, total_pages))
            manifest["cards"].append(
                {
                    "type": "city_rates",
                    "city": city,
                    "page": page,
                    "path": str((day_dir / filename).as_posix()),
                    "description_path": description_path,
                    "currencies": [row["id"] for row in row_group],
                }
            )

    newsletter = matching_newsletter(entries, run_date)
    if newsletter:
        newsletter_hashtags = combine_hashtags(newsletter.get("hashtags"), hashtags)
        filename = "newsletter.svg"
        description_filename = "newsletter-description.txt"
        write_card(day_dir / filename, render_newsletter_card(newsletter, date_label))
        write_card(
            day_dir / description_filename,
            render_newsletter_description(newsletter, date_label, hashtags),
        )
        manifest["newsletter"] = {
            "matched": True,
            "title": newsletter.get("title"),
            "date": newsletter.get("date"),
            "path": str((day_dir / filename).as_posix()),
            "description_path": str((day_dir / description_filename).as_posix()),
            "hashtags": newsletter_hashtags,
        }
        manifest["descriptions"].append(
            {
                "type": "newsletter",
                "path": str((day_dir / description_filename).as_posix()),
                "title": newsletter.get("title"),
            }
        )
        manifest["cards"].append(
            {
                "type": "newsletter",
                "path": str((day_dir / filename).as_posix()),
                "description_path": str((day_dir / description_filename).as_posix()),
                "title": newsletter.get("title"),
            }
        )
    else:
        manifest["newsletter"] = {"matched": False}

    manifest_path = day_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\r\n",
        encoding="utf-8",
        newline="\r\n",
    )
    print(f"Generated {len(manifest['cards'])} cards in {day_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
