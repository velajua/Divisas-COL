import assert from "node:assert/strict";
import test from "node:test";

import {
  getSnapshotDate,
  trimSnapshots,
  upsertSnapshot,
  type Snapshot,
} from "./snapshotCache";

test("getSnapshotDate prefers a date field from the payload", () => {
  assert.equal(
    getSnapshotDate({ generated_at: "2026-05-07T23:10:00Z" }, new Date("2026-05-08T10:00:00-05:00")),
    "2026-05-07",
  );
});

test("getSnapshotDate falls back to the local fetch date", () => {
  assert.equal(getSnapshotDate({}, new Date(2026, 4, 8, 9, 0)), "2026-05-08");
});

test("upsertSnapshot replaces same-day data and keeps newest snapshots first", () => {
  const existing: Snapshot[] = [
    { date: "2026-05-07", fetchedAt: "2026-05-07T10:00:00.000Z", data: { old: true } },
    { date: "2026-05-06", fetchedAt: "2026-05-06T10:00:00.000Z", data: { older: true } },
  ];

  const result = upsertSnapshot(existing, {
    date: "2026-05-07",
    fetchedAt: "2026-05-07T18:00:00.000Z",
    data: { replacement: true },
  });

  assert.deepEqual(result.map((snapshot) => snapshot.date), ["2026-05-07", "2026-05-06"]);
  assert.deepEqual(result[0].data, { replacement: true });
});

test("trimSnapshots keeps the latest five dates", () => {
  const snapshots: Snapshot[] = ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05", "2026-05-06"]
    .map((date) => ({ date, fetchedAt: `${date}T12:00:00.000Z`, data: { date } }));

  const result = trimSnapshots(snapshots, 5);

  assert.deepEqual(result.map((snapshot) => snapshot.date), [
    "2026-05-06",
    "2026-05-05",
    "2026-05-04",
    "2026-05-03",
    "2026-05-02",
  ]);
});
