"use client";

import { useEffect, useState } from "react";
import { Building2, Bell, Target, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/kpi-card";
import { TierBadge } from "@/components/tier-badge";
import { TierChart } from "@/components/charts/tier-chart";
import { ScoreBarChart } from "@/components/charts/score-bar-chart";
import type { DashboardData } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setData(res.data);
        else setError(res.error);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-medium text-red-600">Failed to load dashboard</p>
          <p className="mt-1 text-sm text-zinc-500">{error}</p>
          <p className="mt-4 text-sm text-zinc-400">
            Run the pipeline first: Dagster UI → Materialize all
          </p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Account-level intent scoring overview
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Accounts"
          value={data.total_accounts.toLocaleString()}
          subtitle={`${data.scored_accounts} scored`}
          icon={Building2}
        />
        <KpiCard
          title="Active Alerts"
          value={data.total_alerts}
          subtitle="Attention budget: 5/AE"
          icon={Bell}
          accent="text-red-600"
        />
        <KpiCard
          title="Avg Timing Score"
          value={data.avg_timing_score}
          subtitle="Percentile (0-100)"
          icon={TrendingUp}
          accent="text-green-600"
        />
        <KpiCard
          title="Planted Buyer Recall"
          value={`${data.planted_buyer_recall}%`}
          subtitle="Hot tier detection"
          icon={Target}
          accent="text-amber-600"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tier Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <TierChart data={data.tier_distribution} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Alerts — Score Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <ScoreBarChart data={data.top_alerts} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {data.top_alerts.map((alert) => (
              <div
                key={alert.account_id}
                className="flex items-start gap-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{alert.company_name}</span>
                    <TierBadge tier={alert.tier} />
                    <span className="text-xs text-zinc-400">{alert.domain}</span>
                  </div>
                  <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                    {alert.explanation}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-indigo-600">
                    {Math.round(alert.timing_score)}
                  </p>
                  <p className="text-xs text-zinc-400">timing</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
