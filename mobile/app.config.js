const baseConfig = require("./app.json");
const fs = require("node:fs");
const path = require("node:path");

const sampleAndroidAppId = "ca-app-pub-3940256099942544~3347511713";
const sampleIosAppId = "ca-app-pub-3940256099942544~1458002511";

function loadDotEnv(filePath) {
  if (!fs.existsSync(filePath)) return;

  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;

    const equalsAt = trimmed.indexOf("=");
    const key = trimmed.slice(0, equalsAt).trim();
    const value = trimmed.slice(equalsAt + 1).trim().replace(/^["']|["']$/g, "");
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

loadDotEnv(path.join(__dirname, ".env"));

if (process.env.TESTING_EXPO === "1" && process.env.EXPO_PUBLIC_TESTING_EXPO === undefined) {
  process.env.EXPO_PUBLIC_TESTING_EXPO = "1";
}

const androidAppId = process.env.ADMOB_ANDROID_APP_ID || sampleAndroidAppId;
const iosAppId = process.env.ADMOB_IOS_APP_ID || sampleIosAppId;

module.exports = ({ config }) => ({
  ...config,
  ...baseConfig.expo,
  plugins: [
    ...(baseConfig.expo.plugins || []),
    [
      "react-native-google-mobile-ads",
      {
        androidAppId,
        iosAppId,
        delayAppMeasurementInit: true,
        optimizeInitialization: true,
        optimizeAdLoading: true,
      },
    ],
  ],
});
