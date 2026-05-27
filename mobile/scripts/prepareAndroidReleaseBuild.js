const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const SIGNING_DIR = "local-signing";
const SIGNING_ENV_FILE = "release-signing.env";
const SIGNING_CMD_FILE = "release-signing.cmd";
const KEYSTORE_FILE = "divisas-upload-key.jks";
const KEY_ALIAS = "divisas-upload";

const REQUIRED_SIGNING_KEYS = [
  "DIVISAS_UPLOAD_STORE_FILE",
  "DIVISAS_UPLOAD_STORE_PASSWORD",
  "DIVISAS_UPLOAD_KEY_ALIAS",
  "DIVISAS_UPLOAD_KEY_PASSWORD",
];

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};

  const values = {};
  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;

    const equalsAt = trimmed.indexOf("=");
    const key = trimmed.slice(0, equalsAt).trim();
    const value = trimmed.slice(equalsAt + 1).trim().replace(/^["']|["']$/g, "");
    if (key) values[key] = value;
  }

  return values;
}

function writeEnvFile(filePath, values) {
  const body = Object.entries(values)
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
  fs.writeFileSync(filePath, `${body}\n`);
}

function writeCmdEnvFile(filePath, values) {
  const body = [
    "@echo off",
    ...Object.entries(values).map(([key, value]) => `set "${key}=${value}"`),
  ].join("\r\n");
  fs.writeFileSync(filePath, `${body}\r\n`);
}

function randomSecret(randomBytes = crypto.randomBytes) {
  return randomBytes(16).toString("hex");
}

function validateSigningEnv(env) {
  const missing = REQUIRED_SIGNING_KEYS.filter((key) => !env[key]);
  if (missing.length) {
    throw new Error(`Missing Android release signing values: ${missing.join(", ")}`);
  }
}

function ensureReleaseSigning(projectRoot, options = {}) {
  const run = options.execFileSync || execFileSync;
  const randomBytes = options.randomBytes || crypto.randomBytes;
  const signingDir = path.join(projectRoot, SIGNING_DIR);
  const envPath = path.join(signingDir, SIGNING_ENV_FILE);
  const cmdPath = path.join(signingDir, SIGNING_CMD_FILE);
  const keystorePath = path.join(signingDir, KEYSTORE_FILE);

  fs.mkdirSync(signingDir, { recursive: true });

  const hadEnvFile = fs.existsSync(envPath);
  const existing = loadEnvFile(envPath);
  const env = {
    DIVISAS_UPLOAD_STORE_FILE: existing.DIVISAS_UPLOAD_STORE_FILE || keystorePath,
    DIVISAS_UPLOAD_STORE_PASSWORD: existing.DIVISAS_UPLOAD_STORE_PASSWORD || randomSecret(randomBytes),
    DIVISAS_UPLOAD_KEY_ALIAS: existing.DIVISAS_UPLOAD_KEY_ALIAS || KEY_ALIAS,
    DIVISAS_UPLOAD_KEY_PASSWORD: existing.DIVISAS_UPLOAD_KEY_PASSWORD || randomSecret(randomBytes),
  };

  validateSigningEnv(env);
  writeEnvFile(envPath, env);
  writeCmdEnvFile(cmdPath, env);

  if (!hadEnvFile && env.DIVISAS_UPLOAD_STORE_FILE === keystorePath && fs.existsSync(keystorePath)) {
    fs.rmSync(keystorePath);
  }

  if (!fs.existsSync(env.DIVISAS_UPLOAD_STORE_FILE)) {
    run("keytool", [
      "-genkeypair",
      "-v",
      "-storetype",
      "JKS",
      "-keystore",
      env.DIVISAS_UPLOAD_STORE_FILE,
      "-storepass",
      env.DIVISAS_UPLOAD_STORE_PASSWORD,
      "-alias",
      env.DIVISAS_UPLOAD_KEY_ALIAS,
      "-keypass",
      env.DIVISAS_UPLOAD_KEY_PASSWORD,
      "-keyalg",
      "RSA",
      "-keysize",
      "2048",
      "-validity",
      "10000",
      "-dname",
      "CN=Divisas COL, OU=Mobile, O=Divisas COL, L=Bogota, ST=Bogota, C=CO",
    ], { stdio: "inherit" });
  }

  return {
    cmdPath,
    env,
    envPath,
    keystorePath: env.DIVISAS_UPLOAD_STORE_FILE,
  };
}

function resolveAndroidSdkDir(projectRoot, env = process.env) {
  const bundledSdk = path.join(projectRoot, "android-sdk");
  if (fs.existsSync(bundledSdk)) return bundledSdk;
  if (env.ANDROID_HOME) return env.ANDROID_HOME;
  if (env.ANDROID_SDK_ROOT) return env.ANDROID_SDK_ROOT;
  throw new Error("Android SDK not found. Set ANDROID_HOME or install the bundled mobile/android-sdk.");
}

function escapeLocalPropertiesPath(value) {
  return value.replace(/\\/g, "\\\\");
}

function writeAndroidLocalProperties(projectRoot, env = process.env) {
  const androidDir = path.join(projectRoot, "android");
  if (!fs.existsSync(androidDir)) {
    throw new Error(`Android project not found at ${androidDir}. Run expo prebuild first.`);
  }

  const sdkDir = resolveAndroidSdkDir(projectRoot, env);
  const localPropertiesPath = path.join(androidDir, "local.properties");
  fs.writeFileSync(localPropertiesPath, `sdk.dir=${escapeLocalPropertiesPath(sdkDir)}\n`);
  return localPropertiesPath;
}

function main() {
  const projectRoot = path.join(__dirname, "..");
  const signing = ensureReleaseSigning(projectRoot);
  console.log(`Android release signing env: ${signing.envPath}`);
  console.log(`Android release signing cmd: ${signing.cmdPath}`);

  const androidDir = path.join(projectRoot, "android");
  if (fs.existsSync(androidDir)) {
    console.log(`Android SDK properties: ${writeAndroidLocalProperties(projectRoot)}`);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  ensureReleaseSigning,
  loadEnvFile,
  validateSigningEnv,
  writeAndroidLocalProperties,
};
