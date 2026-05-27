const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  ensureReleaseSigning,
  loadEnvFile,
  writeAndroidLocalProperties,
} = require("./prepareAndroidReleaseBuild");

function tempProject() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "divisas-release-test-"));
}

test("ensureReleaseSigning creates reusable signing env and command files", () => {
  const projectRoot = tempProject();
  const commands = [];

  const signing = ensureReleaseSigning(projectRoot, {
    execFileSync: (command, args) => commands.push([command, args]),
    randomBytes: (size) => Buffer.alloc(size, 0xaa),
  });

  assert.equal(signing.env.DIVISAS_UPLOAD_KEY_ALIAS, "divisas-upload");
  assert.equal(signing.env.DIVISAS_UPLOAD_STORE_PASSWORD.length, 32);
  assert.equal(signing.env.DIVISAS_UPLOAD_KEY_PASSWORD.length, 32);
  assert.equal(commands.length, 1);
  assert.equal(commands[0][0], "keytool");
  assert.ok(fs.existsSync(path.join(projectRoot, "local-signing", "release-signing.env")));
  assert.ok(fs.existsSync(path.join(projectRoot, "local-signing", "release-signing.cmd")));
  assert.match(
    fs.readFileSync(path.join(projectRoot, "local-signing", "release-signing.cmd"), "utf8"),
    /set "DIVISAS_UPLOAD_STORE_FILE=/,
  );
});

test("ensureReleaseSigning reuses existing signing env without rotating passwords", () => {
  const projectRoot = tempProject();
  fs.mkdirSync(path.join(projectRoot, "local-signing"), { recursive: true });
  const keystorePath = path.join(projectRoot, "local-signing", "existing-key.jks");
  fs.writeFileSync(keystorePath, "existing keystore");
  fs.writeFileSync(
    path.join(projectRoot, "local-signing", "release-signing.env"),
    [
      `DIVISAS_UPLOAD_STORE_FILE=${keystorePath}`,
      "DIVISAS_UPLOAD_STORE_PASSWORD=existing-store-password",
      "DIVISAS_UPLOAD_KEY_ALIAS=existing-alias",
      "DIVISAS_UPLOAD_KEY_PASSWORD=existing-key-password",
    ].join("\n"),
  );

  const signing = ensureReleaseSigning(projectRoot, {
    execFileSync: () => {
      throw new Error("keytool should not run");
    },
  });

  assert.equal(signing.env.DIVISAS_UPLOAD_STORE_PASSWORD, "existing-store-password");
  assert.equal(signing.env.DIVISAS_UPLOAD_KEY_ALIAS, "existing-alias");
});

test("ensureReleaseSigning replaces an orphaned default keystore when no env exists", () => {
  const projectRoot = tempProject();
  const signingDir = path.join(projectRoot, "local-signing");
  fs.mkdirSync(signingDir, { recursive: true });
  const orphanedKeystore = path.join(signingDir, "divisas-upload-key.jks");
  fs.writeFileSync(orphanedKeystore, "unknown old key");
  const commands = [];

  ensureReleaseSigning(projectRoot, {
    execFileSync: (command, args) => commands.push([command, args]),
    randomBytes: (size) => Buffer.alloc(size, 0xbb),
  });

  assert.equal(commands.length, 1);
  assert.equal(commands[0][0], "keytool");
  assert.equal(fs.existsSync(orphanedKeystore), false);
});

test("writeAndroidLocalProperties points Gradle at the bundled Android SDK", () => {
  const projectRoot = tempProject();
  fs.mkdirSync(path.join(projectRoot, "android"), { recursive: true });
  fs.mkdirSync(path.join(projectRoot, "android-sdk"), { recursive: true });

  const localPropertiesPath = writeAndroidLocalProperties(projectRoot);

  assert.equal(
    fs.readFileSync(localPropertiesPath, "utf8").trim(),
    `sdk.dir=${path.join(projectRoot, "android-sdk").replace(/\\/g, "\\\\")}`,
  );
});

test("loadEnvFile parses quoted values and ignores comments", () => {
  const projectRoot = tempProject();
  const envPath = path.join(projectRoot, ".env");
  fs.writeFileSync(envPath, "# ignored\nONE=plain\nTWO=\"quoted value\"\n");

  assert.deepEqual(loadEnvFile(envPath), {
    ONE: "plain",
    TWO: "quoted value",
  });
});
