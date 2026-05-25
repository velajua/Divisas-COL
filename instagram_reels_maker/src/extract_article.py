import json
import re
from pathlib import Path
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_select_text(parent, selector: str) -> str:
    element = parent.select_one(selector)
    if element is None:
        return ""
    return clean_text(element.get_text(" "))


def extract_article(html_path: str | Path) -> dict:
    html_path = Path(html_path)
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    article = {
        "source_file": str(html_path),
        "meta_title": safe_select_text(soup, "title"),
        "date": safe_select_text(soup, ".hero-badge"),
        "title": safe_select_text(soup, ".hero-title"),
        "intro": safe_select_text(soup, ".hero-content .hero-desc"),
        "section_label": safe_select_text(soup, ".section-label"),
        "section_title": safe_select_text(soup, ".section-title"),
        "section_desc": safe_select_text(soup, ".section-desc"),
        "cards": [],
        "final_paragraphs": [],
    }

    services = soup.select_one(".services")

    if services is not None:
        for card in services.select(".summary-card"):
            rows = []

            for row in card.select(".summary-row"):
                strong = safe_select_text(row, "strong")
                full = clean_text(row.get_text(" "))

                if strong and full.startswith(strong):
                    body = full[len(strong):].strip()
                    rows.append({"heading": strong, "text": body})
                else:
                    rows.append({"heading": "", "text": full})

            article["cards"].append(
                {
                    "title": safe_select_text(card, ".summary-title"),
                    "chip": safe_select_text(card, ".summary-chip"),
                    "rows": rows,
                }
            )

        summary_grid = services.select_one(".summary-grid")

        if summary_grid is not None:
            for sibling in summary_grid.find_next_siblings("div"):
                for paragraph in sibling.select("p.hero-desc"):
                    text = clean_text(paragraph.get_text(" "))
                    if text:
                        article["final_paragraphs"].append(text)

    return article


def save_article_json(article: dict, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.write_text(
        json.dumps(article, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
