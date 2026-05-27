import type { CountryOption } from "./resultParser";

export type LanguageCode = "es" | "en";

const COUNTRY_ALIASES: Record<string, string> = {
  CO: "colombia",
  Colombia: "colombia",
  PE: "peru",
  Peru: "peru",
};

export function normalizeLanguage(value: string | null | undefined): LanguageCode {
  return String(value || "").toLowerCase().startsWith("en") ? "en" : "es";
}

export function normalizeCountryId(value: string | null | undefined): string {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";

  return COUNTRY_ALIASES[trimmed] || trimmed.toLowerCase().replace(/\s+/g, "-");
}

export function pickDefaultCountry(countries: CountryOption[], detectedCountry: string | null | undefined): string {
  if (!countries.length) return "colombia";

  const detected = normalizeCountryId(detectedCountry);
  if (detected && countries.some((country) => country.id === detected)) {
    return detected;
  }

  if (countries.some((country) => country.id === "colombia")) {
    return "colombia";
  }

  return countries[0].id;
}

export function buildNewsletterUrl(baseUrl: string, language: LanguageCode, country: string): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedCountry = normalizeCountryId(country) || "colombia";
  return `${normalizedBase}/${language}/${normalizedCountry}/newsletter/`;
}

export function buildCountrySiteUrl(baseUrl: string, language: LanguageCode, country: string): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedCountry = normalizeCountryId(country) || "colombia";
  return `${normalizedBase}/${language}/${normalizedCountry}/`;
}

export function buildPrivacyPolicyUrl(baseUrl: string, language: LanguageCode): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  return `${normalizedBase}/${language}/privacy.html`;
}
