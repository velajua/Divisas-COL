export const MOBILE_ADS_CONFIG_URL = "https://divisascol.com/mobile-ads.json";

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

export type MobileAdPlacementConfig = {
  enabled: boolean;
  androidAdUnitId: string;
};

export type MobileAdsConfig = {
  enabled: boolean;
  banner: MobileAdPlacementConfig;
  native: MobileAdPlacementConfig;
};

export const DEFAULT_MOBILE_ADS_CONFIG: MobileAdsConfig = {
  enabled: false,
  banner: {
    enabled: false,
    androidAdUnitId: "",
  },
  native: {
    enabled: false,
    androidAdUnitId: "",
  },
};

const ADMOB_AD_UNIT_ID_PATTERN = /^ca-app-pub-\d{16}\/\d{10}$/;

function normalizePlacement(value: unknown): MobileAdPlacementConfig {
  if (!value || typeof value !== "object") {
    return DEFAULT_MOBILE_ADS_CONFIG.banner;
  }

  const placement = value as Record<string, unknown>;
  const androidAdUnitId = typeof placement.androidAdUnitId === "string" ? placement.androidAdUnitId.trim() : "";
  const enabled = placement.enabled === true && ADMOB_AD_UNIT_ID_PATTERN.test(androidAdUnitId);

  return {
    enabled,
    androidAdUnitId: enabled ? androidAdUnitId : "",
  };
}

export function normalizeMobileAdsConfig(value: unknown): MobileAdsConfig {
  if (!value || typeof value !== "object") {
    return DEFAULT_MOBILE_ADS_CONFIG;
  }

  const config = value as Record<string, unknown>;
  if (config.enabled !== true) {
    return DEFAULT_MOBILE_ADS_CONFIG;
  }

  const banner = normalizePlacement(config.banner);
  const native = normalizePlacement(config.native);
  const enabled = banner.enabled || native.enabled;

  return enabled
    ? {
        enabled,
        banner,
        native,
      }
    : DEFAULT_MOBILE_ADS_CONFIG;
}

export async function fetchMobileAdsConfig(
  url = MOBILE_ADS_CONFIG_URL,
  fetchImpl: FetchLike = fetch,
): Promise<MobileAdsConfig> {
  try {
    const response = await fetchImpl(url, {
      headers: {
        "X-Divisas-Refresh-Intent": "background",
      },
    });

    if (!response.ok) {
      return DEFAULT_MOBILE_ADS_CONFIG;
    }

    return normalizeMobileAdsConfig(await response.json());
  } catch {
    return DEFAULT_MOBILE_ADS_CONFIG;
  }
}
