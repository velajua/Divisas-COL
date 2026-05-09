import assert from "node:assert/strict";
import test from "node:test";

import { inferNearestCity } from "./cityInference";

test("inferNearestCity returns the nearest supported city", () => {
  assert.equal(
    inferNearestCity(
      { latitude: 6.2442, longitude: -75.5812 },
      ["Bogota", "Medellin", "Cali"],
    ),
    "Medellin",
  );
});

test("inferNearestCity falls back to Bogota when no supported city matches", () => {
  assert.equal(
    inferNearestCity(
      { latitude: 10.391, longitude: -75.4794 },
      ["UnknownCity", "Bogota"],
    ),
    "Bogota",
  );
});
