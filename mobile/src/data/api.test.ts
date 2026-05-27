import assert from "node:assert/strict";
import test from "node:test";

import { fetchResultJson, RESULT_JSON_URL } from "./api";
import { getHeaderSubtitle, type HeaderSubtitleCopy } from "./appStatus";

const headerCopy: HeaderSubtitleCopy = {
  loadingSubtitle: "Checking latest exchange rates",
  onlineSubtitle: "Latest exchange rates loaded",
  offlineSubtitle: "Offline rates from saved data",
  unavailableSubtitle: "Connect to load exchange rates",
};

test("RESULT_JSON_URL uses the canonical host without a redirect", () => {
  assert.equal(RESULT_JSON_URL, "https://divisascol.com/result.json");
});

test("fetchResultJson sends refresh intent without browser-only cache options", async () => {
  let receivedUrl = "";
  let receivedInit: RequestInit = {};

  const data = await fetchResultJson(RESULT_JSON_URL, async (url, init) => {
    receivedUrl = String(url);
    receivedInit = init || {};
    return {
      ok: true,
      json: async () => ({ countries: { colombia: { Bogota: {} } } }),
    } as Response;
  });

  assert.equal(receivedUrl, RESULT_JSON_URL);
  assert.equal((receivedInit?.headers as Record<string, string>)["X-Divisas-Refresh-Intent"], "user-visible");
  assert.ok(receivedInit?.signal instanceof AbortSignal);
  assert.deepEqual(data, { countries: { colombia: { Bogota: {} } } });
});

test("fetchResultJson rejects payloads without country rates", async () => {
  await assert.rejects(
    fetchResultJson(RESULT_JSON_URL, async () => ({
      ok: true,
      json: async () => ({ generated_at: "2026-05-14T12:00:00Z" }),
    }) as Response),
    /missing country rates/i,
  );
});

test("fetchResultJson times out slow result requests", async () => {
  const startedAt = Date.now();

  await assert.rejects(
    fetchResultJson(RESULT_JSON_URL, async () => new Promise<Response>(() => {}), 10),
    /timed out/i,
  );
  assert.ok(Date.now() - startedAt < 250);
});

test("getHeaderSubtitle only shows offline copy when saved data is being used after a fetch failure", () => {
  assert.equal(getHeaderSubtitle("updated", headerCopy), "Latest exchange rates loaded");
  assert.equal(getHeaderSubtitle("offline", headerCopy), "Offline rates from saved data");
});

test("getHeaderSubtitle uses non-offline copy while loading or when no saved data is available", () => {
  assert.equal(getHeaderSubtitle("loadingRates", headerCopy), "Checking latest exchange rates");
  assert.equal(getHeaderSubtitle("loadFailed", headerCopy), "Connect to load exchange rates");
});
