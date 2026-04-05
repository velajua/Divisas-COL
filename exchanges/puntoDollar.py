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


def puntoDollar(url, total_data=None, local=None):
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

    response = requests.get(url, timeout=30)
    puntoDollarData = {}
    puntoDollarSoup = BeautifulSoup(response.text, "lxml")

    for i, data in enumerate(puntoDollarSoup.find_all("tr")):
        if i == 0:
            continue

        temp = data.find_all("td")
        if len(temp) < 3:
            continue

        currency = clean_data(temp[0].text, "title")
        buy = clean_data(temp[1].text)
        sell = clean_data(temp[2].text)

        if (
            currency == "País"
            or currency in puntoDollarData
            or "\xa0" in currency
        ):
            continue

        currency_id = CONF["currency_dicto"].get(currency)
        if currency_id is None:
            print(f"Warning: Unknown currency '{currency}' in puntoDollar, skipping")
            continue

        puntoDollarData[currency] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }

    total_data.append({"id": f"puntoDollar{local}", "data": puntoDollarData})
    return total_data
