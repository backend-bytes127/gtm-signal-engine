"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TierBadge } from "@/components/tier-badge";
import { Bell, CheckCircle, XCircle, Zap } from "lucide-react";
import type { Alert } from "@/lib/types";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/alerts")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setAlerts(res.data);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Alerts</h1>
        <p className="text-sm text-zinc-500">
          {alerts.length} accounts surfaced by the scoring engine
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Bell className="h-5 w-5 text-red-500" />
            <div>
              <p className="text-2xl font-bold">
                {alerts.filter((a) => a.tier === "hot").length}
              </p>
              <p className="text-xs text-zinc-500">Hot Alerts</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Zap className="h-5 w-5 text-orange-500" />
            <div>
              <p className="text-2xl font-bold">
                {alerts.filter((a) => a.tier === "warm").length}
              </p>
              <p className="text-xs text-zinc-500">Warm Alerts</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Bell className="h-5 w-5 text-zinc-400" />
            <div>
              <p className="text-2xl font-bold">{alerts.length}</p>
              <p className="text-xs text-zinc-500">Total (budget: 5/AE)</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        {alerts.map((alert, idx) => (
          <Card key={alert.account_id}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-zinc-400">
                      #{idx + 1}
                    </span>
                    <h3 className="text-lg font-semibold">
                      {alert.company_name}
                    </h3>
                    <TierBadge tier={alert.tier} />
                    <span className="text-sm text-zinc-400">{alert.domain}</span>
                  </div>

                  <div className="mt-3 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-900">
                    <p className="text-sm font-medium text-zinc-500">Why Now</p>
                    <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                      {alert.explanation}
                    </p>
                  </div>

                  <div className="mt-4 flex items-center gap-6">
                    <div>
                      <p className="text-xs text-zinc-400">Timing Score</p>
                      <div className="mt-1 flex items-center gap-2">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
                          <div
                            className="h-full rounded-full bg-indigo-500"
                            style={{ width: `${alert.timing_score}%` }}
                          />
                        </div>
                        <span className="text-sm font-bold">
                          {Math.round(alert.timing_score)}
                        </span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-zinc-400">Fit Score</p>
                      <p className="mt-1 text-sm font-bold">
                        {alert.fit_score}/4
                      </p>
                    </div>
                  </div>
                </div>

                <div className="ml-6 flex flex-col gap-2">
                  <button className="flex items-center gap-1.5 rounded-lg bg-green-50 px-3 py-2 text-sm font-medium text-green-700 transition-colors hover:bg-green-100 dark:bg-green-950 dark:text-green-300">
                    <CheckCircle className="h-4 w-4" />
                    Accept
                  </button>
                  <button className="flex items-center gap-1.5 rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 dark:bg-red-950 dark:text-red-300">
                    <XCircle className="h-4 w-4" />
                    Dismiss
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {alerts.length === 0 && (
          <div className="flex h-40 items-center justify-center text-zinc-400">
            No alerts. Run the pipeline to generate scores.
          </div>
        )}
      </div>
    </div>
  );
}
