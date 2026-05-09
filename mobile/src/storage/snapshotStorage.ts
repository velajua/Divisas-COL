import AsyncStorage from "@react-native-async-storage/async-storage";

import type { Snapshot } from "../data/snapshotCache";

const SNAPSHOTS_KEY = "divisascol:snapshots:v1";

export async function loadSnapshots(): Promise<Snapshot[]> {
  const raw = await AsyncStorage.getItem(SNAPSHOTS_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    return [];
  }
}

export async function saveSnapshots(snapshots: Snapshot[]): Promise<void> {
  await AsyncStorage.setItem(SNAPSHOTS_KEY, JSON.stringify(snapshots));
}
