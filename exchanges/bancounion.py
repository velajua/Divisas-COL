import os

from bs4 import BeautifulSoup
from envyaml import EnvYAML

from exchanges.antibot import fetch_browser_page, get_cached_entry, set_cached_entry

CONF = EnvYAML(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
)


def bancounion(url, total_data=None):
    if total_data is None:
        total_data = []

    cache_key = ("bancounion", url)
    cached_entry = get_cached_entry(cache_key)
    if cached_entry:
        total_data.append(cached_entry)
        return total_data

    def clean_data(value, type=None):
        value = value.strip()
        if type == "title":
            return value
        return value.replace("$", "").replace(".", "").replace(",", "").strip()

    response = fetch_browser_page(url, "BancoUnion")
    soup = BeautifulSoup(response.text, "lxml")

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

    entry = {"id": "bancounion", "data": bancounion_data}
    set_cached_entry(cache_key, entry)
    total_data.append(entry)
    return total_data
