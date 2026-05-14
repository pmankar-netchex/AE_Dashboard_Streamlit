/**
 * Minimal CSV exporter. Output is RFC-4180-ish (CRLF line endings, " quoted
 * cells when needed) which means Excel and Google Sheets both open it
 * natively — no xlsx library required.
 */

function escapeCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  let s: string;
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "";
    s = String(v);
  } else if (typeof v === "boolean") {
    s = v ? "true" : "false";
  } else {
    s = String(v);
  }
  if (/[",\r\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

export function toCsv(rows: Array<Record<string, unknown>>, headers: string[]): string {
  const lines: string[] = [];
  lines.push(headers.map(escapeCell).join(","));
  for (const row of rows) {
    lines.push(headers.map((h) => escapeCell(row[h])).join(","));
  }
  return lines.join("\r\n");
}

export function downloadText(filename: string, mime: string, body: string): void {
  // Prepend a UTF-8 BOM so Excel honors non-ASCII chars.
  const blob = new Blob(["﻿", body], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadCsv(
  filename: string,
  rows: Array<Record<string, unknown>>,
  headers: string[],
): void {
  downloadText(filename, "text/csv", toCsv(rows, headers));
}
