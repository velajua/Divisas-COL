const DEFAULT_CITY = "Bogotá";

const GOOGLE_RATES_ENDPOINT = null;

let rawData = null;
let flattenedRows = [];
let currentCity = DEFAULT_CITY;

const DEFAULT_HERO_CURRENCIES = ["AmericanDollar", "Euro"];
const CURRENCY_REFERENCE_CODE_MAP = {
  AmericanDollar: "USD",
  Euro: "EUR",
  PoundSterling: "GBP",
  CanadianDollar: "CAD",
  AustralianDollar: "AUD",
  SwissFranc: "CHF",
  JapaneseYen: "JPY",
  MexicanPeso: "MXN",
  BrazilianReal: "BRL",
  ArgentinePeso: "ARS",
  ChileanPeso: "CLP",
  PeruvianSol: "PEN",
  NewZealandDollar: "NZD",
  SingaporeDollar: "SGD",
  HongKongDollar: "HKD",
  ChineseYuan: "CNY",
  ChineseRenminbi: "CNY",
  Renminbi: "CNY",
  KoreanWon: "KRW",
  NorwegianKrone: "NOK",
  SwedishKrona: "SEK",
  DanishKrone: "DKK"
};

let selectedHeroCurrencies = [...DEFAULT_HERO_CURRENCIES];
let currentCityRows = [];
let currentComparisonMap = {};
let currentReferenceRates = { updatedAt: null, byCurrency: {} };
const referenceRateCache = new Map();

const citySelector = document.getElementById("citySelector");
const mobileCitySelector = document.getElementById("mobileCitySelector");
const heroCityNameEl = document.getElementById("heroCityName");
const heroPriceCityEl = document.getElementById("heroPriceCity");
const heroExchangeHouseCountEl = document.getElementById("heroExchangeHouseCount");
const heroCurrencyCountEl = document.getElementById("heroCurrencyCount");
const heroUpdatedAtEl = document.getElementById("heroUpdatedAt");

const heroCurrencySelector1 = document.getElementById("heroCurrencySelector1");
const heroCurrencySelector2 = document.getElementById("heroCurrencySelector2");
const heroReferenceRateEl1 = document.getElementById("heroReferenceRate1");
const heroReferenceMetaEl1 = document.getElementById("heroReferenceMeta1");
const heroBestBuyLinkEl1 = document.getElementById("heroBestBuyLink1");
const heroBestBuyMetaEl1 = document.getElementById("heroBestBuyMeta1");
const heroReferenceRateEl2 = document.getElementById("heroReferenceRate2");
const heroReferenceMetaEl2 = document.getElementById("heroReferenceMeta2");
const heroBestBuyLinkEl2 = document.getElementById("heroBestBuyLink2");
const heroBestBuyMetaEl2 = document.getElementById("heroBestBuyMeta2");

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

function getCurrencyOptions(cityRows) {
  const map = new Map();

  cityRows.forEach((row) => {
    if (!map.has(row.currencyId)) {
      map.set(row.currencyId, row.currencyLabel || row.currencyId);
    }
  });

  return [...map.entries()]
    .map(([currencyId, currencyLabel]) => ({ currencyId, currencyLabel }))
    .sort((a, b) => a.currencyLabel.localeCompare(b.currencyLabel, "es"));
}

function getDefaultHeroCurrencies(cityRows) {
  const available = getCurrencyOptions(cityRows).map((item) => item.currencyId);
  const picked = [];

  DEFAULT_HERO_CURRENCIES.forEach((currencyId) => {
    if (available.includes(currencyId) && !picked.includes(currencyId)) {
      picked.push(currencyId);
    }
  });

  available.forEach((currencyId) => {
    if (picked.length < 2 && !picked.includes(currencyId)) {
      picked.push(currencyId);
    }
  });

  while (picked.length < 2) {
    picked.push(picked[0] || DEFAULT_HERO_CURRENCIES[picked.length] || "");
  }

  return picked;
}

function fillHeroCurrencySelectors(cityRows, resetToDefault) {
  const options = getCurrencyOptions(cityRows);
  const defaults = getDefaultHeroCurrencies(cityRows);
  const availableIds = options.map((item) => item.currencyId);

  if (
    resetToDefault ||
    !availableIds.includes(selectedHeroCurrencies[0]) ||
    !availableIds.includes(selectedHeroCurrencies[1])
  ) {
    selectedHeroCurrencies = [...defaults];
  }

  const optionsHtml = options
    .map((item) => `<option value="${item.currencyId}">${item.currencyLabel}</option>`)
    .join("");

  heroCurrencySelector1.innerHTML = optionsHtml;
  heroCurrencySelector2.innerHTML = optionsHtml;

  heroCurrencySelector1.value = selectedHeroCurrencies[0] || defaults[0];
  heroCurrencySelector2.value = selectedHeroCurrencies[1] || defaults[1];
}

