export type RawResult = {
  grouped_by_city?: Record<string, Record<string, RawLocation[]>>;
};

export type RawLocation = {
  id?: string;
  city?: string;
  exchange_house?: string;
  source_url?: string;
  data?: Record<string, RawCurrency>;
};

export type RawCurrency = {
  buy?: string | number | null;
  sell?: string | number | null;
  id?: string;
};

export type RateRow = {
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

  Object.entries(result.grouped_by_city || {}).forEach(([cityName, houses]) => {
    Object.entries(houses || {}).forEach(([houseName, locations]) => {
      (locations || []).forEach((location) => {
        Object.entries(location.data || {}).forEach(([currencyLabel, currency]) => {
          rows.push({
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
  });

  return rows;
}

export function getCities(rows: RateRow[]): string[] {
  return [...new Set(rows.map((row) => row.city).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, "es"));
}

export function getCurrencies(rows: RateRow[]): CurrencyOption[] {
  const byId = new Map<string, string>();

  rows.forEach((row) => {
    if (!byId.has(row.currencyId)) {
      byId.set(row.currencyId, row.currencyLabel);
    }
  });

  return [...byId.entries()]
    .map(([id, label]) => ({ id, label: formatDisplayName(label) }))
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
