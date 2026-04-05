const DEFAULT_CITY = "Bogotá";

const GOOGLE_RATES_ENDPOINT = null;

let rawData = null;
let flattenedRows = [];
let currentCity = DEFAULT_CITY;

const citySelector = document.getElementById("citySelector");
const mobileCitySelector = document.getElementById("mobileCitySelector");
const heroCityNameEl = document.getElementById("heroCityName");
const heroPriceCityEl = document.getElementById("heroPriceCity");
const heroExchangeHouseCountEl = document.getElementById("heroExchangeHouseCount");
const heroCurrencyCountEl = document.getElementById("heroCurrencyCount");
const heroUpdatedAtEl = document.getElementById("heroUpdatedAt");

const usdGoogleRateEl = document.getElementById("usdGoogleRate");
const usdGoogleMetaEl = document.getElementById("usdGoogleMeta");
const usdBestBuyLinkEl = document.getElementById("usdBestBuyLink");
const usdBestBuyMetaEl = document.getElementById("usdBestBuyMeta");

const eurGoogleRateEl = document.getElementById("eurGoogleRate");
const eurGoogleMetaEl = document.getElementById("eurGoogleMeta");
const eurBestBuyLinkEl = document.getElementById("eurBestBuyLink");
const eurBestBuyMetaEl = document.getElementById("eurBestBuyMeta");

const summaryGrid = document.getElementById("summaryGrid");
const exchangeGrid = document.getElementById("exchangeGrid");
const currencyGrid = document.getElementById("currencyGrid");
const ratesTableBody = document.getElementById("ratesTableBody");
const loadStatus = document.getElementById("loadStatus");

function formatCop(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toLocaleString("es-CO");
}

function formatSignedCop(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toLocaleString("es-CO");
}

