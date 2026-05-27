import * as Location from "expo-location";
import { StatusBar } from "expo-status-bar";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  NativeModules,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Svg, { Path, Rect } from "react-native-svg";

import { MobileBannerAd, MobileNativeAd } from "./components/MobileAds";
import { DEFAULT_MOBILE_ADS_CONFIG, fetchMobileAdsConfig, type MobileAdsConfig } from "./data/adConfig";
import { fetchResultJson, RESULT_JSON_URL } from "./data/api";
import { getHeaderSubtitle, type MessageKey } from "./data/appStatus";
import { inferNearestCity } from "./data/cityInference";
import {
  flattenRates,
  formatDisplayName,
  getBestRates,
  getCities,
  getCountries,
  getCurrencies,
  type RateRow,
} from "./data/resultParser";
import {
  buildCountrySiteUrl,
  buildNewsletterUrl,
  buildPrivacyPolicyUrl,
  normalizeLanguage,
  pickDefaultCountry,
  type LanguageCode,
} from "./data/settings";
import { getSnapshotDate, type Snapshot, upsertSnapshot } from "./data/snapshotCache";
import { loadPreferences, loadSnapshots, savePreferences, saveSnapshots } from "./storage/snapshotStorage";

type TabId = "today" | "history" | "rates" | "newsletter" | "info";
type DropdownId = "city" | "currency" | "country" | "language" | null;

const SITE_URL = "https://divisascol.com";
const DEFAULT_CURRENCY = "AmericanDollar";
const FRONT_PAGE_CURRENCIES = ["AmericanDollar", "Euro"];

const COPY = {
  es: {
    tabs: {
      today: "Inicio",
      history: "Historial",
      rates: "Tasas",
      newsletter: "Newsletter",
      info: "Datos",
    },
    loadingSubtitle: "Consultando las tasas más recientes",
    onlineSubtitle: "Tasas actualizadas desde Divisas COL",
    offlineSubtitle: "Tasas guardadas sin conexión",
    unavailableSubtitle: "Conéctate para cargar las tasas",
    loadingRates: "Cargando tasas...",
    loadingSaved: "Cargando tasas guardadas...",
    select: "Seleccionar",
    noData: "Sin datos",
    updated: "Información actualizada.",
    offline: "Sin conexión. Mostrando datos guardados.",
    loadFailed: "No pudimos cargar las tasas. Revisa la conexión y vuelve a abrir la app.",
    locationError: "No se pudo inferir la ubicación inicial",
    ratesEmptyTitle: "Sin tasas cargadas",
    todayTitle: (place: string) => `Tasas en ${place}`,
    bestBuy: "Mejor compra",
    bestSell: "Menor venta",
    savedCuts: "Cortes guardados",
    historyTitle: "Volver en el tiempo",
    noHistoryTitle: "Sin historial",
    noHistoryBody: "Abre la app con internet en distintos días para guardar hasta cinco cortes.",
    updatedAt: "Actualizado",
    explore: "Explorar",
    cityCurrencyTitle: "Ciudades y monedas",
    city: "Ciudad",
    country: "País",
    currency: "Moneda",
    language: "Idioma",
    buy: "Compra",
    sell: "Venta",
    web: "Web",
    open: "Abrir",
    openSite: "Abrir sitio",
    newsletterTitle: "Newsletter",
    newsletterBody: "El newsletter vive en la web de Divisas COL. Ábrelo allí para leer entradas o suscribirte.",
    openNewsletter: "Abrir newsletter",
    data: "Datos",
    appStatus: "Estado de la app",
    site: "Sitio",
    savedDays: "Días guardados",
    selectedDate: "Fecha seleccionada",
    selectedCountry: "País seleccionado",
    selectedLanguage: "Idioma seleccionado",
    lastUpdate: "Última actualización",
    privacyTitle: "Privacidad y anuncios",
    privacy: "La ubicación solo se usa en este dispositivo para escoger el país y la ciudad iniciales. Divisas COL no la guarda. La app muestra anuncios con Google AdMob, que puede procesar identificadores del dispositivo o publicidad según sus políticas.",
    seePolicies: "Ver políticas",
    requestData: "Solicitando...",
    refreshData: "Actualizar datos",
    spanish: "Español",
    english: "Inglés",
  },
  en: {
    tabs: {
      today: "Home",
      history: "History",
      rates: "Rates",
      newsletter: "Newsletter",
      info: "Data",
    },
    loadingSubtitle: "Checking latest exchange rates",
    onlineSubtitle: "Latest exchange rates from Divisas COL",
    offlineSubtitle: "Saved offline exchange rates",
    unavailableSubtitle: "Connect to load exchange rates",
    loadingRates: "Loading rates...",
    loadingSaved: "Loading saved rates...",
    select: "Select",
    noData: "No data",
    updated: "Information updated.",
    offline: "Offline. Showing saved data.",
    loadFailed: "We could not load rates. Check your connection and reopen the app.",
    locationError: "Could not infer the initial location",
    ratesEmptyTitle: "No rates loaded",
    todayTitle: (place: string) => `Rates in ${place}`,
    bestBuy: "Best buy",
    bestSell: "Lowest sell",
    savedCuts: "Saved snapshots",
    historyTitle: "Go back in time",
    noHistoryTitle: "No history",
    noHistoryBody: "Open the app with internet on different days to save up to five snapshots.",
    updatedAt: "Updated",
    explore: "Explore",
    cityCurrencyTitle: "Cities and currencies",
    city: "City",
    country: "Country",
    currency: "Currency",
    language: "Language",
    buy: "Buy",
    sell: "Sell",
    web: "Web",
    open: "Open",
    openSite: "Open site",
    newsletterTitle: "Newsletter",
    newsletterBody: "The Divisas COL newsletter lives on the web. Open it there to read posts or subscribe.",
    openNewsletter: "Open newsletter",
    data: "Data",
    appStatus: "App status",
    site: "Site",
    savedDays: "Saved days",
    selectedDate: "Selected date",
    selectedCountry: "Selected country",
    selectedLanguage: "Selected language",
    lastUpdate: "Last update",
    privacyTitle: "Privacy and ads",
    privacy: "Location is only used on this device to choose the initial country and nearest city. Divisas COL does not store it. The app shows ads with Google AdMob, which may process device or advertising identifiers under its policies.",
    seePolicies: "See policies",
    requestData: "Requesting...",
    refreshData: "Refresh data",
    spanish: "Spanish",
    english: "English",
  },
};

