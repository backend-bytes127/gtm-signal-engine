export interface AccountScore {
  account_id: string;
  company_name: string;
  domain: string;
  industry: string;
  employee_count: number;
  timing_score: number;
  fit_score: number;
  tier: "hot" | "warm" | "watch" | "cold";
}

export interface Alert {
  account_id: string;
  company_name: string;
  domain: string;
  tier: "hot" | "warm" | "watch" | "cold";
  timing_score: number;
  fit_score: number;
  explanation: string;
  score_rank: number;
}

export interface TierCount {
  tier: string;
  count: number;
}

export interface DashboardData {
  total_accounts: number;
  scored_accounts: number;
  total_alerts: number;
  tier_distribution: TierCount[];
  top_alerts: Alert[];
  avg_timing_score: number;
  planted_buyer_recall: number;
}

export interface SignalEffectiveness {
  signal_type: string;
  total_events: number;
  accepted: number;
  dismissed: number;
  converted: number;
  acceptance_rate: number;
  weight: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
