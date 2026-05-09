import assert from "node:assert/strict";
import test from "node:test";

import {
  flattenRates,
  getBestRates,
  getCities,
  getCurrencies,
} from "./resultParser";

const sampleResult = {
  grouped_by_city: {
    Bogota: {
      casaUno: [
        {
          id: "sedeUno",
          city: "Bogota",
          exchange_house: "casaUno",
          source_url: "https://example.com/uno",
          data: {
            "Dolar": { buy: "3600", sell: "3700", id: "AmericanDollar" },
            "Euro": { buy: "4300", sell: "4450", id: "Euro" },
          },
        },
      ],
      casaDos: [
        {
          id: "sedeDos",
          city: "Bogota",
          exchange_house: "casaDos",
          source_url: "https://example.com/dos",
          data: {
            "Dolar": { buy: "3650", sell: "3680", id: "AmericanDollar" },
          },
        },
      ],
    },
    Medellin: {
      casaTres: [
        {
          id: "sedeTres",
          data: {
            "Dolar": { buy: "3500", sell: "3710", id: "AmericanDollar" },
          },
        },
      ],
    },
  },
};

test("flattenRates converts grouped city payload into display rows", () => {
  const rows = flattenRates(sampleResult);

  assert.equal(rows.length, 4);
  assert.deepEqual(rows[0], {
    city: "Bogota",
    exchangeHouse: "casaUno",
    locationId: "sedeUno",
    sourceUrl: "https://example.com/uno",
    currencyLabel: "Dolar",
    currencyId: "AmericanDollar",
    buy: 3600,
    sell: 3700,
  });
});

test("getCities and getCurrencies return sorted unique values", () => {
  const rows = flattenRates(sampleResult);

  assert.deepEqual(getCities(rows), ["Bogota", "Medellin"]);
  assert.deepEqual(getCurrencies(rows), [
    { id: "AmericanDollar", label: "Dolar" },
    { id: "Euro", label: "Euro" },
  ]);
});

test("getBestRates returns best buy and lowest sell for a city and currency", () => {
  const rows = flattenRates(sampleResult);
  const best = getBestRates(rows, "Bogota", "AmericanDollar");

  assert.equal(best.bestBuy?.locationId, "sedeDos");
  assert.equal(best.bestBuy?.buy, 3650);
  assert.equal(best.bestSell?.locationId, "sedeDos");
  assert.equal(best.bestSell?.sell, 3680);
});
