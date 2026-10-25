"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface SignalData {
  signal_type: string;
  total_events: number;
  weight: number | null;
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<SignalData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/signals")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setSignals(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
      </div>
    );
  }

  const chartData = signals.slice(0, 12).map((s) => ({
    name: s.signal_type.replace(/_/g, " "),
    events: s.total_events,
    weight: s.weight ?? 0,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Signals</h1>
        <p className="text-sm text-zinc-500">
          Signal types, weights, and event volume
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Event Volume by Signal Type</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={chartData} margin={{ bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: "var(--popover, #fff)",
                  border: "1px solid var(--border, #e4e4e7)",
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="events" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Signal Taxonomy</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Signal Type</TableHead>
                <TableHead className="text-right">Events</TableHead>
                <TableHead className="text-right">Weight</TableHead>
                <TableHead>Distribution</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {signals.map((s) => {
                const maxEvents = Math.max(...signals.map((x) => x.total_events));
                const pct = (s.total_events / maxEvents) * 100;
                return (
                  <TableRow key={s.signal_type}>
                    <TableCell className="font-medium">
                      {s.signal_type.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell className="text-right">
                      {s.total_events.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {s.weight ?? "—"}
                    </TableCell>
                    <TableCell>
                      <div className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                        <div
                          className="h-full rounded-full bg-indigo-400"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
