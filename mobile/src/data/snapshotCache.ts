export type ResultPayload = Record<string, unknown>;

export type Snapshot = {
  date: string;
  fetchedAt: string;
  data: ResultPayload;
};

export function hasGroupedCityRates(data: unknown): data is ResultPayload {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;

  const groupedByCity = (data as { grouped_by_city?: unknown }).grouped_by_city;
  return Boolean(groupedByCity && typeof groupedByCity === "object" && !Array.isArray(groupedByCity));
}

export function assertResultPayload(data: unknown): asserts data is ResultPayload {
  if (!hasGroupedCityRates(data)) {
    throw new Error("Invalid result.json: missing grouped city rates.");
  }
}

function isSnapshot(value: unknown): value is Snapshot {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;

  const snapshot = value as Partial<Snapshot>;
  return Boolean(
    snapshot.date &&
      snapshot.fetchedAt &&
      typeof snapshot.date === "string" &&
      typeof snapshot.fetchedAt === "string" &&
      hasGroupedCityRates(snapshot.data),
  );
}

function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function readPayloadDate(data: ResultPayload): string | null {
  const candidates = [
    data.generated_at,
    data.generatedAt,
    data.date,
    data.updated_at,
    data.updatedAt,
  ];

  for (const candidate of candidates) {
    if (typeof candidate !== "string" || !candidate.trim()) continue;
    const parsed = new Date(candidate);
    if (!Number.isNaN(parsed.getTime())) {
      return candidate.slice(0, 10);
    }
  }

  return null;
}

export function getSnapshotDate(data: ResultPayload, fetchedAt: Date): string {
  return readPayloadDate(data) || toDateKey(fetchedAt);
}

export function trimSnapshots(snapshots: Snapshot[], limit = 5): Snapshot[] {
  return [...snapshots]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, limit);
}

export function sanitizeSnapshots(snapshots: unknown, limit = 5): Snapshot[] {
  if (!Array.isArray(snapshots)) return [];
  return trimSnapshots(snapshots.filter(isSnapshot), limit);
}

export function upsertSnapshot(snapshots: Snapshot[], snapshot: Snapshot, limit = 5): Snapshot[] {
  const withoutSameDate = snapshots.filter((item) => item.date !== snapshot.date);
  return trimSnapshots([snapshot, ...withoutSameDate], limit);
}
