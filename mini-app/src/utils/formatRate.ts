import type { WheelEvent } from "react";

/** Format API decimal string (e.g. "500.00") without float rounding. */
export function formatHourlyRate(rate: string): string {
  const trimmed = rate.trim();
  if (!trimmed) {
    return rate;
  }

  const normalized = trimmed.replace(",", ".");
  const match = /^(-?\d+)(?:\.(\d+))?$/.exec(normalized);
  if (!match) {
    return rate;
  }

  const whole = match[1];
  const fraction = (match[2] ?? "").replace(/0+$/, "");
  const amount = fraction ? `${whole}.${fraction}` : whole;
  const num = Number(amount);
  if (Number.isNaN(num)) {
    return rate;
  }

  return `${num.toLocaleString("ru-RU", {
    minimumFractionDigits: fraction ? Math.min(fraction.length, 2) : 0,
    maximumFractionDigits: 2,
  })} ₽/час`;
}

/** Prevent accidental value changes when scrolling over number inputs. */
export function preventNumberInputWheel(event: WheelEvent<HTMLInputElement>): void {
  event.currentTarget.blur();
}
