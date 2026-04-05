import sys
import os
import json
import traceback
import pandas as pd
from datetime import datetime

from helpers import (
    _build_comparison_data_by_city,
    _call,
    _resolve_fn,
    _group_by_city,
    CONF,
    BQ_PROJECT,
    BQ_TABLE,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from health_check import run_health_check, format_report


def _get_mode(request=None, argv=None):
    if request is not None:
        request_args = getattr(request, "args", {}) or {}
        if request_args.get("mode"):
            return request_args.get("mode")

        try:
            request_json = request.get_json(silent=True) or {}
            if request_json.get("mode"):
                return request_json.get("mode")
        except Exception:
            pass

        return None

    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        return argv[0]

    return None


def _should_write_to_bq(request=None, argv=None):
    if request is not None:
        return True

    argv = argv if argv is not None else sys.argv[1:]
    return "--write-bq" in argv


def _run_scrapers(write_to_bq=False):
    results = run_health_check()
    print(format_report(results))

    total_passed = sum(1 for r in results if r.success)
    total_failed = sum(1 for r in results if not r.success)
    print(f"\nPassed: {total_passed}/{len(results)}")
    print(f"Failed: {total_failed}/{len(results)}")

    total_data = []
    current_city = None
    current_url = None

    try:
        for city, city_scrapers in CONF["function_dicto"].items():
            current_city = city

            for url, spec in city_scrapers.items():
                current_url = url
                fn_name = spec.get("fn")
                args = spec.get("args")
                fn = _resolve_fn(fn_name)

                try:
                    scraped_data = _call(fn, url, [], args)

                    for row in scraped_data:
                        if isinstance(row, dict):
                            row["city"] = city
                            row["exchange_house"] = fn_name
                            row["source_url"] = url

                    total_data.extend(scraped_data)
                    print(f"finished: {city} - {url}")

                except Exception as e:
                    print(f"Error on {city} | {url} ({fn_name}): {e}")

        grouped_by_city = _group_by_city(total_data)
        comparison_data = _build_comparison_data_by_city(total_data)

        if write_to_bq:
            pd.DataFrame.from_records(
                [
                    {
                        "date": datetime.today().strftime("%Y-%m-%d-%H-%M"),
                        "joined_currency_data": str(grouped_by_city),
                        "comparison_data": str(comparison_data),
                        "datetime": datetime.today(),
                    }
                ]
            ).to_gbq(
                destination_table=BQ_TABLE,
                project_id=BQ_PROJECT,
                if_exists="append",
            )

        return {
            "ok": True,
            "health_passed": total_passed,
            "health_failed": total_failed,
            "comparison_data": comparison_data,
            "grouped_by_city": grouped_by_city,
        }

    except Exception:
        print(traceback.format_exc())
        print(f"Error in city={current_city}, url={current_url}")
        return {
            "ok": False,
            "error": traceback.format_exc(),
        }


def main(request=None):
    mode = _get_mode(request=request)
    write_to_bq = _should_write_to_bq(request=request)

    if mode == "health":
        results = run_health_check()
        all_ok = all(r.success for r in results)
        return (format_report(results), 200 if all_ok else 503)

    if mode == "periodic":
        return (
            "periodic mode is not suitable for Cloud Functions because it loops forever",
            400,
        )

    result = _run_scrapers(write_to_bq=write_to_bq)

    if not result["ok"]:
        return (result["error"], 500)

    return ("OK", 200)


if __name__ == "__main__":
    argv = sys.argv[1:]
    mode = _get_mode(argv=argv)
    write_to_bq = _should_write_to_bq(argv=argv)

    if any(arg in ("-h", "--help", "help") for arg in argv):
        print(
            "Usage:\n"
            "  python main.py                Run all scrapers locally\n"
            "  python main.py health         Run health check only\n"
            "  python main.py --write-bq     Run scrapers and write to BigQuery\n"
            "  python main.py -h|--help      Show this help\n\n"
            "Notes:\n"
            "  - 'periodic' is not supported for local one-shot execution.\n"
            "  - In Cloud Functions, use the HTTP request parameter: ?mode=health\n"
        )
        sys.exit(0)

    if mode == "health":
        results = run_health_check()
        print(format_report(results))
        sys.exit(0 if all(r.success for r in results) else 1)

    elif mode == "periodic":
        print("periodic mode is not suitable for local one-shot execution")
        sys.exit(1)

    else:
        result = _run_scrapers(write_to_bq=write_to_bq)
        print(f"\n{result=}\n")
        if mode == "save":
            with open("html/result.json", "w") as f:
                f.write(json.dumps(result))
        sys.exit(0 if result["ok"] else 1)
