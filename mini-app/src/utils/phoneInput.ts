import type { KeyboardEvent } from "react";
import type { PhoneCountryPrefs } from "../api/client";

export const CUSTOM_COUNTRY_CODE = "__custom__";

export const DEFAULT_COUNTRY_CODES = [
  { value: "+7", label: "+7" },
  { value: "+375", label: "+375" },
  { value: "+380", label: "+380" },
  { value: "+996", label: "+996" },
  { value: "+998", label: "+998" },
] as const;

export type CountryCodeOption = {
  value: string;
  label: string;
};

const PHONE_PREFS_KEY_PREFIX = "phone_country_prefs_";

function prefsStorageKey(telegramUserId: number | null): string {
  return `${PHONE_PREFS_KEY_PREFIX}${telegramUserId}`;
}

export function isValidCountryCode(code: string): boolean {
  const digits = code.replace(/\D/g, "");
  if (!digits || digits[0] === "0" || digits.length > 4) {
    return false;
  }
  const normalized = normalizeCountryCode(code);
  return /^\+\d{1,4}$/.test(normalized);
}

export function buildCountryCodeOptions(customCodes: string[] = []): CountryCodeOption[] {
  const seen = new Set<string>();
  const options: CountryCodeOption[] = [];

  for (const item of DEFAULT_COUNTRY_CODES) {
    if (!seen.has(item.value)) {
      seen.add(item.value);
      options.push({ value: item.value, label: item.label });
    }
  }

  for (const raw of customCodes) {
    const normalized = normalizeCountryCode(raw);
    if (isValidCountryCode(normalized) && !seen.has(normalized)) {
      seen.add(normalized);
      options.push({ value: normalized, label: normalized });
    }
  }

  options.push({ value: CUSTOM_COUNTRY_CODE, label: "Другой код" });
  return options;
}

export function extractNationalDigits(nationalDigits: string, countryCode = "+7"): string {
  let digits = nationalDigits.replace(/\D/g, "");
  const codeDigits = countryCode.replace(/\D/g, "");
  if (codeDigits && digits.startsWith(codeDigits)) {
    digits = digits.slice(codeDigits.length);
  }
  if (countryCode === "+7") {
    if (digits.startsWith("8")) {
      digits = digits.slice(1);
    }
    if (digits.startsWith("7")) {
      digits = digits.slice(1);
    }
  }
  return digits.slice(0, 10);
}

export function formatNationalPhone(nationalDigits: string, countryCode = "+7"): string {
  const digits = extractNationalDigits(nationalDigits, countryCode);
  if (digits.length === 0) {
    return "";
  }
  let formatted = `(${digits.slice(0, 3)}`;
  if (digits.length >= 3) {
    formatted += `) ${digits.slice(3, 6)}`;
  }
  if (digits.length >= 6) {
    formatted += `-${digits.slice(6, 8)}`;
  }
  if (digits.length >= 8) {
    formatted += `-${digits.slice(8, 10)}`;
  }
  return formatted;
}

export function normalizeCountryCode(code: string): string {
  const digits = code.replace(/\D/g, "");
  return digits ? `+${digits.slice(0, 4)}` : "+7";
}

function caretIndexForDigit(formatted: string, digitIndex: number): number {
  if (digitIndex <= 0) {
    return 0;
  }
  let count = 0;
  for (let i = 0; i < formatted.length; i++) {
    if (/\d/.test(formatted[i]!)) {
      count++;
      if (count === digitIndex) {
        return i + 1;
      }
    }
  }
  return formatted.length;
}

export function handlePhoneKeyDown(
  event: KeyboardEvent<HTMLInputElement>,
  nationalDigits: string,
  countryCode: string,
  onNationalDigitsChange: (value: string) => void,
  onCaretRestore?: (index: number) => void,
): void {
  if (event.key !== "Backspace" && event.key !== "Delete") {
    return;
  }

  const input = event.currentTarget;
  const caret = input.selectionStart ?? 0;
  if (caret !== (input.selectionEnd ?? 0)) {
    return;
  }

  const formatted = formatNationalPhone(nationalDigits, countryCode);

  if (event.key === "Backspace") {
    if (caret === 0) {
      return;
    }
    const charBefore = formatted[caret - 1];
    if (/\d/.test(charBefore ?? "")) {
      return;
    }
    event.preventDefault();
    const digitCount = formatted.slice(0, caret).replace(/\D/g, "").length;
    if (digitCount <= 0) {
      return;
    }
    const nextDigits = nationalDigits.slice(0, digitCount - 1) + nationalDigits.slice(digitCount);
    onNationalDigitsChange(nextDigits);
    onCaretRestore?.(caretIndexForDigit(formatNationalPhone(nextDigits, countryCode), digitCount - 1));
    return;
  }

  if (caret >= formatted.length) {
    return;
  }
  const charAt = formatted[caret];
  if (/\d/.test(charAt ?? "")) {
    return;
  }
  event.preventDefault();
  const digitIndex = formatted.slice(0, caret).replace(/\D/g, "").length;
  if (digitIndex >= nationalDigits.length) {
    return;
  }
  const nextDigits = nationalDigits.slice(0, digitIndex) + nationalDigits.slice(digitIndex + 1);
  onNationalDigitsChange(nextDigits);
  onCaretRestore?.(caretIndexForDigit(formatNationalPhone(nextDigits, countryCode), digitIndex));
}

export function buildE164Phone(countryCode: string, nationalDigits: string): string | null {
  const normalizedCode = normalizeCountryCode(countryCode);
  const codeDigits = normalizedCode.replace(/\D/g, "");
  const national = extractNationalDigits(nationalDigits, normalizedCode);
  if (!national) {
    return null;
  }
  if (normalizedCode === "+7") {
    return national.length === 10 ? `+7${national}` : null;
  }
  if (national.length < 4 || national.length > 14) {
    return null;
  }
  const e164 = `+${codeDigits}${national}`;
  return e164.length < 9 || e164.length > 16 ? null : e164;
}

export function loadPhoneCountryPrefs(telegramUserId: number | null): PhoneCountryPrefs | null {
  if (telegramUserId === null || typeof localStorage === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(prefsStorageKey(telegramUserId));
    if (!raw) {
      return null;
    }
    const parsed: unknown = JSON.parse(raw);
    if (
      !parsed ||
      typeof parsed !== "object" ||
      typeof (parsed as PhoneCountryPrefs).preferred !== "string" ||
      !Array.isArray((parsed as PhoneCountryPrefs).customCodes) ||
      !(parsed as PhoneCountryPrefs).customCodes.every((c) => typeof c === "string")
    ) {
      return null;
    }
    return parsed as PhoneCountryPrefs;
  } catch {
    return null;
  }
}

export function savePhoneCountryPrefs(telegramUserId: number | null, prefs: PhoneCountryPrefs): void {
  if (telegramUserId === null || typeof localStorage === "undefined") {
    return;
  }
  localStorage.setItem(prefsStorageKey(telegramUserId), JSON.stringify(prefs));
}

export function defaultPhoneCountryPrefs(): PhoneCountryPrefs {
  return { preferred: "+7", customCodes: [] };
}
