import os
import requests

from bs4 import BeautifulSoup
from envyaml import EnvYAML

CONF = EnvYAML(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
)


def bancounion(url, total_data=None):
    if total_data is None:
        total_data = []

    def clean_data(value, type=None):
        return (
            value.strip()
            if type == "title"
            else value.replace("$", "").replace(".", "").strip()
        )

    bancounion = requests.get(url, timeout=30)
    bancounionSoup = BeautifulSoup(bancounion.text, "lxml")
    bancounionData, data = {}, []
    temp = bancounionSoup.find("table").find_all("tr")[0].find_all("th")
    data.append([temp[-2].text])
    data.append([temp[-1].text])
    for i in range(2, 4):
        temp = bancounionSoup.find("table").find_all("tr")[i].find_all("td")
        data[-2].append(temp[-2].text)
        data[-1].append(temp[-1].text)
    for i in data:
        currency = clean_data(i[0], "title")
        buy = clean_data(i[1])
        sell = clean_data(i[2])
        currency_id = CONF["currency_dicto"].get(currency)
        if currency_id is None:
            print(f"Warning: Unknown currency '{currency}' in bancounion, skipping")
            continue
        bancounionData[currency] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }
    total_data.append({"id": "bancounion", "data": bancounionData})
    return total_data
