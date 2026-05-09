export type ResultPayload = Record<string, unknown>;

export type Snapshot = {
  date: string;
  fetchedAt: string;
  data: ResultPayload;
};

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

export function upsertSnapshot(snapshots: Snapshot[], snapshot: Snapshot, limit = 5): Snapshot[] {
  const withoutSameDate = snapshots.filter((item) => item.date !== snapshot.date);
  return trimSnapshots([snapshot, ...withoutSameDate], limit);
}
