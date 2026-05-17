import AsyncStorage from "@react-native-async-storage/async-storage";

import type { LanguageCode } from "../data/settings";
import { sanitizeSnapshots, type Snapshot } from "../data/snapshotCache";

const SNAPSHOTS_KEY = "divisascol:snapshots:v1";
const PREFERENCES_KEY = "divisascol:preferences:v1";

export type AppPreferences = {
  language?: LanguageCode;
  country?: string;
};

export async function loadSnapshots(): Promise<Snapshot[]> {
  const raw = await AsyncStorage.getItem(SNAPSHOTS_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    return sanitizeSnapshots(parsed);
  } catch (error) {
    return [];
  }
}

export async function saveSnapshots(snapshots: Snapshot[]): Promise<void> {
  await AsyncStorage.setItem(SNAPSHOTS_KEY, JSON.stringify(snapshots));
}

export async function loadPreferences(): Promise<AppPreferences> {
  const raw = await AsyncStorage.getItem(PREFERENCES_KEY);
  if (!raw) return {};

  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};

    const preferences = parsed as AppPreferences;
    return {
      language: preferences.language === "en" ? "en" : preferences.language === "es" ? "es" : undefined,
      country: typeof preferences.country === "string" ? preferences.country : undefined,
    };
  } catch (error) {
    return {};
  }
}

export async function savePreferences(preferences: AppPreferences): Promise<void> {
  await AsyncStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
}
