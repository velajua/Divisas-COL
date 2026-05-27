import assert from "node:assert/strict";
import test from "node:test";

import { buildCountrySiteUrl } from "./settings";

test("buildCountrySiteUrl returns the localized country home page", () => {
  assert.equal(
    buildCountrySiteUrl("https://divisascol.com/", "en", "Colombia"),
    "https://divisascol.com/en/colombia/",
  );
});
