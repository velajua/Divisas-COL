import re
from pathlib import Path


import re


SYMBOL_REPLACEMENTS = {
    "US$": " dólares ",
    "$": " pesos ",
    "€": " euros ",
    "£": " libras ",
    "¥": " yenes ",
    "%": " por ciento ",
    "&": " y ",
    "@": " arroba ",
    "#": " numeral ",
    "+": " más ",
    "-": " menos ",
    "*": " por ",
    "/": " dividido entre ",
    "\\": " barra invertida ",
    "=": " igual ",
    "<": " menor que ",
    ">": " mayor que ",
    "≤": " menor o igual que ",
    "≥": " mayor o igual que ",
    "±": " más o menos ",
    "≈": " aproximadamente ",
    "°": " grados ",
    "º": " grados ",
    "ª": " a ",
    "™": " marca registrada ",
    "®": " registrado ",
    "©": " copyright ",
    "|": " barra vertical ",
    "_": " guion bajo ",
    "~": " virgulilla ",
    "^": " elevado a ",
    "…": " puntos suspensivos ",
}


CUSTOM_WORD_REPLACEMENTS = {
    "BanRep": "Banco de la República",
    "spot": "al contado",
}


UNITS = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco",
    "seis", "siete", "ocho", "nueve",
]

SPECIALS = {
    10: "diez",
    11: "once",
    12: "doce",
    13: "trece",
    14: "catorce",
    15: "quince",
    16: "dieciséis",
    17: "diecisiete",
    18: "dieciocho",
    19: "diecinueve",
    20: "veinte",
    21: "veintiuno",
    22: "veintidós",
    23: "veintitrés",
    24: "veinticuatro",
    25: "veinticinco",
    26: "veintiséis",
    27: "veintisiete",
    28: "veintiocho",
    29: "veintinueve",
}

TENS = {
    30: "treinta",
    40: "cuarenta",
    50: "cincuenta",
    60: "sesenta",
    70: "setenta",
    80: "ochenta",
    90: "noventa",
}

HUNDREDS = {
    100: "cien",
    200: "doscientos",
    300: "trescientos",
    400: "cuatrocientos",
    500: "quinientos",
    600: "seiscientos",
    700: "setecientos",
    800: "ochocientos",
    900: "novecientos",
}


def number_to_spanish(n: int) -> str:
    if not 0 <= n <= 999_999_999:
        raise ValueError("Only numbers from 0 to 999,999,999 are supported")

    if n < 10:
        return UNITS[n]

    if n in SPECIALS:
        return SPECIALS[n]

    if n < 100:
        ten = (n // 10) * 10
        unit = n % 10
        return TENS[ten] if unit == 0 else f"{TENS[ten]} y {UNITS[unit]}"

    if n == 100:
        return "cien"

    if n < 1000:
        hundred = (n // 100) * 100
        rest = n % 100
        prefix = "ciento" if hundred == 100 else HUNDREDS[hundred]
        return prefix if rest == 0 else f"{prefix} {number_to_spanish(rest)}"

    if n < 1_000_000:
        thousands = n // 1000
        rest = n % 1000

        if thousands == 1:
            prefix = "mil"
        else:
            prefix = f"{number_to_spanish(thousands)} mil"

        return prefix if rest == 0 else f"{prefix} {number_to_spanish(rest)}"

    millions = n // 1_000_000
    rest = n % 1_000_000

    if millions == 1:
        prefix = "un millón"
    else:
        prefix = f"{number_to_spanish(millions)} millones"

    return prefix if rest == 0 else f"{prefix} {number_to_spanish(rest)}"


def replace_numbers_with_spanish(text: str) -> str:
    def repl(match: re.Match) -> str:
        raw = match.group(0)
        clean = raw.replace(".", "").replace(",", "")

        try:
            n = int(clean)
        except ValueError:
            return raw

        return number_to_spanish(n)

    return re.sub(r"\b\d{1,3}(?:[.,]\d{3})*|\b\d+\b", repl, text)


def normalize_for_voice(text: str) -> str:
    text = text or ""

    for old, new in CUSTOM_WORD_REPLACEMENTS.items():
        text = text.replace(old, new)

    for old, new in sorted(SYMBOL_REPLACEMENTS.items(), key=lambda x: len(x[0]), reverse=True):
        text = text.replace(old, new)

    text = replace_numbers_with_spanish(text)

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


def split_script_into_chunks(script: str, max_chars: int = 150) -> list[str]:
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
