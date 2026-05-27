export type MessageKey = "loadingRates" | "updated" | "offline" | "loadFailed";

export type HeaderSubtitleCopy = {
  loadingSubtitle: string;
  onlineSubtitle: string;
  offlineSubtitle: string;
  unavailableSubtitle: string;
};

export function getHeaderSubtitle(messageKey: MessageKey, copy: HeaderSubtitleCopy): string {
  if (messageKey === "offline") return copy.offlineSubtitle;
  if (messageKey === "loadFailed") return copy.unavailableSubtitle;
  if (messageKey === "loadingRates") return copy.loadingSubtitle;
  return copy.onlineSubtitle;
}