function getCurrencyReferenceCode(currencyId, currencyLabel) {
  if (CURRENCY_REFERENCE_CODE_MAP[currencyId]) {
    return CURRENCY_REFERENCE_CODE_MAP[currencyId];
  }

  const label = String(currencyLabel || "").toUpperCase();

  if (label.includes("USD") || label.includes("DÓLAR ESTADOUNIDENSE") || label.includes("DOLAR ESTADOUNIDENSE")) return "USD";
  if (label.includes("EUR") || label.includes("EURO")) return "EUR";
  if (label.includes("GBP") || label.includes("LIBRA")) return "GBP";
  if (label.includes("CAD")) return "CAD";
  if (label.includes("AUD")) return "AUD";
  if (label.includes("CHF") || label.includes("FRANCO SUIZO")) return "CHF";
  if (label.includes("JPY") || label.includes("YEN")) return "JPY";
  if (label.includes("MXN") || label.includes("PESO MEXICANO")) return "MXN";
  if (label.includes("BRL") || label.includes("REAL BRASILEÑO") || label.includes("REAL BRASILENO")) return "BRL";
  if (label.includes("ARS") || label.includes("PESO ARGENTINO")) return "ARS";
  if (label.includes("CLP") || label.includes("PESO CHILENO")) return "CLP";
  if (label.includes("PEN") || label.includes("SOL PERUANO")) return "PEN";
  if (label.includes("CNY") || label.includes("YUAN") || label.includes("RENMINBI")) return "CNY";

  return null;
}

function extractReferenceRate(data) {
  if (Array.isArray(data) && data[0]) {
    return {
      rate: normalizeNumber(data[0].rate),
      date: data[0].date || null,
    };
  }

  if (data && typeof data === "object") {
    return {
      rate: normalizeNumber(data?.rates?.COP),
      date: data?.date || null,
    };
  }

  return { rate: null, date: null };
}

async function fetchReferenceRate(currencyId, currencyLabel) {
  const referenceCode = getCurrencyReferenceCode(currencyId, currencyLabel);

  if (!referenceCode) {
    return {
      currencyId,
      currencyLabel,
      referenceCode: null,
      rate: null,
      updatedAt: null,
      sourceUrl: "",
    };
  }

  if (referenceRateCache.has(referenceCode)) {
    return referenceRateCache.get(referenceCode);
  }

  const sourceUrl = `https://api.frankfurter.dev/v2/rates?base=${encodeURIComponent(referenceCode)}&quotes=COP`;
  const response = await fetch(sourceUrl, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`No se pudo obtener la referencia general para ${referenceCode}. Status ${response.status}`);
  }

  const data = await response.json();
  const parsed = extractReferenceRate(data);
  const result = {
    currencyId,
    currencyLabel,
    referenceCode,
    rate: parsed.rate,
    updatedAt: parsed.date,
    sourceUrl,
  };

  referenceRateCache.set(referenceCode, result);
  return result;
}

async function loadReferenceRatesForSelectedCurrencies(cityRows) {
  const labelsById = new Map(cityRows.map((row) => [row.currencyId, row.currencyLabel || row.currencyId]));
  const byCurrency = {};

  await Promise.all(
    selectedHeroCurrencies.map(async (currencyId) => {
      if (!currencyId) return;

      try {
        byCurrency[currencyId] = await fetchReferenceRate(currencyId, labelsById.get(currencyId));
      } catch (error) {
        console.error(error);
        byCurrency[currencyId] = {
          currencyId,
          currencyLabel: labelsById.get(currencyId) || currencyId,
          referenceCode: getCurrencyReferenceCode(currencyId, labelsById.get(currencyId)),
          rate: null,
          updatedAt: null,
          sourceUrl: "",
        };
      }
    })
  );

  const updatedAt = Object.values(byCurrency).find((item) => item?.updatedAt)?.updatedAt || null;

  return { updatedAt, byCurrency };
}

