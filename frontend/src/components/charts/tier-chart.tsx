"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import type { TierCount } from "@/lib/types";

const TIER_COLORS: Record<string, string> = {
  hot: "#ef4444",
  warm: "#f97316",
  watch: "#3b82f6",
  cold: "#a1a1aa",
};

export function TierChart({ data }: { data: TierCount[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="tier"
          cx="50%"
          cy="50%"
          outerRadius={100}
          innerRadius={60}
          strokeWidth={2}
          stroke="#fafafa"
        >
          {data.map((entry) => (
            <Cell
              key={entry.tier}
              fill={TIER_COLORS[entry.tier] ?? "#d4d4d8"}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "var(--popover, #fff)",
            border: "1px solid var(--border, #e4e4e7)",
            borderRadius: 8,
          }}
          formatter={(value: number, name: string) => [value, name.toUpperCase()]}
        />
        <Legend
          formatter={(value: string) => (
            <span className="text-xs uppercase">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
