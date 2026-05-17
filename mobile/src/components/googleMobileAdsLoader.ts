type GoogleMobileAdsModule = typeof import("react-native-google-mobile-ads");

export function loadGoogleMobileAdsForPlatform(
  platformOS: string,
  moduleLoader: () => GoogleMobileAdsModule,
): GoogleMobileAdsModule | null {
  if (platformOS !== "android") return null;

  try {
    return moduleLoader();
  } catch {
    return null;
  }
}
