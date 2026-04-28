from copy import deepcopy
import time
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

CACHE_TTL_SECONDS = 300
_CACHE = {}

ANTIBOT_MARKERS = (
    "radware block page",
    "captcha.perfdrive.com",
    "cdn.perfdrive.com",
    "shieldsquare",
    "ssjsconnectorobj",
    "__uzdbm_",
    "hcaptcha",
    "made us think that you are a bot",
    "incident id:",
)


def get_cached_entry(cache_key):
    cached = _CACHE.get(cache_key)
    if not cached:
        return None

    cached_at, entry = cached
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    return deepcopy(entry)


def set_cached_entry(cache_key, entry):
    _CACHE[cache_key] = (time.time(), deepcopy(entry))


def browser_headers(referer=None):
    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "es-CO,es-419;q=0.9,es;q=0.8,en-US;q=0.7,en;q=0.6",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "sec-ch-ua": (
            '"Microsoft Edge";v="146", "Chromium";v="146", '
            '"Not_A Brand";v="99"'
        ),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin" if referer else "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        ),
    }
    if referer:
        headers["referer"] = referer

    return headers


def detect_antibot_block(response, expect_table=True):
    body = response.text.lower()
    soup = BeautifulSoup(response.text, "lxml")
    page_text = soup.get_text(" ", strip=True).lower()
    has_table = soup.find("table") is not None
    final_url = response.url.lower()

    clear_block_markers = (
        "radware block page",
        "captcha.perfdrive.com",
        "hcaptcha",
        "made us think that you are a bot",
        "incident id:",
    )

    matched_clear = [
        marker
        for marker in clear_block_markers
        if marker in body or marker in page_text
    ]
    matched_any = [
        marker for marker in ANTIBOT_MARKERS if marker in body or marker in page_text
    ]

    is_validate_redirect = "validate.perfdrive.com" in final_url
    is_missing_expected_table = expect_table and matched_any and not has_table
    is_blocked = (
        bool(matched_clear) or is_validate_redirect or is_missing_expected_table
    )
    if not is_blocked:
        return None

    return {
        "status": response.status_code,
        "url": response.url,
        "content_length": len(response.text),
        "markers": matched_clear or matched_any,
    }


def raise_for_antibot_block(response, exchange_name, expect_table=True):
    block = detect_antibot_block(response, expect_table=expect_table)
    if block is None:
        return

    markers = ", ".join(block["markers"][:3])
    raise ValueError(
        f"{exchange_name} returned an anti-bot challenge instead of the expected page "
        f"(status={block['status']}, length={block['content_length']}, "
        f"markers={markers}, url={block['url']})"
    )


def site_root(url):
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def warm_up_session(session, url, exchange_name):
    root_url = site_root(url)
    response = session.get(
        root_url,
        headers=browser_headers(),
        timeout=(5, 15),
        allow_redirects=True,
    )
    response.raise_for_status()
    raise_for_antibot_block(response, exchange_name, expect_table=False)
    time.sleep(0.8)
    return root_url


def fetch_browser_page(
    url,
    exchange_name,
    attempts=3,
    timeout=(10, 30),
    expect_table=True,
):
    session = requests.Session()
    response = None
    last_error = None

    for attempt in range(attempts):
        try:
            try:
                referer = warm_up_session(session, url, exchange_name)
            except requests.exceptions.RequestException as exc:
                last_error = exc
                referer = site_root(url)

            response = session.get(
                url,
                headers=browser_headers(referer=referer),
                timeout=timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            raise_for_antibot_block(
                response,
                exchange_name,
                expect_table=expect_table,
            )
            return response
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(3 * (attempt + 1))
            else:
                raise

    raise last_error
