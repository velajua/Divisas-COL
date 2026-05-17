import { useEffect, useState } from "react";
import { Image, Platform, Pressable, StyleSheet, Text, View } from "react-native";

import type { LanguageCode } from "../data/settings";
import type { MobileAdPlacementConfig } from "../data/adConfig";

type GoogleMobileAdsModule = typeof import("react-native-google-mobile-ads");
type LoadedNativeAd = Awaited<ReturnType<GoogleMobileAdsModule["NativeAd"]["createForAdRequest"]>>;

function loadGoogleMobileAds(): GoogleMobileAdsModule | null {
  if (Platform.OS !== "android") return null;
  return require("react-native-google-mobile-ads") as GoogleMobileAdsModule;
}

export function MobileBannerAd({ placement }: { placement: MobileAdPlacementConfig }) {
  if (!placement.enabled || !placement.androidAdUnitId) return null;

  const ads = loadGoogleMobileAds();
  if (!ads) return null;

  const { BannerAd, BannerAdSize } = ads;

  return (
    <View style={styles.bannerShell}>
      <BannerAd
        unitId={placement.androidAdUnitId}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{ requestNonPersonalizedAdsOnly: true }}
      />
    </View>
  );
}

export function MobileNativeAd({
  placement,
  language,
}: {
  placement: MobileAdPlacementConfig;
  language: LanguageCode;
}) {
  const [nativeAd, setNativeAd] = useState<LoadedNativeAd | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const ads = loadGoogleMobileAds();
    if (!placement.enabled || !placement.androidAdUnitId || !ads) {
      setNativeAd(null);
      return undefined;
    }

    let active = true;
    let loadedAd: LoadedNativeAd | null = null;

    ads.NativeAd.createForAdRequest(placement.androidAdUnitId, {
      requestNonPersonalizedAdsOnly: true,
    })
      .then((ad) => {
        loadedAd = ad;
        if (active) {
          setNativeAd(ad);
          setFailed(false);
        } else {
          ad.destroy();
        }
      })
      .catch(() => {
        if (active) {
          setNativeAd(null);
          setFailed(true);
        }
      });

    return () => {
      active = false;
      loadedAd?.destroy();
    };
  }, [placement.androidAdUnitId, placement.enabled]);

  if (!placement.enabled || failed || !nativeAd) return null;

  const ads = loadGoogleMobileAds();
  if (!ads) return null;

  const { NativeAdView, NativeAsset, NativeAssetType, NativeMediaView } = ads;
  const adLabel = language === "en" ? "Ad" : "Anuncio";

  return (
    <NativeAdView nativeAd={nativeAd} style={styles.nativeCard}>
      <View style={styles.nativeHeader}>
        {nativeAd.icon?.url ? <Image source={{ uri: nativeAd.icon.url }} style={styles.nativeIcon} /> : null}
        <View style={styles.nativeHeaderText}>
          <View style={styles.nativeLabelRow}>
            <Text style={styles.nativeBadge}>{adLabel}</Text>
            {nativeAd.advertiser ? (
              <NativeAsset assetType={NativeAssetType.ADVERTISER}>
                <Text style={styles.nativeAdvertiser}>{nativeAd.advertiser}</Text>
              </NativeAsset>
            ) : null}
          </View>
          <NativeAsset assetType={NativeAssetType.HEADLINE}>
            <Text style={styles.nativeHeadline}>{nativeAd.headline}</Text>
          </NativeAsset>
        </View>
      </View>
      <NativeMediaView style={styles.nativeMedia} />
      <NativeAsset assetType={NativeAssetType.BODY}>
        <Text style={styles.nativeBody}>{nativeAd.body}</Text>
      </NativeAsset>
      <NativeAsset assetType={NativeAssetType.CALL_TO_ACTION}>
        <Pressable style={styles.nativeButton}>
          <Text style={styles.nativeButtonText}>{nativeAd.callToAction}</Text>
        </Pressable>
      </NativeAsset>
    </NativeAdView>
  );
}

const styles = StyleSheet.create({
  bannerShell: {
    alignItems: "center",
    backgroundColor: "#17130d",
    borderTopColor: "#352b1d",
    borderTopWidth: 1,
    minHeight: 56,
    paddingVertical: 4,
  },
  nativeCard: {
    backgroundColor: "#fffaf1",
    borderColor: "#d8b06c",
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 18,
    overflow: "hidden",
    padding: 14,
  },
  nativeHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  nativeIcon: {
    borderRadius: 6,
    height: 44,
    width: 44,
  },
  nativeHeaderText: {
    flex: 1,
  },
  nativeLabelRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
    marginBottom: 4,
  },
  nativeBadge: {
    backgroundColor: "#c9a227",
    borderRadius: 4,
    color: "#17130d",
    fontSize: 11,
    fontWeight: "800",
    overflow: "hidden",
    paddingHorizontal: 6,
    paddingVertical: 2,
    textTransform: "uppercase",
  },
  nativeAdvertiser: {
    color: "#6d6254",
    flexShrink: 1,
    fontSize: 12,
    fontWeight: "700",
  },
  nativeHeadline: {
    color: "#17130d",
    fontSize: 17,
    fontWeight: "800",
  },
  nativeMedia: {
    aspectRatio: 1.91,
    backgroundColor: "#efe2ca",
    borderRadius: 8,
    marginTop: 12,
    overflow: "hidden",
    width: "100%",
  },
  nativeBody: {
    color: "#2c261f",
    fontSize: 14,
    lineHeight: 20,
    marginTop: 12,
  },
  nativeButton: {
    alignItems: "center",
    backgroundColor: "#17130d",
    borderRadius: 8,
    marginTop: 12,
    padding: 12,
  },
  nativeButtonText: {
    color: "#f8efe0",
    fontSize: 14,
    fontWeight: "800",
  },
});
