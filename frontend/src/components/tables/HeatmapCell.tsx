import type { FormatHint } from "@/types/dashboard";
import { fmt } from "@/lib/formatters";
import { lightHeatmapColor } from "@/lib/heatmap";

interface Props {
  value: number | null;
  norm: number | null;
  format: FormatHint;
}

export function HeatmapCell({ value, norm, format }: Props) {
  const bg = lightHeatmapColor(norm);
  return (
    <td
      className="whitespace-nowrap px-2 py-1.5 text-right text-sm tabular-nums"
      style={{ backgroundColor: bg }}
    >
      {fmt(value, format)}
    </td>
  );
}
