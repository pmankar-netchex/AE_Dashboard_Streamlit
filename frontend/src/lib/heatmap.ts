/**
 * Heatmap utilities.
 *
 * normalizeColumn: maps a column of numbers to 0..1, returning null for null
 * values and a uniform null for columns that have a single distinct value.
 *
 * lightHeatmapColor: very pale red→green tint for in-cell backgrounds.
 *   Pink (low) → green (high). Reversed for LOWER_IS_BETTER columns.
 *
 * rdylgnFor: full-saturation Red→Yellow→Green ramp for the standalone
 * Performance Heatmap grid.
 *
 * textOnColor: returns "light" or "dark" given an rgb() string, using the
 * WCAG relative luminance formula. Use to pick legible text color.
 */

export function normalizeColumn(
  values: (number | null | undefined)[],
  reverse = false,
): (number | null)[] {
  const numeric = values.map((v) =>
    v != null && Number.isFinite(v) ? (v as number) : null,
  );
  const finite = numeric.filter((v): v is number => v !== null);
  if (finite.length === 0) return numeric.map(() => null);
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) return numeric.map(() => null);
  return numeric.map((v) => {
    if (v === null) return null;
    const n = (v - min) / (max - min);
    return reverse ? 1 - n : n;
  });
}

/**
 * Pale tint for in-cell backgrounds. Tuned to stay legible behind dark text:
 *   norm=0  → very light pink  (255, 245, 245)
 *   norm=1  → very light green (240, 252, 240)
 * Half the saturation of the original Streamlit heatmap.
 */
export function lightHeatmapColor(norm: number | null): string {
  if (norm === null) return "transparent";
  const clamped = Math.min(1, Math.max(0, norm));
  const r = Math.round(255 - clamped * 15);
  const g = Math.round(245 + clamped * 7);
  const b = Math.round(245 - clamped * 5);
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Saturated edge marker for in-cell indicators (used as a 3px left border).
 * Same scale as lightHeatmapColor — full saturation so the bar pops.
 */
export function edgeMarkerColor(norm: number | null): string {
  if (norm === null) return "transparent";
  const t = Math.min(1, Math.max(0, norm));
  // Lerp from a muted red (220, 90, 90) → muted green (90, 170, 100)
  const r = Math.round(220 + (90 - 220) * t);
  const g = Math.round(90 + (170 - 90) * t);
  const b = Math.round(90 + (100 - 90) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

/** Red→Yellow→Green 7-stop interpolation, returns rgb(r, g, b) string. */
const RDYLGN_STOPS: [number, [number, number, number]][] = [
  [0.0, [165, 0, 38]],
  [0.17, [215, 48, 39]],
  [0.33, [244, 109, 67]],
  [0.5, [254, 224, 139]],
  [0.67, [217, 239, 139]],
  [0.83, [102, 189, 99]],
  [1.0, [26, 152, 80]],
];

export function rdylgnFor(norm: number | null): string {
  if (norm === null) return "transparent";
  const t = Math.min(1, Math.max(0, norm));
  for (let i = 0; i < RDYLGN_STOPS.length - 1; i++) {
    const [a, ca] = RDYLGN_STOPS[i];
    const [b, cb] = RDYLGN_STOPS[i + 1];
    if (t >= a && t <= b) {
      const f = (t - a) / (b - a);
      const r = Math.round(ca[0] + (cb[0] - ca[0]) * f);
      const g = Math.round(ca[1] + (cb[1] - ca[1]) * f);
      const bl = Math.round(ca[2] + (cb[2] - ca[2]) * f);
      return `rgb(${r}, ${g}, ${bl})`;
    }
  }
  return "transparent";
}

/**
 * Pick a legible text color for the given rgb() background. Uses WCAG
 * relative luminance — light text below ~0.45, dark text above.
 */
export function textOnColor(rgb: string): string {
  const m = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return "rgba(0,0,0,0.85)";
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  const luminance =
    0.2126 * lin(parseInt(m[1])) +
    0.7152 * lin(parseInt(m[2])) +
    0.0722 * lin(parseInt(m[3]));
  return luminance > 0.5 ? "rgba(0,0,0,0.85)" : "rgba(255,255,255,0.95)";
}
