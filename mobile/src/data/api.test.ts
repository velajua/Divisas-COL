import assert from "node:assert/strict";
import test from "node:test";

import { fetchResultJson, RESULT_JSON_URL } from "./api";

test("RESULT_JSON_URL uses the canonical host without a redirect", () => {
  assert.equal(RESULT_JSON_URL, "https://divisascol.com/result.json");
});

test("fetchResultJson sends refresh intent without browser-only cache options", async () => {
  let receivedUrl = "";
  let receivedInit: RequestInit | undefined = undefined;

  const data = await fetchResultJson(RESULT_JSON_URL, async (url, init) => {
    receivedUrl = String(url);
    receivedInit = init;
    return {
      ok: true,
      json: async () => ({ ok: true }),
    } as Response;
  });

  assert.equal(receivedUrl, RESULT_JSON_URL);
  assert.deepEqual(receivedInit, {
    headers: {
      "X-Divisas-Refresh-Intent": "user-visible",
    },
  });
  assert.deepEqual(data, { ok: true });
});
