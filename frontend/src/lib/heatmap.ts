/**
 * Port of dashboard_ui._light_heatmap (legacy Streamlit) for per-column tinting.
 *
 *   norm = (v - min) / (max - min)
 *   if reverse: norm = 1 - norm
 *   color = rgb(255 - n*35, 230 + n*25, 230 - n*10)
 *
 * Pink (low) → green (high). Reversed for LOWER_IS_BETTER columns.
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

export function lightHeatmapColor(norm: number | null): string {
  if (norm === null) return "transparent";
  const clamped = Math.min(1, Math.max(0, norm));
  const r = Math.round(255 - clamped * 35);
  const g = Math.round(230 + clamped * 25);
  const b = Math.round(230 - clamped * 10);
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Red→Yellow→Green ramp for the Performance Heatmap.
 * 7-stop interpolation across the classic RdYlGn palette.
 */
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
