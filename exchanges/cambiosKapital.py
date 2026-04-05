import os
import re
import requests

from bs4 import BeautifulSoup
from envyaml import EnvYAML
from unidecode import unidecode

CONF = EnvYAML(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
)


def cambiosKapital(url, total_data=None):
    if total_data is None:
        total_data = []

    def clean_data(value, type=None):
        if type == "title":
            return unidecode(value.strip())

        value = str(value).strip()
        value = re.sub(r"\s+", "", value)

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

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "accept-language": "es-419,es;q=0.9,en;q=0.8",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    cambiosKapital_resp = requests.get(url, headers=headers, timeout=30)
    cambiosKapitalSoup = BeautifulSoup(cambiosKapital_resp.content, "lxml")
    cambiosKapitalData = {}

    for item in cambiosKapitalSoup.find_all("div", class_="jet-listing-grid__item"):
        text = item.get_text(strip=True)
        parts = text.split("Compramos:")
        if len(parts) < 2:
            continue

        currency = clean_data(parts[0], "title")
        rest = "Compramos:".join(parts[1:])
        values = rest.split("Vendemos:")
        if len(values) < 2:
            continue

        buy = clean_data(values[0])
        sell = clean_data(values[1])

        currency_id = CONF["currency_dicto"].get(currency)
        if currency_id is None:
            print(f"Warning: Unknown currency '{currency}' in cambiosKapital, skipping")
            continue

        cambiosKapitalData[currency] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }

    total_data.append({"id": "cambiosKapital", "data": cambiosKapitalData})
    return total_data
