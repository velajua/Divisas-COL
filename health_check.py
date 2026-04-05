import os
import re
import sys
import time
import logging
import importlib
import traceback
from dataclasses import dataclass, field
from typing import Optional

from envyaml import EnvYAML

CONF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
CONF = EnvYAML(CONF_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass
class ScraperResult:
    name: str
    url: str
    city: str
    success: bool = False
    currency_count: int = 0
    missing_currencies: list = field(default_factory=list)
    invalid_values: list = field(default_factory=list)
    error: Optional[str] = None


def _resolve_fn(fn_name: str):
    try:
        mod = importlib.import_module(f"exchanges.{fn_name}")
    except ModuleNotFoundError as e:
        raise NotImplementedError(
            f"Scraper module 'exchanges.{fn_name}' not found."
        ) from e

    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        raise NotImplementedError(
            f"Found module 'exchanges.{fn_name}', but function '{fn_name}()' is missing."
        )
    return fn


def _call(fn, url, total_data, args):
    if args is None:
        return fn(url, total_data)
    if isinstance(args, dict):
        return fn(url, total_data, **args)
    if isinstance(args, (list, tuple)):
        return fn(url, total_data, *args)
    return fn(url, total_data, args)


def _normalize_number(val):
    if val is None:
        return None

    s = str(val).strip()

    # invalid placeholders
    if s in ("", "-", "–", "-X", "X"):
        return None

    # remove thousand separators
    s = s.replace(",", "").replace(" ", "")

    # allow leading negative
    if re.match(r"^-?\d+$", s):
        return int(s)

    return None


def _validate_values(entry: dict) -> list:
    invalid = []

    for currency_name, data in entry.get("data", {}).items():
        for key in ("buy", "sell"):
            val = data.get(key)

            normalized = _normalize_number(val)

            if normalized is None:
                invalid.append(f"{currency_name}.{key}='{val}'")

    return invalid


def _expected_currency_ids(fn_name: str) -> set:
    """
    expected_currencies is now a dict-of-dicts, not lists.
    Example:
      expected_currencies:
        puntoDollar:
          AmericanDollar: true
          Euro: true
    """
    raw = CONF.get("expected_currencies", {}).get(fn_name, {}) or {}

    if isinstance(raw, dict):
        return set(raw.keys())

    if isinstance(raw, (list, tuple, set)):
        return set(raw)

    return set()


def run_health_check() -> list[ScraperResult]:
    results = []

    for city, city_scrapers in CONF.get("function_dicto", {}).items():
        for url, spec in city_scrapers.items():
            fn_name = spec.get("fn")
            args = spec.get("args")
            result = ScraperResult(name=fn_name or "UNKNOWN", url=url, city=city)

            try:
                if not fn_name:
                    raise ValueError(f"Missing 'fn' for scraper config: city={city}, url={url}")

                fn = _resolve_fn(fn_name)
                total_data = _call(fn, url, [], args)

                if not total_data:
                    result.error = "No data returned"
                    results.append(result)
                    continue

                entry = total_data[-1]
                result.currency_count = len(entry.get("data", {}))

                scraped_ids = {
                    d.get("id")
                    for d in entry.get("data", {}).values()
                    if isinstance(d, dict) and d.get("id")
                }

                expected_ids = _expected_currency_ids(fn_name)
                result.missing_currencies = sorted(expected_ids - scraped_ids)
                result.invalid_values = _validate_values(entry)

                result.success = (
                    result.currency_count > 0
                    and len(result.missing_currencies) == 0
                    and len(result.invalid_values) == 0
                )

            except Exception as e:
                result.error = f"{e}\n{traceback.format_exc()}"

            results.append(result)

    return results


def format_report(results: list[ScraperResult]) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("HEALTH CHECK REPORT")
    lines.append("=" * 60)

    all_ok = True
    for r in results:
        status = "PASS" if r.success else "FAIL"
        if not r.success:
            all_ok = False

        lines.append(f"\n[{status}] {r.name} ({r.city} | {r.url})")

        if r.success:
            lines.append(f"  Currencies scraped: {r.currency_count}")
        else:
            if r.error:
                lines.append(f"  Error: {r.error.splitlines()[0]}")
            if r.missing_currencies:
                lines.append(f"  Missing currencies: {r.missing_currencies}")
            if r.invalid_values:
                lines.append(f"  Invalid values: {r.invalid_values}")

    lines.append("\n" + "=" * 60)
    summary = "ALL PASSED" if all_ok else "SOME FAILED"
    lines.append(f"SUMMARY: {summary}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    results = run_health_check()
    print(format_report(results))
    if not all(r.success for r in results):
        sys.exit(1)


def run_periodic_check(stop_event=None):
    config = CONF.get("periodic_check", {})
    interval = config.get("interval_seconds", 300)
    max_retries = config.get("max_retries", 3)
    retry_delay = config.get("retry_delay_seconds", 10)
    alert_on_failure = config.get("alert_on_failure", True)
    log_each = config.get("log_each_attempt", True)

    attempt = 0
    while True:
        if stop_event and stop_event.is_set():
            logging.info("Periodic check stopped by signal")
            break

        attempt += 1
        if log_each:
            logging.info(f"Periodic check attempt #{attempt}")

        all_passed = False
        results = []
        for retry in range(max_retries):
            if stop_event and stop_event.is_set():
                break

            if retry > 0:
                logging.info(f"Retry {retry}/{max_retries} for attempt #{attempt}")
                time.sleep(retry_delay)

            try:
                results = run_health_check()
                all_passed = all(r.success for r in results)
            except Exception as e:
                logging.error(f"Health check error: {e}")
                all_passed = False

            if log_each:
                logging.info(format_report(results))

            if all_passed:
                break

            logging.warning(f"Attempt #{attempt} retry {retry}: some checks failed")

        if not all_passed and alert_on_failure and results:
            failed = [r for r in results if not r.success]
            logging.error(
                f"Periodic check attempt #{attempt} FAILED after {max_retries} retries. "
                f"Failed scrapers: {[f'{r.city}:{r.name}' for r in failed]}"
            )

        if log_each:
            status = "ALL PASSED" if all_passed else "FAILED"
            logging.info(f"Periodic check attempt #{attempt}: {status}")

        time.sleep(interval)
