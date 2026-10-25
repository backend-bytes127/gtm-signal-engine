"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TierBadge } from "@/components/tier-badge";
import type { AccountScore } from "@/lib/types";

const TIER_FILTERS = ["all", "hot", "warm", "watch", "cold"] as const;

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<AccountScore[]>([]);
  const [tier, setTier] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("timing_score");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  const [loading, setLoading] = useState(true);

  const fetchAccounts = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ sort: sortBy, order: sortOrder });
    if (tier !== "all") params.set("tier", tier);
    if (search) params.set("q", search);

    fetch(`/api/accounts?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setAccounts(res.data);
      })
      .finally(() => setLoading(false));
  }, [tier, search, sortBy, sortOrder]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  function handleSort(col: string) {
    if (sortBy === col) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(col);
      setSortOrder("desc");
    }
  }

  const sortIndicator = (col: string) =>
    sortBy === col ? (sortOrder === "desc" ? " ↓" : " ↑") : "";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Accounts</h1>
        <p className="text-sm text-zinc-500">
          {accounts.length} accounts scored and ranked
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {TIER_FILTERS.map((t) => (
          <button
            key={t}
            onClick={() => setTier(t)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              tier === t
                ? "bg-indigo-600 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {t === "all" ? "All Tiers" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
        <input
          type="text"
          placeholder="Search company..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-500 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account Scores</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer"
                    onClick={() => handleSort("company_name")}
                  >
                    Company{sortIndicator("company_name")}
                  </TableHead>
                  <TableHead>Industry</TableHead>
                  <TableHead
                    className="cursor-pointer text-right"
                    onClick={() => handleSort("employee_count")}
                  >
                    Employees{sortIndicator("employee_count")}
                  </TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead
                    className="cursor-pointer text-right"
                    onClick={() => handleSort("timing_score")}
                  >
                    Timing{sortIndicator("timing_score")}
                  </TableHead>
                  <TableHead
                    className="cursor-pointer text-right"
                    onClick={() => handleSort("fit_score")}
                  >
                    Fit{sortIndicator("fit_score")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((a) => (
                  <TableRow key={a.account_id}>
                    <TableCell>
                      <div>
                        <span className="font-medium">{a.company_name}</span>
                        <span className="ml-2 text-xs text-zinc-400">
                          {a.domain}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-500">
                      {a.industry}
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {a.employee_count?.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <TierBadge tier={a.tier} />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="h-2 w-16 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                          <div
                            className="h-full rounded-full bg-indigo-500"
                            style={{ width: `${a.timing_score}%` }}
                          />
                        </div>
                        <span className="w-8 text-right text-sm font-medium">
                          {Math.round(a.timing_score)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium">
                      {a.fit_score}/4
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
