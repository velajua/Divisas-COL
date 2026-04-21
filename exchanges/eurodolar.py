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


def eurodolar(url, total_data=None):
    if total_data is None:
        total_data = []

    def clean_money(value):
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

    response = requests.get(url, timeout=30)
    eurodolarData = {}
    eurodolarSoup = BeautifulSoup(response.text, "lxml")

    coins_names = [
        unidecode(i.text).strip()
        for i in eurodolarSoup.find_all("h3", class_="et_pb_module_header")[:-1]
    ]

    vals = [
        j.split()[-1]
        for i in eurodolarSoup.find_all("div", class_="et_pb_text_inner")[3:-7]
        for j in i.text.split("\n")
        if j
    ]

    buy = vals[::2]
    sell = vals[1::2]

    for name, b, s in zip(coins_names, buy, sell):
        currency_id = CONF["currency_dicto"].get(name)
        if currency_id is None:
            print(f"Warning: Unknown currency '{name}' in eurodolar, skipping")
            continue

        eurodolarData[name] = {
            "buy": clean_money(b),
            "sell": clean_money(s),
            "id": currency_id,
        }

    total_data.append({"id": "eurodolar", "data": eurodolarData})
    return total_data
