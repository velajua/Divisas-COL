import assert from "node:assert/strict";
import { test } from "node:test";

import { loadGoogleMobileAdsForPlatform } from "./googleMobileAdsLoader";

test("loadGoogleMobileAdsForPlatform returns null when Android native module is missing", () => {
  const ads = loadGoogleMobileAdsForPlatform("android", () => {
    throw new Error(
      "TurboModuleRegistry.getEnforcing(...): 'RNGoogleMobileAdsModule' could not be found.",
    );
  });

  assert.equal(ads, null);
});

test("loadGoogleMobileAdsForPlatform skips loading AdMob when TESTING_EXPO is enabled", () => {
  let loaded = false;

  const ads = loadGoogleMobileAdsForPlatform("android", () => {
    loaded = true;
    throw new Error("AdMob should not load during Expo testing.");
  }, {
    TESTING_EXPO: "1",
  });

  assert.equal(ads, null);
  assert.equal(loaded, false);
});

test("loadGoogleMobileAdsForPlatform skips loading AdMob when EXPO_PUBLIC_TESTING_EXPO is enabled", () => {
  let loaded = false;

  const ads = loadGoogleMobileAdsForPlatform("android", () => {
    loaded = true;
    throw new Error("AdMob should not load during Expo testing.");
  }, {
    EXPO_PUBLIC_TESTING_EXPO: "1",
  });

  assert.equal(ads, null);
  assert.equal(loaded, false);
});
