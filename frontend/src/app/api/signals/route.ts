import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export async function GET() {
  try {
    const signals = await query(
      `SELECT
         e.event_type as signal_type,
         COUNT(*) as total_events,
         t.base_weight as weight
       FROM main.cleaned_events e
       LEFT JOIN main_seeds.signal_taxonomy t ON e.event_type = t.signal_type
       GROUP BY e.event_type, t.base_weight
       ORDER BY total_events DESC`
    );

    return NextResponse.json({ success: true, data: signals });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
