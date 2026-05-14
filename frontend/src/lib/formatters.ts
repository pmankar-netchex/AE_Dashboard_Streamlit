import type { FormatHint } from "@/types/dashboard";

const currencyFmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const numberFmt = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

export function fmtCurrency(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return currencyFmt.format(v);
}

export function fmtPercent(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function fmtNumber(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return numberFmt.format(Math.round(v));
}

export function fmt(value: number | null | undefined, hint: FormatHint): string {
  switch (hint) {
    case "currency":
      return fmtCurrency(value);
    case "percent":
      return fmtPercent(value);
    case "number":
    default:
      return fmtNumber(value);
  }
}
