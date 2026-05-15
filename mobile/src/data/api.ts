import { assertResultPayload, type ResultPayload } from "./snapshotCache";

export const RESULT_JSON_URL = "https://divisascol.com/result.json";

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

export async function fetchResultJson(
  url = RESULT_JSON_URL,
  fetchImpl: FetchLike = fetch,
): Promise<ResultPayload> {
  const response = await fetchImpl(url, {
    headers: {
      "X-Divisas-Refresh-Intent": "user-visible",
    },
  });

  if (!response.ok) {
    throw new Error(`Could not fetch result.json: ${response.status}`);
  }

  const data = await response.json();
  assertResultPayload(data);
  return data;
}
