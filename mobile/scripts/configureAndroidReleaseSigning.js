const fs = require("node:fs");
const path = require("node:path");

const SIGNING_CONFIG = `        release {
            storeFile file(System.getenv("DIVISAS_UPLOAD_STORE_FILE"))
            storePassword System.getenv("DIVISAS_UPLOAD_STORE_PASSWORD")
            keyAlias System.getenv("DIVISAS_UPLOAD_KEY_ALIAS")
            keyPassword System.getenv("DIVISAS_UPLOAD_KEY_PASSWORD")
        }`;

function addReleaseSigningConfig(contents) {
  if (contents.includes("DIVISAS_UPLOAD_STORE_FILE")) {
    return contents;
  }

  const debugConfigEnd = /(\s*debug\s*\{[\s\S]*?\n\s{8}\})/;
  if (!debugConfigEnd.test(contents)) {
    throw new Error("Could not find Android debug signing config block.");
  }

  return contents.replace(debugConfigEnd, `$1\n${SIGNING_CONFIG}`);
}

function useReleaseSigningConfig(contents) {
  const buildTypesAt = contents.indexOf("buildTypes {");
  if (buildTypesAt === -1) {
    throw new Error("Could not find Android buildTypes block.");
  }

  const beforeBuildTypes = contents.slice(0, buildTypesAt);
  const buildTypesAndAfter = contents.slice(buildTypesAt);
  const releaseSigningConfig = /(\n\s*release\s*\{[\s\S]*?\n\s*signingConfig\s+signingConfigs\.)\w+/;
  if (!releaseSigningConfig.test(buildTypesAndAfter)) {
    throw new Error("Could not find Android release build type signingConfig.");
  }

  return beforeBuildTypes + buildTypesAndAfter.replace(releaseSigningConfig, "$1release");
}

function configureAndroidReleaseSigning(contents) {
  return useReleaseSigningConfig(addReleaseSigningConfig(contents));
}

function configureBuildGradle(buildGradlePath) {
  const original = fs.readFileSync(buildGradlePath, "utf8");
  const next = configureAndroidReleaseSigning(original);
  if (next !== original) {
    fs.writeFileSync(buildGradlePath, next);
  }
}

function main() {
  const buildGradlePath = path.join(__dirname, "..", "android", "app", "build.gradle");
  configureBuildGradle(buildGradlePath);
  console.log(`Configured release signing in ${buildGradlePath}`);
}

if (require.main === module) {
  main();
}

module.exports = {
  addReleaseSigningConfig,
  configureAndroidReleaseSigning,
  useReleaseSigningConfig,
};
