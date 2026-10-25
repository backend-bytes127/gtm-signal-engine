import { NextResponse } from "next/server";
import { query } from "@/lib/db";
import type { AccountScore } from "@/lib/types";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const tier = searchParams.get("tier");
    const sort = searchParams.get("sort") ?? "timing_score";
    const order = searchParams.get("order") === "asc" ? "ASC" : "DESC";
    const search = searchParams.get("q");

    const allowedSorts = ["timing_score", "fit_score", "company_name", "employee_count"];
    const sortCol = allowedSorts.includes(sort) ? sort : "timing_score";

    let where = "WHERE 1=1";
    if (tier) where += ` AND s.tier = '${tier.replace(/'/g, "")}'`;
    if (search) where += ` AND LOWER(a.company_name) LIKE '%${search.toLowerCase().replace(/'/g, "")}%'`;

    const accounts = await query<AccountScore>(
      `SELECT s.account_id, a.company_name, a.domain, a.industry,
              a.employee_count, s.timing_score, s.fit_score, s.tier
       FROM main.account_scores s
       JOIN bronze.accounts a ON s.account_id = a.account_id
       ${where}
       ORDER BY ${sortCol} ${order}
       LIMIT 100`
    );

    return NextResponse.json({ success: true, data: accounts });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
