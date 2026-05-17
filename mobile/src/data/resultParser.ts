export type RawResult = {
  countries?: Record<string, Record<string, Record<string, RawCompactLocation[]>>>;
  grouped_by_country?: Record<string, Record<string, Record<string, RawLocation[]>>>;
  grouped_by_city?: Record<string, Record<string, RawLocation[]>>;
};

export type RawCompactLocation = {
  id?: string;
  url?: string;
  rates?: Record<string, RawCompactCurrency>;
};

export type RawLocation = {
  id?: string;
  country?: string;
  city?: string;
  exchange_house?: string;
  source_url?: string;
  data?: Record<string, RawCurrency>;
};

export type RawCompactCurrency = {
  label?: string;
  buy?: string | number | null;
  sell?: string | number | null;
};

export type RawCurrency = {
  buy?: string | number | null;
  sell?: string | number | null;
  id?: string;
};

export type RateRow = {
  country: string;
  city: string;
  exchangeHouse: string;
  locationId: string;
  sourceUrl: string;
  currencyLabel: string;
  currencyId: string;
  buy: number | null;
  sell: number | null;
};

export type CurrencyOption = {
  id: string;
  label: string;
};

export type CountryOption = {
  id: string;
  label: string;
};

export type DisplayLanguage = "es" | "en";

const CURRENCY_NAMES: Record<string, Record<DisplayLanguage, string>> = {
  AmericanDollar: { es: "Dólar estadounidense", en: "US Dollar" },
  Euro: { es: "Euro", en: "Euro" },
  BritishPound: { es: "Libra esterlina", en: "British Pound" },
  CanadianDollar: { es: "Dólar canadiense", en: "Canadian Dollar" },
  AustralianDollar: { es: "Dólar australiano", en: "Australian Dollar" },
  MexicanPeso: { es: "Peso mexicano", en: "Mexican Peso" },
  ArgentineanPeso: { es: "Peso argentino", en: "Argentine Peso" },
  ChileanPeso: { es: "Peso chileno", en: "Chilean Peso" },
  BrasilianReal: { es: "Real brasilero", en: "Brazilian Real" },
  BrazilianReal: { es: "Real brasilero", en: "Brazilian Real" },
  SwissFranc: { es: "Franco suizo", en: "Swiss Franc" },
  PeruveanNewSun: { es: "Sol peruano", en: "Peruvian Sol" },
  ChineseYuan: { es: "Yuan chino", en: "Chinese Yuan" },
  JapaneseYen: { es: "Yen japonés", en: "Japanese Yen" },
  DominicanPeso: { es: "Peso dominicano", en: "Dominican Peso" },
  CostarricanColon: { es: "Colón costarricense", en: "Costa Rican Colon" },
  UAEDirham: { es: "Dirham de Emiratos", en: "UAE Dirham" },
  GuatemalanQuetzal: { es: "Quetzal guatemalteco", en: "Guatemalan Quetzal" },
  TurkishLira: { es: "Lira turca", en: "Turkish Lira" },
  SouthKoreanWon: { es: "Won surcoreano", en: "South Korean Won" },
  RussianRuble: { es: "Rublo ruso", en: "Russian Ruble" },
  NicaraguanCordoba: { es: "Córdoba nicaragüense", en: "Nicaraguan Cordoba" },
  NewZealandDollar: { es: "Dólar neozelandés", en: "New Zealand Dollar" },
  BahamianDollar: { es: "Dólar bahameño", en: "Bahamian Dollar" },
  DanishKrone: { es: "Corona danesa", en: "Danish Krone" },
  NorwegianKrone: { es: "Corona noruega", en: "Norwegian Krone" },
  SwedishKrone: { es: "Corona sueca", en: "Swedish Krona" },
  ArubanFlorin: { es: "Florín arubeño", en: "Aruban Florin" },
  NetherlandsAntilleanGuilder: { es: "Florín antillano", en: "Netherlands Antillean Guilder" },
  BolivianBoliviano: { es: "Boliviano", en: "Bolivian Boliviano" },
  ThaiBaht: { es: "Baht tailandés", en: "Thai Baht" },
  UruguayanPeso: { es: "Peso uruguayo", en: "Uruguayan Peso" },
  HongKongDollar: { es: "Dólar de Hong Kong", en: "Hong Kong Dollar" },
  HonduranLempira: { es: "Lempira hondureño", en: "Honduran Lempira" },
};

