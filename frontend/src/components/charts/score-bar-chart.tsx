"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { Alert } from "@/lib/types";

export function ScoreBarChart({ data }: { data: Alert[] }) {
  const chartData = data.map((a) => ({
    name: a.company_name.length > 15 ? a.company_name.slice(0, 15) + "..." : a.company_name,
    timing: Math.round(a.timing_score),
    fit: a.fit_score,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={120} />
        <Tooltip
          contentStyle={{
            background: "var(--popover, #fff)",
            border: "1px solid var(--border, #e4e4e7)",
            borderRadius: 8,
          }}
        />
        <Bar dataKey="timing" fill="#6366f1" name="Timing Score" radius={[0, 4, 4, 0]} />
        <Bar dataKey="fit" fill="#22c55e" name="Fit Score" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
