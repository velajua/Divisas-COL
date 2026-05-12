import re
from pathlib import Path


def normalize_for_voice(text: str) -> str:
    text = text or ""

    replacements = {
        "US$": "dólares ",
        "%": " por ciento",
        "BanRep": "Banco de la República",
        "spot": "al contado",
        "72": "setenta y dos",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_voiceover_script(article: dict, mode: str = "full") -> str:
    lines = []

    title = normalize_for_voice(article.get("title", ""))
    intro = normalize_for_voice(article.get("intro", ""))

    if title:
        lines.append(title)
        lines.append("")

    if intro:
        lines.append(intro)
        lines.append("")

    section_title = normalize_for_voice(article.get("section_title", ""))
    section_desc = normalize_for_voice(article.get("section_desc", ""))

    if section_title:
        lines.append(section_title)

    if section_desc:
        lines.append(section_desc)

    if section_title or section_desc:
        lines.append("")

    cards = article.get("cards", [])

    for index, card in enumerate(cards, start=1):
        card_title = normalize_for_voice(card.get("title", ""))
        chip = normalize_for_voice(card.get("chip", ""))

        if card_title:
            lines.append(f"Señal número {index}: {card_title}.")

        if chip:
            lines.append(f"El tema central es: {chip}.")

        rows = card.get("rows", [])

        if mode == "short":
            rows = rows[:1]

        for row in rows:
            heading = normalize_for_voice(row.get("heading", ""))
            text = normalize_for_voice(row.get("text", ""))

            if heading and text:
                lines.append(f"{heading}. {text}")
            elif text:
                lines.append(text)

        lines.append("")

    final_paragraphs = article.get("final_paragraphs", [])

    if final_paragraphs:
        lines.append("En conclusión:")

        for paragraph in final_paragraphs:
            lines.append(normalize_for_voice(paragraph))

    script = "\n".join(lines)
    script = re.sub(r"\n{3,}", "\n\n", script)
    return script.strip()


def split_script_into_chunks(script: str, max_chars: int = 220) -> list[str]:
    import re

    sentences = re.split(r"(?<=[.!?¿¡:;])\s+", script.replace("\n", " "))
    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            parts = re.split(r"(?<=[,;:])\s+", sentence)
            for part in parts:
                part = part.strip()
                if not part:
                    continue

                if current and len(current) + 1 + len(part) > max_chars:
                    chunks.append(current)
                    current = part
                else:
                    current = f"{current} {part}".strip()
            continue

        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks


def save_text(text: str, output_path: str | Path) -> None:
    Path(output_path).write_text(text, encoding="utf-8")
