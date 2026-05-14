import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AERow } from "@/types/dashboard";
import { fmtCurrency } from "@/lib/formatters";

interface Props {
  rows: AERow[];
}

export function BookingsBarChart({ rows }: Props) {
  const data = rows.map((r) => ({
    name: r.ae_name,
    bookings_ytd: r.values["S1-COL-D"] ?? 0,
  }));
  return (
    <div className="rounded-lg border border-border p-4">
      <h3 className="mb-3 text-sm font-medium">Bookings YTD by AE</h3>
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11 }}
              angle={-30}
              textAnchor="end"
              height={70}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => fmtCurrency(Number(v))}
              width={80}
            />
            <Tooltip
              formatter={(v: number) => fmtCurrency(v)}
              cursor={{ fill: "rgba(0,0,0,0.04)" }}
            />
            <Bar dataKey="bookings_ytd" fill="hsl(222 47% 33%)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
