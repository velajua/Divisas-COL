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
