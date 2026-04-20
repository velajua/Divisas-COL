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

    current_currency = None
    current_rates = []

    def flush_currency():
        nonlocal current_currency, current_rates

        if current_currency is None or len(current_rates) < 2:
            current_currency = None
            current_rates = []
            return

        if current_currency in amerikanCashData or "\xa0" in current_currency:
            current_currency = None
            current_rates = []
            return

        currency_id = CONF["currency_dicto"].get(current_currency)
        if currency_id is None:
            print(f"Warning: Unknown currency '{current_currency}' in amerikanCash, skipping")
            current_currency = None
            current_rates = []
            return

        amerikanCashData[current_currency] = {
            "buy": current_rates[0],
            "sell": current_rates[1],
            "id": currency_id,
        }
        current_currency = None
        current_rates = []

    for token in tokens[start_idx:]:
        currency = clean_data(token, "title")
        rate = clean_data(token)
        currency_id = CONF["currency_dicto"].get(currency)

        if currency_id is not None:
            if current_currency is None:
                current_currency = currency
                current_rates = []
            elif currency != current_currency and current_rates:
                flush_currency()
                current_currency = currency
            elif currency != current_currency:
                current_currency = currency
                current_rates = []
            continue

        if current_currency is not None and is_rate(rate):
            current_rates.append(rate)
            if len(current_rates) >= 2:
                flush_currency()

    total_data.append({"id": f"amerikanCash{local}", "data": amerikanCashData})
    return total_data