export type BestRates = {
  bestBuy: RateRow | null;
  bestSell: RateRow | null;
};

export function normalizeNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;

  const cleaned = String(value).trim().replace(/\s+/g, "").replace(/,/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatDisplayName(value: string): string {
  return value
    .trim()
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z0-9])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((word) => {
      if (/^[A-Z0-9]+$/.test(word)) return word;
      return `${word.charAt(0).toUpperCase()}${word.slice(1)}`;
    })
    .join(" ");
}

export function flattenRates(result: RawResult): RateRow[] {
  const rows: RateRow[] = [];
  const countries = result.countries || {};

  Object.entries(countries).forEach(([countryName, cities]) => {
    Object.entries(cities || {}).forEach(([cityName, houses]) => {
      Object.entries(houses || {}).forEach(([houseName, locations]) => {
        (locations || []).forEach((location) => {
          Object.entries(location.rates || {}).forEach(([currencyId, currency]) => {
            rows.push({
              country: countryName,
              city: cityName,
              exchangeHouse: houseName,
              locationId: location.id || houseName,
              sourceUrl: location.url || "",
              currencyLabel: currency.label || currencyId,
              currencyId,
              buy: normalizeNumber(currency.buy),
              sell: normalizeNumber(currency.sell),
            });
          });
        });
      });
    });
  });

  if (rows.length) return rows;

  const groupedByCountry = result.grouped_by_country || {};

  Object.entries(groupedByCountry).forEach(([countryName, cities]) => {
    Object.entries(cities || {}).forEach(([cityName, houses]) => {
      appendLegacyGroupedRows(rows, countryName, cityName, houses);
    });
  });

  if (rows.length) return rows;

  Object.entries(result.grouped_by_city || {}).forEach(([cityName, houses]) => {
    appendLegacyGroupedRows(rows, "colombia", cityName, houses);
  });

  return rows;
}

function appendLegacyGroupedRows(
  rows: RateRow[],
  countryName: string,
  cityName: string,
  houses: Record<string, RawLocation[]>,
): void {
  Object.entries(houses || {}).forEach(([houseName, locations]) => {
    (locations || []).forEach((location) => {
      Object.entries(location.data || {}).forEach(([currencyLabel, currency]) => {
        rows.push({
          country: location.country || countryName,
          city: location.city || cityName,
          exchangeHouse: location.exchange_house || houseName,
          locationId: location.id || houseName,
          sourceUrl: location.source_url || "",
          currencyLabel,
          currencyId: currency.id || currencyLabel,
          buy: normalizeNumber(currency.buy),
          sell: normalizeNumber(currency.sell),
        });
      });
    });
  });
}

export function getCountries(rows: RateRow[]): CountryOption[] {
  const byId = new Map<string, string>();

  rows.forEach((row) => {
    if (row.country && !byId.has(row.country)) {
      byId.set(row.country, formatDisplayName(row.country));
    }
  });

  return [...byId.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label, "es"));
}

export function getCities(rows: RateRow[]): string[] {
  return [...new Set(rows.map((row) => row.city).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, "es"));
}

export function getCurrencyLabel(currencyId: string, fallbackLabel: string, language: DisplayLanguage = "es"): string {
  return CURRENCY_NAMES[currencyId]?.[language] || formatDisplayName(fallbackLabel || currencyId);
}

export function getCurrencies(rows: RateRow[], language: DisplayLanguage = "es"): CurrencyOption[] {
  const byId = new Map<string, string>();

  rows.forEach((row) => {
    if (!byId.has(row.currencyId)) {
      byId.set(row.currencyId, getCurrencyLabel(row.currencyId, row.currencyLabel, language));
    }
  });

  return [...byId.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label, "es"));
}

export function getBestRates(rows: RateRow[], city: string, currencyId: string): BestRates {
  const selected = rows.filter((row) => row.city === city && row.currencyId === currencyId);
  const buyRows = selected.filter((row) => typeof row.buy === "number" && row.buy > 0);
  const sellRows = selected.filter((row) => typeof row.sell === "number" && row.sell > 0);

  return {
    bestBuy: buyRows.reduce<RateRow | null>((best, row) => (!best || row.buy! > best.buy! ? row : best), null),
    bestSell: sellRows.reduce<RateRow | null>((best, row) => (!best || row.sell! < best.sell! ? row : best), null),
  };
}
