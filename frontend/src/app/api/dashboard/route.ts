import { NextResponse } from "next/server";
import { query } from "@/lib/db";
import type { DashboardData, TierCount, Alert } from "@/lib/types";

export async function GET() {
  try {
    const [totals] = await query<{ total: number; scored: number }>(
      `SELECT
         (SELECT COUNT(*) FROM bronze.accounts) as total,
         (SELECT COUNT(*) FROM main.account_scores) as scored`
    );

    const [alertCount] = await query<{ n: number }>(
      "SELECT COUNT(*) as n FROM main.alerts"
    );

    const tiers = await query<TierCount>(
      `SELECT tier, COUNT(*) as count
       FROM main.account_scores
       GROUP BY tier ORDER BY count DESC`
    );

    const topAlerts = await query<Alert>(
      `SELECT account_id, company_name, domain, tier,
              timing_score, fit_score, explanation, score_rank
       FROM main.alerts
       ORDER BY score_rank LIMIT 5`
    );

    const [avgScore] = await query<{ avg: number }>(
      "SELECT AVG(timing_score) as avg FROM main.account_scores"
    );

    let plantedRecall = 0;
    try {
      const [recall] = await query<{ rate: number }>(
        `SELECT AVG(CASE WHEN tier = 'hot' THEN 1.0 ELSE 0.0 END) as rate
         FROM main.account_scores
         WHERE account_id IN (
           SELECT DISTINCT ce.account_id
           FROM main.cleaned_events ce
           JOIN bronze.raw_events re ON ce.event_id = re.event_id
           WHERE json_extract_string(re.event_properties, '$._planted') = 'true'
         )`
      );
      plantedRecall = recall?.rate ?? 0;
    } catch {
      // planted buyer tracking not available
    }

    const data: DashboardData = {
      total_accounts: totals?.total ?? 0,
      scored_accounts: totals?.scored ?? 0,
      total_alerts: alertCount?.n ?? 0,
      tier_distribution: tiers,
      top_alerts: topAlerts,
      avg_timing_score: Math.round(avgScore?.avg ?? 0),
      planted_buyer_recall: Math.round(plantedRecall * 100),
    };

    return NextResponse.json({ success: true, data });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
