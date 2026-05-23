type GoogleMobileAdsModule = typeof import("react-native-google-mobile-ads");
type Env = Partial<Record<string, string | undefined>>;

const runtimeEnv: Env =
  typeof process === "undefined"
    ? {}
    : {
        TESTING_EXPO: process.env.TESTING_EXPO,
        EXPO_PUBLIC_TESTING_EXPO: process.env.EXPO_PUBLIC_TESTING_EXPO,
      };

export function loadGoogleMobileAdsForPlatform(
  platformOS: string,
  moduleLoader: () => GoogleMobileAdsModule,
  env: Env = runtimeEnv,
): GoogleMobileAdsModule | null {
  if (env.TESTING_EXPO === "1" || env.EXPO_PUBLIC_TESTING_EXPO === "1") return null;
  if (platformOS !== "android") return null;

  try {
    return moduleLoader();
  } catch {
    return null;
  }
}