function prettyHouseName(value) {
  if (!value) return "Sin nombre";

  const map = {
    puntoDollar: "Punto Dollar",
    puntoDollarUnicentro: "Punto Dollar Unicentro",
    puntoDollarSalitre: "Punto Dollar Salitre",
    cambiosVancouver: "Cambios Vancouver",
    cambiosKapital: "Cambios Kapital",
    bancounion: "Banco Unión",
    eurodolar: "Eurodólar",
  };

  if (map[value]) return map[value];

  return String(value)
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeNumber(value) {
  if (value === null || value === undefined) return null;

  let cleaned = String(value).trim().replace(/\s+/g, "");

  if (cleaned.includes(",") && !cleaned.includes(".")) {
    const parts = cleaned.split(",");

    if (parts.length === 2 && /^\d+$/.test(parts[0]) && /^\d+$/.test(parts[1])) {
      if (parts[1].length <= 2) {
        cleaned = `${parts[0]}.${parts[1]}`;
      } else {
        cleaned = cleaned.replace(/,/g, "");
      }
    } else {
      cleaned = cleaned.replace(/,/g, "");
    }
  } else {
    cleaned = cleaned.replace(/,/g, "");
  }

  const num = Number(cleaned);
  return Number.isFinite(num) ? num : null;
}

function normalizeCityName(city) {
  return city || DEFAULT_CITY;
}

function getNowLabel() {
  const now = new Date();
  return now.toLocaleString("es-CO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadResultData() {
  const candidates = ["result.json"];

  for (const path of candidates) {
    try {
      const res = await fetch(path, { cache: "no-store" });
      if (!res.ok) continue;
      const data = await res.json();
      return data;
    } catch (err) {}
  }

  throw new Error("No se pudo cargar el archivo de datos.");
}

function flattenGroupedByCity(groupedByCity) {
  const rows = [];

  Object.entries(groupedByCity || {}).forEach(([cityName, houses]) => {
    Object.entries(houses || {}).forEach(([houseGroupName, locations]) => {
      (locations || []).forEach((location) => {
        const locationId = location.id || houseGroupName;
        const exchangeHouse = location.exchange_house || houseGroupName;
        const sourceUrl = location.source_url || "#";
        const city = normalizeCityName(location.city || cityName);

        Object.entries(location.data || {}).forEach(([currencyLabel, currencyData]) => {
          const buy = normalizeNumber(currencyData.buy);
          const sell = normalizeNumber(currencyData.sell);

          rows.push({
            city,
            exchangeHouse,
            exchangeHousePretty: prettyHouseName(exchangeHouse),
            locationId,
            locationPretty: prettyHouseName(locationId),
            sourceUrl,
            currencyLabel,
            currencyId: currencyData.id || currencyLabel,
            buy,
            sell,
          });
        });
      });
    });
  });

  return rows;
}

function getAvailableCities(rows) {
  return [...new Set(rows.map((row) => row.city).filter(Boolean))].sort((a, b) => a.localeCompare(b, "es"));
}

function fillCitySelectors(cities) {
  const html = cities
    .map((city) => `<option value="${city}">${city}</option>`)
    .join("");

  citySelector.innerHTML = html;
  mobileCitySelector.innerHTML = html;

  const initial = cities.includes(DEFAULT_CITY) ? DEFAULT_CITY : (cities[0] || DEFAULT_CITY);

  citySelector.value = initial;
  mobileCitySelector.value = initial;
  currentCity = initial;
}

function getRowsByCity(city) {
  return flattenedRows.filter((row) => row.city === city);
}

function getDistinctLocations(rows) {
  return [...new Set(rows.map((row) => row.locationId))];
}

function getDistinctCurrencies(rows) {
  return [...new Set(rows.map((row) => row.currencyId))];
}

function getBestBuyRow(rows, currencyId) {
  const valid = rows.filter((row) => row.currencyId === currencyId && Number.isFinite(row.buy) && row.buy > 0);
  if (!valid.length) return null;
  return valid.reduce((best, row) => (row.buy > best.buy ? row : best), valid[0]);
}

function getBestSellRow(rows, currencyId) {
  const valid = rows.filter((row) => row.currencyId === currencyId && Number.isFinite(row.sell) && row.sell > 0);
  if (!valid.length) return null;
  return valid.reduce((best, row) => (row.sell < best.sell ? row : best), valid[0]);
}

function buildComparisonMap(rawComparisonData, city) {
  const cityData = (rawComparisonData || {})[city] || [];
  const map = {};

  cityData.forEach((triple) => {
    if (!Array.isArray(triple) || triple.length < 3) return;

    const line1 = triple[0] || "";
    const line2 = triple[1] || "";
    const line3 = triple[2] || "";

    const currencyMatch =
      line1.match(/Value for buying ([A-Za-z]+)/) ||
      line2.match(/Value for selling ([A-Za-z]+)/) ||
      line3.match(/Difference for ([A-Za-z]+)/);

    const diffMatch = line3.match(/Difference for [A-Za-z]+ in value is (-?\d+)/);

    if (!currencyMatch) return;

    const currencyId = currencyMatch[1];
    map[currencyId] = {
      buyLine: line1,
      sellLine: line2,
      diffLine: line3,
      diffValue: diffMatch ? Number(diffMatch[1]) : null,
    };
  });

  return map;
}

function renderHeroCounts(cityRows, referenceRates) {
  heroCityNameEl.textContent = currentCity;
  heroPriceCityEl.textContent = currentCity;
  heroExchangeHouseCountEl.textContent = getDistinctLocations(cityRows).length || "0";
  heroCurrencyCountEl.textContent = getDistinctCurrencies(cityRows).length || "0";
  heroUpdatedAtEl.textContent = referenceRates?.updatedAt || getNowLabel();
}

function setRateLink(linkEl, metaEl, row, labelPrefix) {
  if (!row) {
    linkEl.textContent = "—";
    linkEl.removeAttribute("href");
    metaEl.textContent = "";
    return;
  }

  linkEl.textContent = `${formatCop(row.buy)} COP`;
  linkEl.href = row.sourceUrl || "#";
  metaEl.innerHTML = `${labelPrefix} en <a href="${row.sourceUrl || "#"}" target="_blank" rel="noopener noreferrer">${row.locationPretty}</a>`;
}

function buildReferenceComparisonText(referenceRate, bestBuyRow) {
  if (!Number.isFinite(referenceRate) || !bestBuyRow || !Number.isFinite(bestBuyRow.buy)) {
    return "";
  }

  const diff = bestBuyRow.buy - referenceRate;

  if (diff === 0) {
    return "Igual a la referencia general al momento de carga.";
  }

  if (diff > 0) {
    return `${formatSignedCop(diff)} COP por encima de la referencia general.`;
  }

  return `${formatSignedCop(Math.abs(diff))} COP por debajo de la referencia general.`;
}

async function fetchReferenceRates() {
  const usdUrl = "https://api.frankfurter.dev/v2/rates?base=USD&quotes=COP";
  const eurUrl = "https://api.frankfurter.dev/v2/rates?base=EUR&quotes=COP";

  const [usdRes, eurRes] = await Promise.all([
    fetch(usdUrl, { cache: "no-store" }),
    fetch(eurUrl, { cache: "no-store" }),
  ]);

  if (!usdRes.ok || !eurRes.ok) {
    throw new Error(`No se pudo obtener la referencia general. USD: ${usdRes.status}, EUR: ${eurRes.status}`);
  }

  const [usdData, eurData] = await Promise.all([
    usdRes.json(),
    eurRes.json(),
  ]);

  const usdRow = Array.isArray(usdData) ? usdData[0] : null;
  const eurRow = Array.isArray(eurData) ? eurData[0] : null;

  return {
    usdCop: normalizeNumber(usdRow?.rate),
    eurCop: normalizeNumber(eurRow?.rate),
    sourceLabel: "Referencia general",
    updatedAt: usdRow?.date || eurRow?.date || null,
    usdSourceUrl: usdUrl,
    eurSourceUrl: eurUrl,
  };
}

function renderHeroRates(cityRows, referenceRates) {
  const bestUsdBuy = getBestBuyRow(cityRows, "AmericanDollar");
  const bestEurBuy = getBestBuyRow(cityRows, "Euro");

  if (Number.isFinite(referenceRates.usdCop)) {
    usdGoogleRateEl.textContent = `${formatCop(referenceRates.usdCop)} COP`;
    usdGoogleMetaEl.innerHTML = `<a href="${referenceRates.usdSourceUrl}" target="_blank" rel="noopener noreferrer">Referencia general USD/COP</a>`;
  } else {
    usdGoogleRateEl.textContent = "—";
    usdGoogleMetaEl.textContent = "Referencia no disponible";
  }

  if (Number.isFinite(referenceRates.eurCop)) {
    eurGoogleRateEl.textContent = `${formatCop(referenceRates.eurCop)} COP`;
    eurGoogleMetaEl.innerHTML = `<a href="${referenceRates.eurSourceUrl}" target="_blank" rel="noopener noreferrer">Referencia general EUR/COP</a>`;
  } else {
    eurGoogleRateEl.textContent = "—";
    eurGoogleMetaEl.textContent = "Referencia no disponible";
  }

  setRateLink(usdBestBuyLinkEl, usdBestBuyMetaEl, bestUsdBuy, "Mejor compra");
  setRateLink(eurBestBuyLinkEl, eurBestBuyMetaEl, bestEurBuy, "Mejor compra");

  const usdCompare = buildReferenceComparisonText(referenceRates.usdCop, bestUsdBuy);
  const eurCompare = buildReferenceComparisonText(referenceRates.eurCop, bestEurBuy);

  if (bestUsdBuy && usdCompare) {
    usdBestBuyMetaEl.innerHTML += `<br>${usdCompare}`;
  }

  if (bestEurBuy && eurCompare) {
    eurBestBuyMetaEl.innerHTML += `<br>${eurCompare}`;
  }
}

function renderSummary(cityRows, comparisonMap) {
  const currencies = ["AmericanDollar", "Euro"];
  const cards = [];

  currencies.forEach((currencyId) => {
    const rows = cityRows.filter((row) => row.currencyId === currencyId);
    if (!rows.length) return;

    const bestBuy = getBestBuyRow(rows, currencyId);
    const bestSell = getBestSellRow(rows, currencyId);
    const comp = comparisonMap[currencyId];
    const displayName = rows[0]?.currencyLabel || currencyId;

    cards.push(`
      <article class="summary-card">
        <h3>${displayName}</h3>
        <div class="currency-line"><strong>Mejor compra</strong><br>${bestBuy ? `<a href="${bestBuy.sourceUrl}" target="_blank" rel="noopener noreferrer">${bestBuy.exchangeHousePretty}</a> · ${formatCop(bestBuy.buy)} COP` : "—"}</div>
        <div class="currency-line"><strong>Menor venta</strong><br>${bestSell ? `<a href="${bestSell.sourceUrl}" target="_blank" rel="noopener noreferrer">${bestSell.exchangeHousePretty}</a> · ${formatCop(bestSell.sell)} COP` : "—"}</div>
        ${bestBuy && bestSell ? `<div class="currency-line"><strong>Lectura del mercado</strong><br>La diferencia entre la mejor compra y la menor venta reportadas es de ${formatCop(bestSell.sell - bestBuy.buy)} COP.</div>` : ""}      </article>
    `);
  });

  summaryGrid.innerHTML = cards.join("");
}

function renderExchangeGrid(cityRows) {
  const locations = [];
  const seen = new Set();

  cityRows.forEach((row) => {
    if (seen.has(row.locationId)) return;
    seen.add(row.locationId);

    const locationRows = cityRows.filter((r) => r.locationId === row.locationId);
    const usd = getBestBuyRow(locationRows, "AmericanDollar");
    const eur = getBestBuyRow(locationRows, "Euro");

    locations.push(`
      <article class="exchange-card">
        
        <div class="exchange-head">
          <div class="exchange-title-wrap">
            <div class="exchange-title">${row.exchangeHousePretty}</div>
            ${row.locationPretty && row.locationPretty !== row.exchangeHousePretty
              ? `<div class="exchange-subtitle">${row.locationPretty}</div>`
              : ""}
          </div>
          <a href="${row.sourceUrl}" target="_blank" class="exchange-link">Ver fuente</a>
        </div>

        <div class="exchange-rates">
        <div class="rate-pill">
          <div class="label">USD compra</div>
          <div class="value">${usd ? `${formatCop(usd.buy)} COP` : "—"}</div>
        </div>

        
        <div class="rate-pill">
        <div class="label">EUR compra</div>
        <div class="value">${eur ? `${formatCop(eur.buy)} COP` : "—"}</div>
        </div>
        <div class="rate-pill">
        <div class="label">Monedas</div>
          <div class="value">${getDistinctCurrencies(locationRows).length}</div>
        </div>  
        </div>

      </article>
    `);
  });

  exchangeGrid.innerHTML = locations.join("");
}

function renderCurrencyGrid(cityRows, comparisonMap) {
  const currencyIds = getDistinctCurrencies(cityRows);

  const cards = currencyIds.map((currencyId) => {
    const rows = cityRows.filter((row) => row.currencyId === currencyId);
    const bestBuy = getBestBuyRow(rows, currencyId);
    const bestSell = getBestSellRow(rows, currencyId);
    const comp = comparisonMap[currencyId];
    const displayName = rows[0]?.currencyLabel || currencyId;

    return `
      <article class="currency-card">
        <h3>${displayName}</h3>
        <div class="currency-line"><strong>Mejor compra</strong><br>${bestBuy ? `<a href="${bestBuy.sourceUrl}" target="_blank" rel="noopener noreferrer">${prettyHouseName(bestBuy.locationId)}</a> · ${formatCop(bestBuy.buy)} COP` : "—"}</div>
        <div class="currency-line"><strong>Menor venta</strong><br>${bestSell ? `<a href="${bestSell.sourceUrl}" target="_blank" rel="noopener noreferrer">${prettyHouseName(bestSell.locationId)}</a> · ${formatCop(bestSell.sell)} COP` : "—"}</div>
        ${bestBuy && bestSell ? `<div class="currency-line"><strong>Lectura del mercado</strong><br>La diferencia entre la mejor compra y la menor venta reportadas es de ${formatCop(bestSell.sell - bestBuy.buy)} COP.</div>` : ""}      </article>
    `;
  });

  currencyGrid.innerHTML = cards.join("");
}

function renderTable(cityRows) {
  const rowsHtml = cityRows.map((row) => `
    <tr>
      <td>${row.city}</td>
      <td>${row.exchangeHousePretty}</td>
      <td>${row.locationPretty}</td>
      <td>${row.currencyLabel}</td>
      <td>${Number.isFinite(row.buy) ? `${formatCop(row.buy)} COP` : "—"}</td>
      <td>${Number.isFinite(row.sell) ? `${formatCop(row.sell)} COP` : "—"}</td>
      <td><a href="${row.sourceUrl}" target="_blank" rel="noopener noreferrer">Abrir</a></td>
    </tr>
  `);

  ratesTableBody.innerHTML = rowsHtml.join("");
}

function renderCity(city, referenceRates) {
  currentCity = city;
  citySelector.value = city;
  mobileCitySelector.value = city;

  const cityRows = getRowsByCity(city);
  const comparisonMap = buildComparisonMap(rawData?.comparison_data, city);

  renderHeroCounts(cityRows, referenceRates);
  renderHeroRates(cityRows, referenceRates);
  renderSummary(cityRows, comparisonMap);
  renderExchangeGrid(cityRows);
  renderCurrencyGrid(cityRows, comparisonMap);
  renderTable(cityRows);
}

function setLoadStatus(message, isError) {
  loadStatus.textContent = message || "";
  loadStatus.classList.toggle("hidden", !message);
  loadStatus.classList.toggle("error", Boolean(isError));
}

async function init() {
  try {
    setLoadStatus("");

    rawData = await loadResultData();
    flattenedRows = flattenGroupedByCity(rawData.grouped_by_city || {});

    const cities = getAvailableCities(flattenedRows);
    fillCitySelectors(cities);

    let referenceRates = {
      usdCop: null,
      eurCop: null,
      sourceLabel: "Referencia general",
      updatedAt: null,
      usdSourceUrl: "",
      eurSourceUrl: "",
    };

    try {
      referenceRates = await fetchReferenceRates();
    } catch (err) {
      console.error(err);
    }

    renderCity(currentCity, referenceRates);

    citySelector.addEventListener("change", () => {
      renderCity(citySelector.value, referenceRates);
    });

    mobileCitySelector.addEventListener("change", () => {
      renderCity(mobileCitySelector.value, referenceRates);
    });
  } catch (err) {
    console.error(err);
    setLoadStatus("No se pudo cargar la información disponible en este momento.", true);
  }
}

document.addEventListener("DOMContentLoaded", init);