function renderHeroRateCard({ cityRows, currencyId, referenceData, rateEl, metaEl, bestBuyLinkEl, bestBuyMetaEl }) {
  const rows = cityRows.filter((row) => row.currencyId === currencyId);
  const bestBuy = getBestBuyRow(rows, currencyId);
  const referenceRate = referenceData?.rate;
  const referenceCode = referenceData?.referenceCode;

  if (Number.isFinite(referenceRate)) {
    rateEl.textContent = `${formatCop(referenceRate)} COP`;
    metaEl.innerHTML = referenceData?.sourceUrl
      ? `<a href="${referenceData.sourceUrl}" target="_blank" rel="noopener noreferrer">Referencia ${referenceCode}/COP</a>`
      : "Referencia disponible";
  } else {
    rateEl.textContent = "—";
    metaEl.textContent = referenceCode
      ? `No hay referencia disponible ahora para ${referenceCode}/COP.`
      : "No hay referencia disponible para esta moneda.";
  }

  setRateLink(bestBuyLinkEl, bestBuyMetaEl, bestBuy, "Mejor compra");

  const compareText = buildReferenceComparisonText(referenceRate, bestBuy);

  if (bestBuy && compareText) {
    bestBuyMetaEl.innerHTML += `<br>${compareText}`;
  }
}

function renderHeroRates(cityRows, referenceRates) {
  const firstCurrencyId = selectedHeroCurrencies[0];
  const secondCurrencyId = selectedHeroCurrencies[1];

  renderHeroRateCard({
    cityRows,
    currencyId: firstCurrencyId,
    referenceData: referenceRates.byCurrency[firstCurrencyId],
    rateEl: heroReferenceRateEl1,
    metaEl: heroReferenceMetaEl1,
    bestBuyLinkEl: heroBestBuyLinkEl1,
    bestBuyMetaEl: heroBestBuyMetaEl1,
  });

  renderHeroRateCard({
    cityRows,
    currencyId: secondCurrencyId,
    referenceData: referenceRates.byCurrency[secondCurrencyId],
    rateEl: heroReferenceRateEl2,
    metaEl: heroReferenceMetaEl2,
    bestBuyLinkEl: heroBestBuyLinkEl2,
    bestBuyMetaEl: heroBestBuyMetaEl2,
  });
}

function renderSummary(cityRows) {
  const cards = [];

  selectedHeroCurrencies.forEach((currencyId) => {
    const rows = cityRows.filter((row) => row.currencyId === currencyId);
    if (!rows.length) return;

    const bestBuy = getBestBuyRow(rows, currencyId);
    const bestSell = getBestSellRow(rows, currencyId);
    const displayName = rows[0]?.currencyLabel || currencyId;

    cards.push(`
      <article class="summary-card">
        <h3>${displayName}</h3>
        <div class="currency-line"><strong>Mejor compra</strong><br>${bestBuy ? `<a href="${bestBuy.sourceUrl}" target="_blank" rel="noopener noreferrer">${bestBuy.exchangeHousePretty}</a> · ${formatCop(bestBuy.buy)} COP` : "—"}</div>
        <div class="currency-line"><strong>Menor venta</strong><br>${bestSell ? `<a href="${bestSell.sourceUrl}" target="_blank" rel="noopener noreferrer">${bestSell.exchangeHousePretty}</a> · ${formatCop(bestSell.sell)} COP` : "—"}</div>
        ${bestBuy && bestSell ? `<div class="currency-line"><strong>Lectura del mercado</strong><br>La diferencia entre la mejor compra y la menor venta reportadas es de ${formatCop(bestSell.sell - bestBuy.buy)} COP.</div>` : ""}
      </article>
    `);
  });

  summaryGrid.innerHTML = cards.join("");
}

