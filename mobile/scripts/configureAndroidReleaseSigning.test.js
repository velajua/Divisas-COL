const assert = require("node:assert/strict");
const test = require("node:test");

const { configureAndroidReleaseSigning } = require("./configureAndroidReleaseSigning");

const sampleBuildGradle = `android {
    signingConfigs {
        debug {
            storeFile file('debug.keystore')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
    }
    buildTypes {
        debug {
            signingConfig signingConfigs.debug
        }
        release {
            signingConfig signingConfigs.debug
            minifyEnabled enableProguardInReleaseBuilds
        }
    }
}`;

test("configureAndroidReleaseSigning adds env backed release signing", () => {
  const result = configureAndroidReleaseSigning(sampleBuildGradle);

  assert.match(result, /release \{\r?\n\s+storeFile file\(System.getenv\("DIVISAS_UPLOAD_STORE_FILE"\)\)/);
  assert.match(result, /storePassword System.getenv\("DIVISAS_UPLOAD_STORE_PASSWORD"\)/);
  assert.match(result, /keyAlias System.getenv\("DIVISAS_UPLOAD_KEY_ALIAS"\)/);
  assert.match(result, /keyPassword System.getenv\("DIVISAS_UPLOAD_KEY_PASSWORD"\)/);
  assert.match(result, /debug \{\r?\n\s+signingConfig signingConfigs.debug/);
  assert.match(result, /release \{\r?\n\s+signingConfig signingConfigs.release/);
});

test("configureAndroidReleaseSigning is idempotent", () => {
  const once = configureAndroidReleaseSigning(sampleBuildGradle);
  const twice = configureAndroidReleaseSigning(once);

  assert.equal(twice, once);
  assert.equal((twice.match(/DIVISAS_UPLOAD_STORE_FILE/g) || []).length, 1);
});
