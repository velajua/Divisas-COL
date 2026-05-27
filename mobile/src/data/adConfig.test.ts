import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_MOBILE_ADS_CONFIG,
  MOBILE_ADS_CONFIG_URL,
  fetchMobileAdsConfig,
  normalizeMobileAdsConfig,
} from "./adConfig";

test("MOBILE_ADS_CONFIG_URL uses the canonical host without a redirect", () => {
  assert.equal(MOBILE_ADS_CONFIG_URL, "https://divisascol.com/mobile-ads.json");
});

test("normalizeMobileAdsConfig keeps valid remote banner and native ad unit ids", () => {
  assert.deepEqual(
    normalizeMobileAdsConfig({
      enabled: true,
      banner: {
        enabled: true,
        androidAdUnitId: "ca-app-pub-1234567890123456/1111111111",
      },
      native: {
        enabled: true,
        androidAdUnitId: "ca-app-pub-1234567890123456/2222222222",
      },
    }),
    {
      enabled: true,
      banner: {
        enabled: true,
        androidAdUnitId: "ca-app-pub-1234567890123456/1111111111",
      },
      native: {
        enabled: true,
        androidAdUnitId: "ca-app-pub-1234567890123456/2222222222",
      },
    },
  );
});

test("normalizeMobileAdsConfig disables placements with missing or invalid ids", () => {
  assert.deepEqual(
    normalizeMobileAdsConfig({
      enabled: true,
      banner: {
        enabled: true,
        androidAdUnitId: "not-an-ad-unit",
      },
      native: {
        enabled: true,
      },
    }),
    DEFAULT_MOBILE_ADS_CONFIG,
  );
});

test("fetchMobileAdsConfig falls back to disabled ads when the remote config cannot load", async () => {
  const config = await fetchMobileAdsConfig(MOBILE_ADS_CONFIG_URL, async () => ({
    ok: false,
    status: 404,
  }) as Response);

  assert.deepEqual(config, DEFAULT_MOBILE_ADS_CONFIG);
});

test("fetchMobileAdsConfig times out slow remote config requests", async () => {
  const startedAt = Date.now();
  const config = await fetchMobileAdsConfig(
    MOBILE_ADS_CONFIG_URL,
    async () => new Promise<Response>(() => {}),
    10,
  );

  assert.deepEqual(config, DEFAULT_MOBILE_ADS_CONFIG);
  assert.ok(Date.now() - startedAt < 250);
});