function getDeviceLanguage(): LanguageCode {
  const settings = NativeModules.SettingsManager?.settings;
  const locale = settings?.AppleLocale || settings?.AppleLanguages?.[0] || NativeModules.I18nManager?.localeIdentifier;
  return normalizeLanguage(locale);
}

function formatCop(value: number | null | undefined, language: LanguageCode): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${value.toLocaleString(language === "en" ? "en-US" : "es-CO")} COP`;
}

function pickDefaultCity(rows: RateRow[]): string {
  const cities = getCities(rows);
  return cities.includes("Bogota") ? "Bogota" : (cities[0] || "");
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionAccent} />
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

function LogoMark({ size = 44 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 512 512">
      <Rect width="512" height="512" rx="92" fill="#0f0e0c" />
      <Path
        fill="#f2d39b"
        d="M75 104H195C371 104 425 196 425 256C425 316 371 408 195 408H75V408H125V182H195V330H125V104H75Z"
      />
      <Path fill="#0f0e0c" d="M183 154C340 154 378 208 378 256C378 304 340 358 183 358Z" />
      <Path
        d="M326 216A64 64 0 1 0 326 296"
        stroke="#f2d39b"
        strokeWidth="28"
        strokeLinecap="round"
        fill="none"
      />
    </Svg>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.muted}>{body}</Text>
    </View>
  );
}

function RateCard({
  label,
  row,
  valueType,
  language,
  noDataLabel,
  openLabel,
}: {
  label: string;
  row: RateRow | null;
  valueType: "buy" | "sell";
  language: LanguageCode;
  noDataLabel: string;
  openLabel: string;
}) {
  return (
    <View style={styles.rateCard}>
      <View style={styles.rateCardContent}>
        <View style={styles.rateCardText}>
          <Text style={styles.cardLabel}>{label}</Text>
          <Text style={styles.rateValue}>{formatCop(row?.[valueType], language)}</Text>
          <Text style={styles.cardMeta}>
            {row ? `${formatDisplayName(row.exchangeHouse)} / ${formatDisplayName(row.locationId)}` : noDataLabel}
          </Text>
        </View>
        {row?.sourceUrl ? (
          <Pressable style={styles.inlineButton} onPress={() => Linking.openURL(row.sourceUrl)}>
            <Text style={styles.inlineButtonText}>{openLabel}</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

function Dropdown({
  label,
  value,
  options,
  open,
  onToggle,
  onSelect,
  placeholder,
}: {
  label: string;
  value: string;
  options: Array<{ id: string; label: string }>;
  open: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
  placeholder: string;
}) {
  return (
    <View style={styles.dropdownBlock}>
      <Text style={styles.groupLabel}>{label}</Text>
      <Pressable onPress={onToggle} style={styles.dropdownButton}>
        <Text style={styles.dropdownValue}>{value || placeholder}</Text>
        <Text style={styles.dropdownChevron}>{open ? "^" : "v"}</Text>
      </Pressable>
      {open ? (
        <View style={styles.dropdownMenu}>
          {options.map((option) => (
            <Pressable
              key={option.id}
              onPress={() => onSelect(option.id)}
              style={[styles.dropdownItem, option.label === value && styles.dropdownItemSelected]}
            >
              <Text style={[styles.dropdownItemText, option.label === value && styles.dropdownItemTextSelected]}>
                {option.label}
              </Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

export default function AppRoot() {
  const [activeTab, setActiveTab] = useState<TabId>("today");
  const [language, setLanguage] = useState<LanguageCode>(getDeviceLanguage);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedCountry, setSelectedCountry] = useState<string>("");
  const [selectedCity, setSelectedCity] = useState<string>("");
  const [selectedCurrency, setSelectedCurrency] = useState<string>(DEFAULT_CURRENCY);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [messageKey, setMessageKey] = useState<MessageKey>("loadingRates");
  const [openDropdown, setOpenDropdown] = useState<DropdownId>(null);
  const [mobileAdsConfig, setMobileAdsConfig] = useState<MobileAdsConfig>(DEFAULT_MOBILE_ADS_CONFIG);
  const locationRequestedRef = useRef(false);
  const userCountryRef = useRef(false);
  const t = COPY[language];
  const message = t[messageKey];
  const headerSubtitle = getHeaderSubtitle(messageKey, t);
  const tabs = useMemo<Array<{ id: TabId; label: string }>>(() => [
    { id: "today", label: t.tabs.today },
    { id: "history", label: t.tabs.history },
    { id: "rates", label: t.tabs.rates },
    { id: "newsletter", label: t.tabs.newsletter },
    { id: "info", label: t.tabs.info },
  ], [t]);

  const selectedSnapshot = useMemo(
    () => snapshots.find((snapshot) => snapshot.date === selectedDate) || snapshots[0] || null,
    [selectedDate, snapshots],
  );
  const allRows = useMemo(() => selectedSnapshot ? flattenRates(selectedSnapshot.data) : [], [selectedSnapshot]);
  const countries = useMemo(() => getCountries(allRows), [allRows]);
  const rows = useMemo(
    () => allRows.filter((row) => !selectedCountry || row.country === selectedCountry),
    [allRows, selectedCountry],
  );
  const cities = useMemo(() => getCities(rows), [rows]);
  const currencies = useMemo(() => getCurrencies(rows, language), [language, rows]);
  const selectedCountryLabel = countries.find((item) => item.id === selectedCountry)?.label || formatDisplayName(selectedCountry || "colombia");
  const selectedCurrencyLabel = currencies.find((item) => item.id === selectedCurrency)?.label || "Dollar";
  const countrySiteUrl = buildCountrySiteUrl(SITE_URL, language, selectedCountry);
  const newsletterUrl = buildNewsletterUrl(SITE_URL, language, selectedCountry);
  const privacyPolicyUrl = buildPrivacyPolicyUrl(SITE_URL, language);
  const languageOptions = useMemo(() => [
    { id: "es", label: t.spanish },
    { id: "en", label: t.english },
  ], [t]);

  async function applyLocationDefaults(rowsForLocation: RateRow[], preferredCountry?: string) {
    if (locationRequestedRef.current || !rowsForLocation.length) return;
    locationRequestedRef.current = true;

    let countryForCity = preferredCountry || selectedCountry;

    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        if (!countryForCity) {
          setSelectedCountry(pickDefaultCountry(getCountries(rowsForLocation), null));
        }
        return;
      }

      const position = await Location.getCurrentPositionAsync({});
      const geocoded = await Location.reverseGeocodeAsync(position.coords);
      const detectedCountry = geocoded[0]?.isoCountryCode || geocoded[0]?.country;
      const nextCountry = preferredCountry || pickDefaultCountry(getCountries(rowsForLocation), detectedCountry);

      countryForCity = nextCountry;
      if (!userCountryRef.current) {
        setSelectedCountry(nextCountry);
      }

      const rowsInCountry = rowsForLocation.filter((row) => row.country === countryForCity);
      const inferredCity = inferNearestCity(
        {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        },
        getCities(rowsInCountry.length ? rowsInCountry : rowsForLocation),
      );

      setSelectedCity(inferredCity);
    } catch (error) {
      console.error(t.locationError, error);
      if (!countryForCity) {
        setSelectedCountry(pickDefaultCountry(getCountries(rowsForLocation), null));
      }
    }
  }

  async function refreshRates(existingSnapshots = snapshots) {
    if (isRefreshing) return;

    setIsRefreshing(true);

    try {
      const data = await fetchResultJson();
      const now = new Date();
      const snapshot: Snapshot = {
        date: getSnapshotDate(data, now),
        fetchedAt: now.toISOString(),
        data,
      };
      const nextSnapshots = upsertSnapshot(existingSnapshots, snapshot, 5);

      await saveSnapshots(nextSnapshots);
      setSnapshots(nextSnapshots);
      setSelectedDate(snapshot.date);
      setMessageKey("updated");
      await applyLocationDefaults(flattenRates(snapshot.data), selectedCountry);
    } catch (error) {
      console.error("Failed to refresh result.json", error);
      if (existingSnapshots.length) {
        setMessageKey("offline");
      } else {
        setMessageKey("loadFailed");
      }
    } finally {
      setIsRefreshing(false);
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;

    async function load() {
      void fetchMobileAdsConfig().then((adsConfig) => {
        if (alive) {
          setMobileAdsConfig(adsConfig);
        }
      });

      const [saved, preferences] = await Promise.all([
        loadSnapshots(),
        loadPreferences(),
      ]);
      if (!alive) return;

      if (preferences.language) {
        setLanguage(preferences.language);
      }
      if (preferences.country) {
        userCountryRef.current = true;
        setSelectedCountry(preferences.country);
      }
      setSnapshots(saved);
      setSelectedDate(saved[0]?.date || "");
      if (saved[0]) {
        await applyLocationDefaults(flattenRates(saved[0].data), preferences.country);
      }
      await refreshRates(saved);
    }

    load();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!rows.length) return;

    const nextCity = selectedCity && cities.includes(selectedCity) ? selectedCity : pickDefaultCity(rows);
    if (nextCity !== selectedCity) {
      setSelectedCity(nextCity);
    }

    if (!currencies.some((currency) => currency.id === selectedCurrency)) {
      setSelectedCurrency(currencies[0]?.id || DEFAULT_CURRENCY);
    }
  }, [cities, currencies, rows, selectedCity, selectedCurrency]);

  useEffect(() => {
    if (!allRows.length || selectedCountry) return;

    setSelectedCountry(pickDefaultCountry(countries, null));
  }, [allRows, countries, selectedCountry]);

  function renderToday() {
    if (!selectedSnapshot) {
      return <EmptyState title={t.ratesEmptyTitle} body={message} />;
    }

    return (
      <>
        <SectionTitle eyebrow={selectedSnapshot.date} title={t.todayTitle(selectedCity || selectedCountryLabel)} />
        {FRONT_PAGE_CURRENCIES.map((currencyId) => {
          const label = currencies.find((currency) => currency.id === currencyId)?.label || currencyId;
          const rates = getBestRates(rows, selectedCity, currencyId);

          return (
            <View key={currencyId} style={styles.currencyBlock}>
              <Text style={styles.currencyTitle}>{label}</Text>
              <View style={styles.cardRow}>
                <RateCard
                  label={t.bestBuy}
                  row={rates.bestBuy}
                  valueType="buy"
                  language={language}
                  noDataLabel={t.noData}
                  openLabel={t.open}
                />
                <RateCard
                  label={t.bestSell}
                  row={rates.bestSell}
                  valueType="sell"
                  language={language}
                  noDataLabel={t.noData}
                  openLabel={t.open}
                />
              </View>
            </View>
          );
        })}
        <MobileNativeAd placement={mobileAdsConfig.native} language={language} />
        <Text style={styles.muted}>{message}</Text>
      </>
    );
  }

  function renderHistory() {
    if (!snapshots.length) {
      return <EmptyState title={t.noHistoryTitle} body={t.noHistoryBody} />;
    }

    return (
      <>
        <SectionTitle eyebrow={t.savedCuts} title={t.historyTitle} />
        <View style={styles.stack}>
          {snapshots.map((snapshot) => (
            <Pressable
              key={snapshot.date}
              onPress={() => {
                setSelectedDate(snapshot.date);
                setActiveTab("today");
              }}
              style={[styles.historyItem, snapshot.date === selectedDate && styles.historyItemSelected]}
            >
              <Text style={styles.historyDate}>{snapshot.date}</Text>
              <Text style={styles.muted}>{t.updatedAt} {new Date(snapshot.fetchedAt).toLocaleString(language === "en" ? "en-US" : "es-CO")}</Text>
            </Pressable>
          ))}
        </View>
      </>
    );
  }

  function renderRates() {
    if (!rows.length) {
      return <EmptyState title={t.ratesEmptyTitle} body={message} />;
    }

    const visibleRows = rows
      .filter((row) => row.city === selectedCity && row.currencyId === selectedCurrency)
      .slice(0, 40);

    return (
      <>
        <SectionTitle eyebrow={t.explore} title={t.cityCurrencyTitle} />
        <View style={styles.filterPanel}>
          <Dropdown
            label={t.city}
            value={selectedCity}
            options={cities.map((city) => ({ id: city, label: city }))}
            open={openDropdown === "city"}
            onToggle={() => setOpenDropdown(openDropdown === "city" ? null : "city")}
            onSelect={(city) => {
              setSelectedCity(city);
              setOpenDropdown(null);
            }}
            placeholder={t.select}
          />
          <Dropdown
            label={t.currency}
            value={selectedCurrencyLabel}
            options={currencies}
            open={openDropdown === "currency"}
            onToggle={() => setOpenDropdown(openDropdown === "currency" ? null : "currency")}
            onSelect={(currency) => {
              setSelectedCurrency(currency);
              setOpenDropdown(null);
            }}
            placeholder={t.select}
          />
        </View>
        <View style={styles.table}>
          {visibleRows.map((row) => (
            <View key={`${row.locationId}-${row.currencyLabel}-${row.buy}-${row.sell}`} style={styles.rateRow}>
              <View style={styles.rateRowContent}>
                <View style={styles.rateRowMain}>
                  <Text style={styles.rowTitle}>{formatDisplayName(row.exchangeHouse)}</Text>
                  <Text style={styles.muted}>{formatDisplayName(row.locationId)}</Text>
                </View>
                <View style={styles.rateRowValues}>
                  <Text style={styles.rowValue}>{t.buy} {formatCop(row.buy, language)}</Text>
                  <Text style={styles.rowValue}>{t.sell} {formatCop(row.sell, language)}</Text>
                </View>
              </View>
              {row.sourceUrl ? (
                <Pressable style={styles.inlineButton} onPress={() => Linking.openURL(row.sourceUrl)}>
                  <Text style={styles.inlineButtonText}>{t.open}</Text>
                </Pressable>
              ) : null}
            </View>
          ))}
        </View>
      </>
    );
  }

  function renderNewsletter() {
    return (
      <>
        <SectionTitle eyebrow={t.web} title={t.newsletterTitle} />
        <View style={styles.panel}>
          <Text style={styles.bodyText}>{t.newsletterBody}</Text>
          <Pressable style={styles.primaryButton} onPress={() => Linking.openURL(newsletterUrl)}>
            <Text style={styles.primaryButtonText}>{t.openNewsletter}</Text>
          </Pressable>
        </View>
      </>
    );
  }

  function renderInfo() {
    return (
      <>
        <SectionTitle eyebrow={t.data} title={t.appStatus} />
        <View style={styles.panel}>
          <Dropdown
            label={t.language}
            value={languageOptions.find((option) => option.id === language)?.label || ""}
            options={languageOptions}
            open={openDropdown === "language"}
            onToggle={() => setOpenDropdown(openDropdown === "language" ? null : "language")}
            onSelect={(nextLanguage) => {
              const normalized = normalizeLanguage(nextLanguage);
              setLanguage(normalized);
              setOpenDropdown(null);
              savePreferences({ language: normalized, country: selectedCountry });
            }}
            placeholder={t.select}
          />
          <Dropdown
            label={t.country}
            value={selectedCountryLabel}
            options={countries}
            open={openDropdown === "country"}
            onToggle={() => setOpenDropdown(openDropdown === "country" ? null : "country")}
            onSelect={(country) => {
              userCountryRef.current = true;
              setSelectedCountry(country);
              setSelectedCity("");
              setOpenDropdown(null);
              savePreferences({ language, country });
            }}
            placeholder={t.select}
          />
          <Text style={styles.infoLine}>{t.site}: {SITE_URL}</Text>
          <Pressable style={styles.secondaryButton} onPress={() => Linking.openURL(countrySiteUrl)}>
            <Text style={styles.secondaryButtonText}>{t.openSite}</Text>
          </Pressable>
          <Text style={styles.spacedInfoLine}>{t.savedDays}: {snapshots.length} / 5</Text>
          <Text style={styles.infoLine}>{t.selectedDate}: {selectedSnapshot?.date || "-"}</Text>
          <Text style={styles.infoLine}>{t.selectedCountry}: {selectedCountryLabel}</Text>
          <Text style={styles.infoLine}>{t.selectedLanguage}: {languageOptions.find((option) => option.id === language)?.label}</Text>
          <Text style={styles.infoLine}>{t.lastUpdate}: {selectedSnapshot ? new Date(selectedSnapshot.fetchedAt).toLocaleString(language === "en" ? "en-US" : "es-CO") : "-"}</Text>
          <View style={styles.policyBox}>
            <Text style={styles.policyTitle}>{t.privacyTitle}</Text>
            <Text style={styles.infoLine}>{t.privacy}</Text>
            <Pressable style={styles.secondaryButton} onPress={() => Linking.openURL(privacyPolicyUrl)}>
              <Text style={styles.secondaryButtonText}>{t.seePolicies}</Text>
            </Pressable>
          </View>
          <Text style={styles.muted}>{message}</Text>
          <Pressable
            style={[styles.primaryButton, isRefreshing && styles.pressedButton]}
            onPress={() => refreshRates(snapshots)}
          >
            <Text style={styles.primaryButtonText}>{isRefreshing ? t.requestData : t.refreshData}</Text>
          </Pressable>
        </View>
      </>
    );
  }

  function renderContent() {
    if (isLoading) {
      return (
        <View style={styles.loading}>
          <ActivityIndicator color="#c9a227" />
          <Text style={styles.muted}>{t.loadingSaved}</Text>
        </View>
      );
    }

    if (activeTab === "today") return renderToday();
    if (activeTab === "history") return renderHistory();
    if (activeTab === "rates") return renderRates();
    if (activeTab === "newsletter") return renderNewsletter();
    return renderInfo();
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />
      <Pressable style={styles.header} onPress={() => Linking.openURL(SITE_URL)}>
        <View style={styles.brandRow}>
          <LogoMark size={46} />
          <View style={styles.brandTextBlock}>
            <Text style={styles.brand}>Divisas COL</Text>
            <Text style={styles.subtitle}>{headerSubtitle}</Text>
          </View>
        </View>
      </Pressable>
      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {renderContent()}
      </ScrollView>
      <MobileBannerAd placement={mobileAdsConfig.banner} />
      <View style={[styles.tabBar, Platform.OS === "android" && styles.androidTabBar]}>
        {tabs.map((tab) => (
          <Pressable
            key={tab.id}
            onPress={() => setActiveTab(tab.id)}
            style={[styles.tab, activeTab === tab.id && styles.tabActive]}
          >
            <Text style={[styles.tabText, activeTab === tab.id && styles.tabTextActive]}>{tab.label}</Text>
          </Pressable>
        ))}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#0f0e0c",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 34,
    paddingBottom: 18,
    backgroundColor: "#0f0e0c",
  },
  brandRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  brandTextBlock: {
    flex: 1,
  },
  brand: {
    color: "#f8efe0",
    fontSize: 28,
    fontWeight: "700",
  },
  subtitle: {
    color: "#d7c8ad",
    fontSize: 13,
    marginTop: 4,
  },
  content: {
    flex: 1,
    backgroundColor: "#f7f1e5",
  },
  contentInner: {
    padding: 18,
    paddingBottom: 28,
  },
  sectionHeader: {
    backgroundColor: "#171511",
    borderColor: "rgba(201, 169, 107, 0.18)",
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 16,
    overflow: "hidden",
    padding: 16,
  },
  sectionAccent: {
    backgroundColor: "#c9a96b",
    height: 3,
    left: 0,
    position: "absolute",
    right: 0,
    top: 0,
  },
  eyebrow: {
    color: "#f2d39b",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  title: {
    color: "#f7f1e5",
    fontSize: 24,
    fontWeight: "700",
    marginTop: 4,
  },
  cardRow: {
    gap: 12,
  },
  currencyBlock: {
    marginBottom: 18,
  },
  currencyTitle: {
    color: "#17130d",
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 8,
  },
  rateCard: {
    backgroundColor: "#fffaf1",
    borderColor: "#e4d6bb",
    borderRadius: 8,
    borderWidth: 1,
    padding: 16,
  },
  rateCardContent: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  rateCardText: {
    flex: 1,
    minWidth: 0,
  },
  cardLabel: {
    color: "#7a6230",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  rateValue: {
    color: "#17130d",
    fontSize: 26,
    fontWeight: "800",
    marginTop: 8,
  },
  cardMeta: {
    color: "#5d5345",
    fontSize: 13,
    marginTop: 6,
  },
  primaryButton: {
    alignItems: "center",
    backgroundColor: "#17130d",
    borderRadius: 8,
    marginTop: 16,
    padding: 14,
  },
  primaryButtonText: {
    color: "#f8efe0",
    fontSize: 15,
    fontWeight: "700",
  },
  pressedButton: {
    opacity: 0.72,
  },
  secondaryButton: {
    alignItems: "center",
    alignSelf: "flex-start",
    borderColor: "#17130d",
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  secondaryButtonText: {
    color: "#17130d",
    fontSize: 14,
    fontWeight: "700",
  },
  inlineButton: {
    alignItems: "center",
    alignSelf: "center",
    borderColor: "#17130d",
    borderRadius: 8,
    borderWidth: 1,
    minWidth: 72,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  inlineButtonText: {
    color: "#17130d",
    fontSize: 13,
    fontWeight: "800",
  },
  muted: {
    color: "#6d6254",
    fontSize: 13,
    marginTop: 8,
  },
  emptyState: {
    backgroundColor: "#fffaf1",
    borderColor: "#e4d6bb",
    borderRadius: 8,
    borderWidth: 1,
    padding: 18,
  },
  emptyTitle: {
    color: "#17130d",
    fontSize: 18,
    fontWeight: "700",
  },
  stack: {
    gap: 10,
  },
  historyItem: {
    backgroundColor: "#fffaf1",
    borderColor: "#e4d6bb",
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
  },
  historyItemSelected: {
    borderColor: "#c9a227",
    borderWidth: 2,
  },
  historyDate: {
    color: "#17130d",
    fontSize: 18,
    fontWeight: "700",
  },
  groupLabel: {
    color: "#f2d39b",
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 8,
    textTransform: "uppercase",
  },
  table: {
    gap: 10,
    marginTop: 14,
  },
  rateRow: {
    alignItems: "center",
    backgroundColor: "#fffaf1",
    borderColor: "#e4d6bb",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 10,
    padding: 14,
  },
  rateRowMain: {
    gap: 3,
  },
  rateRowContent: {
    flex: 1,
    gap: 10,
    minWidth: 0,
  },
  rowTitle: {
    color: "#17130d",
    fontSize: 16,
    fontWeight: "700",
  },
  rateRowValues: {
    gap: 4,
  },
  rowValue: {
    color: "#2c261f",
    fontSize: 14,
    fontWeight: "700",
  },
  panel: {
    backgroundColor: "#fffaf1",
    borderColor: "#d8b06c",
    borderRadius: 8,
    borderWidth: 1,
    padding: 16,
  },
  filterPanel: {
    backgroundColor: "#171511",
    borderColor: "rgba(201, 169, 107, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    gap: 14,
    padding: 14,
  },
  dropdownBlock: {
    gap: 0,
  },
  dropdownButton: {
    alignItems: "center",
    backgroundColor: "#241f19",
    borderColor: "rgba(242, 211, 155, 0.26)",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: 48,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  dropdownValue: {
    color: "#f7f1e5",
    flex: 1,
    fontSize: 16,
    fontWeight: "700",
  },
  dropdownChevron: {
    color: "#f2d39b",
    fontSize: 16,
    fontWeight: "800",
    marginLeft: 10,
  },
  dropdownMenu: {
    backgroundColor: "#fffaf1",
    borderColor: "#d8b06c",
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 8,
    overflow: "hidden",
  },
  dropdownItem: {
    borderBottomColor: "#eadcc3",
    borderBottomWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  dropdownItemSelected: {
    backgroundColor: "#f1dfbd",
  },
  dropdownItemText: {
    color: "#2c261f",
    fontSize: 15,
    fontWeight: "700",
  },
  dropdownItemTextSelected: {
    color: "#17130d",
  },
  bodyText: {
    color: "#2c261f",
    fontSize: 15,
    lineHeight: 22,
  },
  infoLine: {
    color: "#2c261f",
    fontSize: 14,
    marginBottom: 8,
  },
  spacedInfoLine: {
    color: "#2c261f",
    fontSize: 14,
    marginBottom: 8,
    marginTop: 18,
  },
  policyBox: {
    borderTopColor: "#eadcc3",
    borderTopWidth: 1,
    marginTop: 8,
    paddingTop: 12,
  },
  policyTitle: {
    color: "#17130d",
    fontSize: 15,
    fontWeight: "800",
    marginBottom: 6,
  },
  loading: {
    alignItems: "center",
    gap: 8,
    padding: 30,
  },
  tabBar: {
    backgroundColor: "#17130d",
    borderTopColor: "#352b1d",
    borderTopWidth: 1,
    flexDirection: "row",
    paddingHorizontal: 6,
    paddingVertical: 8,
  },
  androidTabBar: {
    paddingBottom: 56,
  },
  tab: {
    alignItems: "center",
    borderRadius: 8,
    flex: 1,
    paddingHorizontal: 2,
    paddingVertical: 10,
  },
  tabActive: {
    backgroundColor: "#c9a227",
  },
  tabText: {
    color: "#d7c8ad",
    fontSize: 11,
    fontWeight: "700",
  },
  tabTextActive: {
    color: "#17130d",
  },
});
