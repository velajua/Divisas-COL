import * as Location from "expo-location";
import { StatusBar } from "expo-status-bar";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Svg, { Path, Rect } from "react-native-svg";

import { fetchResultJson, RESULT_JSON_URL } from "./data/api";
import { inferNearestCity } from "./data/cityInference";
import {
  flattenRates,
  formatDisplayName,
  getBestRates,
  getCities,
  getCurrencies,
  type RateRow,
} from "./data/resultParser";
import { getSnapshotDate, type Snapshot, upsertSnapshot } from "./data/snapshotCache";
import { loadSnapshots, saveSnapshots } from "./storage/snapshotStorage";

type TabId = "today" | "history" | "rates" | "newsletter" | "info";
type DropdownId = "city" | "currency" | null;

const NEWSLETTER_URL = "https://www.divisascol.com/colombia/newsletter/";
const SITE_URL = "https://divisascol.com";
const DEFAULT_CURRENCY = "AmericanDollar";
const FRONT_PAGE_CURRENCIES = ["AmericanDollar", "Euro"];

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "today", label: "Inicio" },
  { id: "history", label: "Historial" },
  { id: "rates", label: "Tasas" },
  { id: "newsletter", label: "Newsletter" },
  { id: "info", label: "Datos" },
];

function formatCop(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${value.toLocaleString("es-CO")} COP`;
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

function RateCard({ label, row, valueType }: { label: string; row: RateRow | null; valueType: "buy" | "sell" }) {
  return (
    <View style={styles.rateCard}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={styles.rateValue}>{formatCop(row?.[valueType])}</Text>
      <Text style={styles.cardMeta}>
        {row ? `${formatDisplayName(row.exchangeHouse)} / ${formatDisplayName(row.locationId)}` : "Sin datos"}
      </Text>
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
}: {
  label: string;
  value: string;
  options: Array<{ id: string; label: string }>;
  open: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
}) {
  return (
    <View style={styles.dropdownBlock}>
      <Text style={styles.groupLabel}>{label}</Text>
      <Pressable onPress={onToggle} style={styles.dropdownButton}>
        <Text style={styles.dropdownValue}>{value || "Seleccionar"}</Text>
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
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedCity, setSelectedCity] = useState<string>("");
  const [selectedCurrency, setSelectedCurrency] = useState<string>(DEFAULT_CURRENCY);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [message, setMessage] = useState("Cargando tasas...");
  const [openDropdown, setOpenDropdown] = useState<DropdownId>(null);
  const locationRequestedRef = useRef(false);

  const selectedSnapshot = useMemo(
    () => snapshots.find((snapshot) => snapshot.date === selectedDate) || snapshots[0] || null,
    [selectedDate, snapshots],
  );
  const rows = useMemo(() => selectedSnapshot ? flattenRates(selectedSnapshot.data) : [], [selectedSnapshot]);
  const cities = useMemo(() => getCities(rows), [rows]);
  const currencies = useMemo(() => getCurrencies(rows), [rows]);
  const selectedCurrencyLabel = currencies.find((item) => item.id === selectedCurrency)?.label || "Dolar";

  async function applyLocationCity(rowsForLocation: RateRow[]) {
    if (locationRequestedRef.current || !rowsForLocation.length) return;
    locationRequestedRef.current = true;

    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") return;

      const position = await Location.getCurrentPositionAsync({});
      const inferredCity = inferNearestCity(
        {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        },
        getCities(rowsForLocation),
      );

      setSelectedCity(inferredCity);
    } catch (error) {
      console.error("No se pudo inferir la ciudad inicial", error);
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
      setMessage("Información actualizada.");
      await applyLocationCity(flattenRates(snapshot.data));
    } catch (error) {
      console.error("Failed to refresh result.json", error);
      if (existingSnapshots.length) {
        setMessage("Sin conexión. Mostrando datos guardados.");
      } else {
        setMessage("No pudimos cargar las tasas. Revisa la conexión y vuelve a abrir la app.");
      }
    } finally {
      setIsRefreshing(false);
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;

    async function load() {
      const saved = await loadSnapshots();
      if (!alive) return;

      setSnapshots(saved);
      setSelectedDate(saved[0]?.date || "");
      if (saved[0]) {
        await applyLocationCity(flattenRates(saved[0].data));
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

  function renderToday() {
    if (!selectedSnapshot) {
      return <EmptyState title="Sin tasas cargadas" body={message} />;
    }

    return (
      <>
        <SectionTitle eyebrow={selectedSnapshot.date} title={`Tasas en ${selectedCity || "Colombia"}`} />
        {FRONT_PAGE_CURRENCIES.map((currencyId) => {
          const label = currencies.find((currency) => currency.id === currencyId)?.label || currencyId;
          const rates = getBestRates(rows, selectedCity, currencyId);

          return (
            <View key={currencyId} style={styles.currencyBlock}>
              <Text style={styles.currencyTitle}>{label}</Text>
              <View style={styles.cardRow}>
                <RateCard label="Mejor compra" row={rates.bestBuy} valueType="buy" />
                <RateCard label="Menor venta" row={rates.bestSell} valueType="sell" />
              </View>
            </View>
          );
        })}
        <Text style={styles.muted}>{message}</Text>
      </>
    );
  }

  function renderHistory() {
    if (!snapshots.length) {
      return <EmptyState title="Sin historial" body="Abre la app con internet en distintos días para guardar hasta cinco cortes." />;
    }

    return (
      <>
        <SectionTitle eyebrow="Cortes guardados" title="Volver en el tiempo" />
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
              <Text style={styles.muted}>Actualizado {new Date(snapshot.fetchedAt).toLocaleString("es-CO")}</Text>
            </Pressable>
          ))}
        </View>
      </>
    );
  }

  function renderRates() {
    if (!rows.length) {
      return <EmptyState title="Sin tasas disponibles" body={message} />;
    }

    const visibleRows = rows
      .filter((row) => row.city === selectedCity && row.currencyId === selectedCurrency)
      .slice(0, 40);

    return (
      <>
        <SectionTitle eyebrow="Explorar" title="Ciudades y monedas" />
        <View style={styles.filterPanel}>
          <Dropdown
            label="Ciudad"
            value={selectedCity}
            options={cities.map((city) => ({ id: city, label: city }))}
            open={openDropdown === "city"}
            onToggle={() => setOpenDropdown(openDropdown === "city" ? null : "city")}
            onSelect={(city) => {
              setSelectedCity(city);
              setOpenDropdown(null);
            }}
          />
          <Dropdown
            label="Moneda"
            value={selectedCurrencyLabel}
            options={currencies}
            open={openDropdown === "currency"}
            onToggle={() => setOpenDropdown(openDropdown === "currency" ? null : "currency")}
            onSelect={(currency) => {
              setSelectedCurrency(currency);
              setOpenDropdown(null);
            }}
          />
        </View>
        <View style={styles.table}>
          {visibleRows.map((row) => (
            <View key={`${row.locationId}-${row.currencyLabel}-${row.buy}-${row.sell}`} style={styles.rateRow}>
              <View style={styles.rateRowMain}>
                <Text style={styles.rowTitle}>{formatDisplayName(row.exchangeHouse)}</Text>
                <Text style={styles.muted}>{formatDisplayName(row.locationId)}</Text>
              </View>
              <View style={styles.rateRowValues}>
                <Text style={styles.rowValue}>Compra {formatCop(row.buy)}</Text>
                <Text style={styles.rowValue}>Venta {formatCop(row.sell)}</Text>
              </View>
            </View>
          ))}
        </View>
      </>
    );
  }

  function renderNewsletter() {
    return (
      <>
        <SectionTitle eyebrow="Web" title="Newsletter" />
        <View style={styles.panel}>
          <Text style={styles.bodyText}>
            El newsletter vive en la web de Divisas COL. Ábrelo allí para leer entradas o suscribirte.
          </Text>
          <Pressable style={styles.primaryButton} onPress={() => Linking.openURL(NEWSLETTER_URL)}>
            <Text style={styles.primaryButtonText}>Abrir newsletter</Text>
          </Pressable>
        </View>
      </>
    );
  }

  function renderInfo() {
    return (
      <>
        <SectionTitle eyebrow="Datos" title="Estado de la app" />
        <View style={styles.panel}>
          <Text style={styles.infoLine}>Sitio: {SITE_URL}</Text>
          <Text style={styles.infoLine}>Días guardados: {snapshots.length} / 5</Text>
          <Text style={styles.infoLine}>Fecha seleccionada: {selectedSnapshot?.date || "-"}</Text>
          <Text style={styles.infoLine}>Última actualización: {selectedSnapshot ? new Date(selectedSnapshot.fetchedAt).toLocaleString("es-CO") : "-"}</Text>
          <Text style={styles.infoLine}>
            Privacidad: la ubicación solo se usa en este dispositivo para escoger la ciudad inicial más cercana. No la
            guardamos ni la enviamos a Divisas COL.
          </Text>
          <Text style={styles.muted}>{message}</Text>
          <Pressable
            style={[styles.primaryButton, isRefreshing && styles.pressedButton]}
            onPress={() => refreshRates(snapshots)}
          >
            <Text style={styles.primaryButtonText}>{isRefreshing ? "Solicitando..." : "Actualizar datos"}</Text>
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
          <Text style={styles.muted}>Cargando tasas guardadas...</Text>
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
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <LogoMark size={46} />
          <View style={styles.brandTextBlock}>
            <Text style={styles.brand}>Divisas COL</Text>
            <Text style={styles.subtitle}>Tasas guardadas para consultar sin conexión</Text>
          </View>
        </View>
      </View>
      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {renderContent()}
      </ScrollView>
      <View style={[styles.tabBar, Platform.OS === "android" && styles.androidTabBar]}>
        {TABS.map((tab) => (
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
    backgroundColor: "#fffaf1",
    borderColor: "#e4d6bb",
    borderRadius: 8,
    borderWidth: 1,
    gap: 10,
    padding: 14,
  },
  rateRowMain: {
    gap: 3,
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