function renderExchangeGrid(cityRows) {
  const locations = [];
  const seen = new Set();
  const selectedCurrencies = [...new Set(selectedHeroCurrencies.filter(Boolean))];

  cityRows.forEach((row) => {
    if (seen.has(row.locationId)) return;
    seen.add(row.locationId);

    const locationRows = cityRows.filter((r) => r.locationId === row.locationId);

    const filteredCurrencyRows = selectedCurrencies
      .map((currencyId) => {
        const rowsForCurrency = locationRows.filter((r) => r.currencyId === currencyId);
        if (!rowsForCurrency.length) return null;

        return {
          currencyId,
          currencyLabel: rowsForCurrency[0].currencyLabel || currencyId,
          bestBuy: getBestBuyRow(rowsForCurrency, currencyId),
        };
      })
      .filter(Boolean);

    if (!filteredCurrencyRows.length) return;

    const ratePillsHtml = filteredCurrencyRows.map((item) => `
      <div class="rate-pill">
        <div class="label">${item.currencyLabel} compra</div>
        <div class="value">${item.bestBuy ? `${formatCop(item.bestBuy.buy)} COP` : "—"}</div>
      </div>
    `).join("");

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
          ${ratePillsHtml}
          <div class="rate-pill">
            <div class="label">Monedas filtradas</div>
            <div class="value">${filteredCurrencyRows.length}</div>
          </div>
        </div>
      </article>
    `);
  });

  exchangeGrid.innerHTML = locations.join("");
}

function renderCurrencyGrid(cityRows) {
  const currencyIds = getDistinctCurrencies(cityRows);

  const cards = currencyIds.map((currencyId) => {
    const rows = cityRows.filter((row) => row.currencyId === currencyId);
    const bestBuy = getBestBuyRow(rows, currencyId);
    const bestSell = getBestSellRow(rows, currencyId);
    const displayName = rows[0]?.currencyLabel || currencyId;

    return `
      <article class="currency-card">
        <h3>${displayName}</h3>
        <div class="currency-line"><strong>Mejor compra</strong><br>${bestBuy ? `<a href="${bestBuy.sourceUrl}" target="_blank" rel="noopener noreferrer">${prettyHouseName(bestBuy.locationId)}</a> · ${formatCop(bestBuy.buy)} COP` : "—"}</div>
        <div class="currency-line"><strong>Menor venta</strong><br>${bestSell ? `<a href="${bestSell.sourceUrl}" target="_blank" rel="noopener noreferrer">${prettyHouseName(bestSell.locationId)}</a> · ${formatCop(bestSell.sell)} COP` : "—"}</div>
        ${bestBuy && bestSell ? `<div class="currency-line"><strong>Lectura del mercado</strong><br>La diferencia entre la mejor compra y la menor venta reportadas es de ${formatCop(bestSell.sell - bestBuy.buy)} COP.</div>` : ""}
      </article>
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

async function renderSelectedCurrencySections() {
  currentReferenceRates = await loadReferenceRatesForSelectedCurrencies(currentCityRows);
  renderHeroCounts(currentCityRows, currentReferenceRates);
  renderHeroRates(currentCityRows, currentReferenceRates);
  renderSummary(currentCityRows);
  renderExchangeGrid(currentCityRows);
}

async function renderCity(city, resetCurrencySelection) {
  currentCity = city;
  citySelector.value = city;
  mobileCitySelector.value = city;

  currentCityRows = getRowsByCity(city);
  currentComparisonMap = buildComparisonMap(rawData?.comparison_data, city);

  fillHeroCurrencySelectors(currentCityRows, Boolean(resetCurrencySelection));
  await renderSelectedCurrencySections();
  renderExchangeGrid(currentCityRows);
  renderCurrencyGrid(currentCityRows, currentComparisonMap);
  renderTable(currentCityRows);
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

    await renderCity(currentCity, true);

    citySelector.addEventListener("change", async () => {
      await renderCity(citySelector.value, true);
    });

    mobileCitySelector.addEventListener("change", async () => {
      await renderCity(mobileCitySelector.value, true);
    });

    heroCurrencySelector1.addEventListener("change", async () => {
      selectedHeroCurrencies[0] = heroCurrencySelector1.value;
      await renderSelectedCurrencySections();
    });

    heroCurrencySelector2.addEventListener("change", async () => {
      selectedHeroCurrencies[1] = heroCurrencySelector2.value;
      await renderSelectedCurrencySections();
    });
  } catch (err) {
    console.error(err);
    setLoadStatus("No se pudo cargar la información disponible en este momento.", true);
  }
}

function initMobileMenu() {
  const mobileMenuBtn = document.getElementById("mobileMenuBtn");
  const mobileMenu = document.getElementById("mobileMenu");
  const mobileMenuOverlay = document.getElementById("mobileMenuOverlay");
  const mobileMenuClose = document.getElementById("mobileMenuClose");
  const mobileNavLinks = document.querySelectorAll(".mobile-nav-links a");

  if (!mobileMenuBtn || !mobileMenu || !mobileMenuOverlay || !mobileMenuClose) {
    return;
  }

  function openMobileMenu() {
    mobileMenu.classList.add("open");
    mobileMenuOverlay.classList.add("open");
    document.body.classList.add("menu-open");
  }

  function closeMobileMenu() {
    mobileMenu.classList.remove("open");
    mobileMenuOverlay.classList.remove("open");
    document.body.classList.remove("menu-open");
  }

  mobileMenuBtn.addEventListener("click", function (event) {
    event.preventDefault();
    event.stopPropagation();
    openMobileMenu();
  });

  mobileMenuClose.addEventListener("click", function (event) {
    event.preventDefault();
    closeMobileMenu();
  });

  mobileMenuOverlay.addEventListener("click", closeMobileMenu);

  mobileNavLinks.forEach((link) => {
    link.addEventListener("click", closeMobileMenu);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeMobileMenu();
    }
  });
}

document.addEventListener("DOMContentLoaded", function () {
  initMobileMenu();
  init();
});
