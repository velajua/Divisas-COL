import importlib

from envyaml import EnvYAML

BQ_PROJECT = "cedar-setup-376217"
BQ_TABLE = "divisas.bogota-divisas"

CONF = EnvYAML("config.yaml")


def _resolve_fn(fn_name: str):
    fn = globals().get(fn_name)
    if callable(fn):
        return fn

    pkg = f"{__package__}.exchanges" if __package__ else "exchanges"

    try:
        mod = importlib.import_module(f"{pkg}.{fn_name}")
    except ModuleNotFoundError as e:
        raise NotImplementedError(
            f"Scraper function '{fn_name}' not found: expected file '{pkg.replace('.', '/')}/{fn_name}.py'."
        ) from e

    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        raise NotImplementedError(
            f"Found module '{pkg}.{fn_name}', but function '{fn_name}()' is missing."
        )

    globals()[fn_name] = fn
    return fn


def _call(fn, url, total_data, args):
    if args is None:
        return fn(url, total_data)
    if isinstance(args, dict):
        return fn(url, total_data, **args)
    if isinstance(args, (list, tuple)):
        return fn(url, total_data, *args)
    return fn(url, total_data, args)


def join_data(total_data):
    values = {key_: [] for key_ in list(CONF["currency_dicto"].values())}

    for dicto in total_data:
        if not isinstance(dicto, dict):
            continue

        for key_, data_ in dicto.get("data", {}).items():
            currency_id = data_.get("id")
            if currency_id in values:
                values[currency_id].append(
                    {
                        key_: {
                            "id": dicto.get("id"),
                            "buy": data_.get("buy"),
                            "sell": data_.get("sell"),
                        }
                    }
                )

    return values


def joined_currency(joined_currency_data):
    comparison_data = []

    for key_ in list(joined_currency_data.keys()):
        key_currency = joined_currency_data[key_]
        buy_value, sell_value = 0, 1e10
        temp_buy_data, temp_sell_data = "", ""

        for temp_currency in key_currency:
            b = list(temp_currency.keys())

            try:
                temp_buy = int(str(temp_currency[b[0]]["buy"]).replace(" ", ""))
                temp_sell = int(str(temp_currency[b[0]]["sell"]).replace(" ", ""))

                if temp_buy > buy_value:
                    buy_value = temp_buy
                    temp_buy_data = (
                        f"Value for buying {key_} is best value at "
                        f"{temp_currency[b[0]]['id']} with value "
                        f"{temp_currency[b[0]]['buy']}"
                    )

                if temp_sell < sell_value:
                    sell_value = temp_sell
                    temp_sell_data = (
                        f"Value for selling {key_} is best value at "
                        f"{temp_currency[b[0]]['id']} with value "
                        f"{temp_currency[b[0]]['sell']}"
                    )
            except (ValueError, TypeError, KeyError):
                pass

        difference_value = f"Difference for {key_} in value is {buy_value - sell_value}"
        comparison_data.append([temp_buy_data, temp_sell_data, difference_value])

    return comparison_data


def _group_by_city(data):
    grouped = {}

    for row in data:
        if not isinstance(row, dict):
            continue

        city = row.get("city", "UNKNOWN_CITY")
        exchange_house = row.get("exchange_house", "UNKNOWN_EXCHANGE_HOUSE")

        grouped.setdefault(city, {})
        grouped[city].setdefault(exchange_house, [])
        grouped[city][exchange_house].append(row)

    return grouped


def _build_comparison_data_by_city(data):
    comparison_by_city = {}
    grouped_by_city = _group_by_city(data)

    for city, exchange_houses in grouped_by_city.items():
        city_rows = []

        for rows in exchange_houses.values():
            city_rows.extend(rows)

        joined_currency_data = join_data(city_rows)
        comparison_by_city[city] = joined_currency(joined_currency_data)

    return comparison_by_city
