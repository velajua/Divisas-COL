import os
import re
import requests

from bs4 import BeautifulSoup
from envyaml import EnvYAML

CONF = EnvYAML(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
)

def amerikanCash(url, total_data=None, local=None):
    if total_data is None:
        total_data = []

    def clean_data(value, type=None):
        value = value.strip()

        if type == "title":
            return value.replace("0", "").strip()

        if value in ("-X", "-", "–", "-0"):
            return "0"

        value = re.sub(r"\s+", "", value)
        value = value.strip("-–")

        if "." in value:
            parts = value.split(".")

            if (
                len(parts) > 1
                and all(part.isdigit() for part in parts)
                and all(len(part) == 3 for part in parts[1:])
            ):
                value = "".join(parts)
            else:
                value = value.replace(".", ",")

        return value

    def is_rate(value):
        value = value.strip()
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", value))

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    amerikanCashData = {}
    amerikanCashSoup = BeautifulSoup(response.text, "lxml")
    tokens = [text.strip() for text in amerikanCashSoup.stripped_strings if text.strip()]

    start_idx = None
    for i, token in enumerate(tokens):
        if token.upper() == "DIVISA":
            if i + 2 < len(tokens) and tokens[i + 1].upper() == "COMPRA" and tokens[i + 2].upper() == "VENTA":
                start_idx = i + 3
                break

    if start_idx is None:
        raise ValueError("Could not find DIVISA / COMPRA / VENTA section")

    i = start_idx
    while i < len(tokens) - 2:
        currency = clean_data(tokens[i], "title")
        buy = clean_data(tokens[i + 1])
        sell = clean_data(tokens[i + 2])

        if is_rate(buy) and is_rate(sell):
            if currency not in amerikanCashData and "\xa0" not in currency:
                currency_id = CONF["currency_dicto"].get(currency)
                if currency_id is None:
                    print(f"Warning: Unknown currency '{currency}' in amerikanCash, skipping")
                    i += 3
                    continue

                amerikanCashData[currency] = {
                    "buy": buy,
                    "sell": sell,
                    "id": currency_id,
                }
            i += 3
        else:
            i += 1

    total_data.append({"id": f"amerikanCash{local}", "data": amerikanCashData})
    return total_data
