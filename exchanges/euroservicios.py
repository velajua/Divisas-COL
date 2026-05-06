import os
import re
import time
import requests

from envyaml import EnvYAML
from unidecode import unidecode

CONF = EnvYAML(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
)


NORMALIZED_CURRENCY_IDS = {
    re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", unidecode(currency_name)).strip().lower()): currency_id
    for currency_name, currency_id in CONF["currency_dicto"].items()
}


def euroservicios(url, total_data=None):
    if total_data is None:
        total_data = []

    def clean_name(value):
        return re.sub(r"\s+", " ", unidecode(str(value)).strip())

    def clean_rate(value):
        if value is None:
            return "0"

        if isinstance(value, str):
            value = value.strip()
            if value in ("-X", "-", "–", "-0", ""):
                return "0"
            value = value.replace("\xa0", " ")
            value = re.sub(r"\s+", "", value)
            value = value.strip("-–")
            return value.replace(".", ",") if "." in value else value

        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value).replace(".", ",")

        return str(value)

    def resolve_currency_id(item):
        normalized_name = re.sub(
            r"\s+",
            " ",
            re.sub(r"\([^)]*\)", "", unidecode(str(item.get("name", "")))).strip().lower(),
        )
        if normalized_name in NORMALIZED_CURRENCY_IDS:
            return NORMALIZED_CURRENCY_IDS[normalized_name]

        return None

    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": (
            "es-419,es;q=0.9,en;q=0.8,es-ES;q=0.7,en-GB;q=0.6,en-US;q=0.5,"
            "ca;q=0.4,es-CO;q=0.3"
        ),
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

    api_url = "https://admin.euroservicios.com.co/api/getTasas"

    for attempt in range(4):
        try:
            response = session.get(
                api_url,
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

    payload = response.json()
    euroserviciosData = {}

    for item in payload.get("dataTasas", []):
        if not isinstance(item, dict):
            continue

        if not item.get("available", 1):
            continue

        currency_id = resolve_currency_id(item)
        if currency_id is None:
            continue

        currency_name = clean_name(item.get("name", ""))
        if not currency_name:
            continue

        buy = clean_rate(item.get("buyMedellin"))
        sell = clean_rate(item.get("sellMedellin"))

        euroserviciosData[currency_name] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }

    total_data.append({"id": "euroservicios", "data": euroserviciosData})
    return total_data
