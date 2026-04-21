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


def cambiosVancouver(url, total_data=None):
    if total_data is None:
        total_data = []

    def clean_data(value, type=None):
        if type == "title":
            return value.strip()

        value = str(value).replace("$", "").strip()
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

    cambiosVancouverHeaders = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "accept-language": "es-419,es;q=0.9,en;q=0.8",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    cambiosVancouver = requests.get(url, headers=cambiosVancouverHeaders, timeout=30)
    cambiosVancouverSoup = BeautifulSoup(cambiosVancouver.text, "lxml")
    cambiosVancouverData = {}

    for i, data in enumerate(cambiosVancouverSoup.find_all("tr")):
        if i == 0:
            continue

        temp = data.find_all("td")
        if len(temp) == 0:
            continue

        currency = clean_data(temp[1].text, "title")
        buy = clean_data(temp[2].text)
        sell = clean_data(temp[3].text)

        if (
            currency == "País"
            or currency in cambiosVancouverData.keys()
            or "\xa0" in currency
            or buy == "-0"
            or sell == "-0"
        ):
            continue

        currency_id = CONF["currency_dicto"].get(currency)
        if currency_id is None:
            print(
                f"Warning: Unknown currency '{currency}' in cambiosVancouver, skipping"
            )
            continue

        cambiosVancouverData[currency] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }

    total_data.append({"id": "cambiosVancouver", "data": cambiosVancouverData})
    return total_data
