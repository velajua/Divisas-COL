import os
import re
import time
import requests

from bs4 import BeautifulSoup
from envyaml import EnvYAML

CONF = EnvYAML(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
)


def euroservicios(url, total_data=None):
    if total_data is None:
        total_data = []

    def clean_data(value, type=None):
        value = value.strip()

        if type == "title":
            value = re.sub(r"^\#+\s*", "", value).strip()
            value = re.sub(r"\s+", " ", value).strip()
            return value

        if value in ("-X", "-", "–", "-0"):
            return "0"

        value = re.sub(r"^\$\s*", "", value)
        value = value.replace("\xa0", " ")
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

        return value

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "es-419,es;q=0.9,en;q=0.8,es-ES;q=0.7,en-GB;q=0.6,en-US;q=0.5,ca;q=0.4,es-CO;q=0.3",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        ),
    }

    session = requests.Session()
    session.headers.update(headers)

    response = None
    last_error = None

    for attempt in range(4):
        try:
            response = session.get(
                url,
                timeout=(15, 60),
                allow_redirects=True,
            )
            response.raise_for_status()
            break

        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
            else:
                raise

    if response is None:
        raise last_error

    euroserviciosSoup = BeautifulSoup(response.content, "lxml")

    euroserviciosData = {}

    cards = euroserviciosSoup.find_all(
        "div",
        class_=lambda x: isinstance(x, str) and "group" in x
    )

    for card in cards:
        title_tag = card.find("h4")
        if not title_tag:
            continue

        currency = clean_data(title_tag.get_text(" ", strip=True), "title")

        buy = None
        sell = None

        for p_tag in card.find_all("p"):
            text = p_tag.get_text(" ", strip=True)

            if "Compra:" in text:
                buy = clean_data(text.split(":", 1)[1])

            elif "Venta:" in text:
                sell = clean_data(text.split(":", 1)[1])

        if buy is None or sell is None:
            continue

        if currency in euroserviciosData:
            continue

        currency_id = CONF["currency_dicto"].get(currency)
        if currency_id is None:
            print(
                f"Warning: Unknown currency '{currency}' in euroservicios, skipping"
            )
            continue

        euroserviciosData[currency] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }

    total_data.append({"id": "euroservicios", "data": euroserviciosData})
    return total_data
