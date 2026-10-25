import { NextResponse } from "next/server";
import { query } from "@/lib/db";
import type { Alert } from "@/lib/types";

export async function GET() {
  try {
    const alerts = await query<Alert>(
      `SELECT account_id, company_name, domain, tier,
              timing_score, fit_score, explanation, score_rank
       FROM main.alerts
       ORDER BY score_rank`
    );

    return NextResponse.json({ success: true, data: alerts });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
