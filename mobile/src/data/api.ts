import { assertResultPayload, type ResultPayload } from "./snapshotCache";
import { fetchWithTimeout } from "./fetchTimeout";

export const RESULT_JSON_URL = "https://divisascol.com/result.json";
const RESULT_JSON_TIMEOUT_MS = 8000;

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

export async function fetchResultJson(
  url = RESULT_JSON_URL,
  fetchImpl: FetchLike = fetch,
  timeoutMs = RESULT_JSON_TIMEOUT_MS,
): Promise<ResultPayload> {
  const response = await fetchWithTimeout(
    fetchImpl,
    url,
    {
      headers: {
        "X-Divisas-Refresh-Intent": "user-visible",
      },
    },
    timeoutMs,
  );

  if (!response.ok) {
    throw new Error(`Could not fetch result.json: ${response.status}`);
  }

  const data = await response.json();
  assertResultPayload(data);
  return data;
}
