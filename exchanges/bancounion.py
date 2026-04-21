import os
import time
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
        value = value.strip()
        if type == "title":
            return value
        return value.replace("$", "").replace(".", "").replace(",", "").strip()

    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": (
            "es-419,es;q=0.9,en;q=0.8,es-ES;q=0.7,en-US;q=0.6"
        ),
        "cache-control": "no-cache",
        "pragma": "no-cache",
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

    for attempt in range(3):
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
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
            else:
                raise

    if response is None:
        raise last_error

    soup = BeautifulSoup(response.text, "lxml")
    page_text = soup.get_text(" ", strip=True).lower()

    if (
        "radware block page" in response.text.lower()
        or "hcaptcha" in response.text.lower()
        or "made us think that you are a bot" in page_text
        or "incident id:" in page_text
    ):
        raise ValueError(
            "BancoUnion returned a CAPTCHA/block page instead of the exchange table"
        )

    bancounion_data = {}

    table = soup.find("table")
    if table is None:
        raise ValueError("BancoUnion page did not contain an HTML table")

    rows = table.find_all("tr")
    if len(rows) < 4:
        raise ValueError("BancoUnion table structure is smaller than expected")

    header_cells = rows[0].find_all(["th", "td"])
    if len(header_cells) < 2:
        raise ValueError("BancoUnion header row does not contain enough columns")

    data = [
        [header_cells[-2].get_text(" ", strip=True)],
        [header_cells[-1].get_text(" ", strip=True)],
    ]

    for i in range(2, 4):
        cols = rows[i].find_all(["td", "th"])
        if len(cols) < 2:
            continue
        data[-2].append(cols[-2].get_text(" ", strip=True))
        data[-1].append(cols[-1].get_text(" ", strip=True))

    for item in data:
        if len(item) < 3:
            continue

        currency = clean_data(item[0], "title")
        buy = clean_data(item[1])
        sell = clean_data(item[2])

        currency_id = CONF["currency_dicto"].get(currency)
        if currency_id is None:
            print(f"Warning: Unknown currency '{currency}' in bancounion, skipping")
            continue

        bancounion_data[currency] = {
            "buy": buy,
            "sell": sell,
            "id": currency_id,
        }

    total_data.append({"id": "bancounion", "data": bancounion_data})
    return total_data
