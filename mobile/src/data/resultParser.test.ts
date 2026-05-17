import assert from "node:assert/strict";
import test from "node:test";

import {
  flattenRates,
  formatDisplayName,
  getBestRates,
  getCities,
  getCountries,
  getCurrencies,
} from "./resultParser";
import { buildNewsletterUrl, pickDefaultCountry } from "./settings";

const sampleResult = {
  countries: {
    colombia: {
      Bogota: {
        casaUno: [
          {
            id: "sedeUno",
            url: "https://example.com/uno",
            rates: {
              AmericanDollar: { label: "Dolar", buy: "3600", sell: "3700" },
              Euro: { label: "Euro", buy: "4300", sell: "4450" },
            },
          },
        ],
        casaDos: [
          {
            id: "sedeDos",
            url: "https://example.com/dos",
            rates: {
              AmericanDollar: { label: "Dolar", buy: "3650", sell: "3680" },
            },
          },
        ],
      },
      Medellin: {
        casaTres: [
          {
            id: "sedeTres",
            rates: {
              AmericanDollar: { label: "Dolar", buy: "3500", sell: "3710" },
            },
          },
        ],
      },
    },
  },
};

test("flattenRates converts grouped city payload into display rows", () => {
  const rows = flattenRates(sampleResult);

  assert.equal(rows.length, 4);
  assert.deepEqual(rows[0], {
    city: "Bogota",
    country: "colombia",
    exchangeHouse: "casaUno",
    locationId: "sedeUno",
    sourceUrl: "https://example.com/uno",
    currencyLabel: "Dolar",
    currencyId: "AmericanDollar",
    buy: 3600,
    sell: 3700,
  });
});

test("getCountries returns formatted country options from compact payloads", () => {
  const rows = flattenRates({
    countries: {
      colombia: {
        Bogota: {
          casaUno: [{ rates: { AmericanDollar: { label: "Dolar", buy: "3600", sell: "3700" } } }],
        },
      },
      peru: {
        Lima: {
          casaDos: [{ rates: { AmericanDollar: { label: "Dolar", buy: "100", sell: "110" } } }],
        },
      },
    },
  });

  assert.deepEqual(getCountries(rows), [
    { id: "colombia", label: "Colombia" },
    { id: "peru", label: "Peru" },
  ]);
});

test("pickDefaultCountry prefers detected country and falls back to Colombia", () => {
  const countries = [
    { id: "colombia", label: "Colombia" },
    { id: "peru", label: "Peru" },
  ];

  assert.equal(pickDefaultCountry(countries, "PE"), "peru");
  assert.equal(pickDefaultCountry(countries, "XX"), "colombia");
  assert.equal(pickDefaultCountry([{ id: "peru", label: "Peru" }], "XX"), "peru");
});

test("buildNewsletterUrl uses selected language and country", () => {
  assert.equal(
    buildNewsletterUrl("https://divisascol.com", "en", "peru"),
    "https://divisascol.com/en/peru/newsletter/",
  );
  assert.equal(
    buildNewsletterUrl("https://divisascol.com/", "es", ""),
    "https://divisascol.com/es/colombia/newsletter/",
  );
});

test("getCities and getCurrencies return sorted unique values", () => {
  const rows = flattenRates(sampleResult);

  assert.deepEqual(getCities(rows), ["Bogota", "Medellin"]);
  assert.deepEqual(getCurrencies(rows), [
    { id: "AmericanDollar", label: "Dólar estadounidense" },
    { id: "Euro", label: "Euro" },
  ]);
});

test("getCurrencies translates known currency ids for Spanish display", () => {
  assert.deepEqual(
    getCurrencies([
      {
        city: "Bogota",
        country: "colombia",
        exchangeHouse: "casaUno",
        locationId: "sedeUno",
        sourceUrl: "",
        currencyLabel: "AmericanDollar",
        currencyId: "AmericanDollar",
        buy: 3600,
        sell: 3700,
      },
    ]),
    [{ id: "AmericanDollar", label: "Dólar estadounidense" }],
  );
});

test("getCurrencies translates known currency ids for English display", () => {
  const rows = flattenRates({
    countries: {
      colombia: {
        Bogota: {
          casaUno: [
            {
              rates: {
                AmericanDollar: { label: "Dólar Estadounidense", buy: "3600", sell: "3700" },
                BrazilianReal: { label: "Real Brasilero", buy: "700", sell: "780" },
              },
            },
          ],
        },
      },
    },
  });

  assert.deepEqual(getCurrencies(rows, "en"), [
    { id: "BrazilianReal", label: "Brazilian Real" },
    { id: "AmericanDollar", label: "US Dollar" },
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

test("formatDisplayName separates compact store and location names", () => {
  assert.equal(formatDisplayName("casaDeCambiosBogota"), "Casa De Cambios Bogota");
  assert.equal(formatDisplayName("sede_norte_2"), "Sede Norte 2");
  assert.equal(formatDisplayName("USDExpressCOL"), "USD Express COL");
});
