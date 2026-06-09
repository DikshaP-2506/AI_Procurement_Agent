export type RiskLevel = 'low' | 'medium' | 'high';

export interface RiskAlert {
  alert_type: string;
  severity: RiskLevel;
  message: string;
  source: string;
}

export interface HistoricalPerformance {
  vendor_id: string;
  historical_score: number;
  on_time_delivery_rate: number;
  sla_compliance: number;
  past_projects: number;
}

export interface RiskAssessment {
  vendor_id: string;
  vendor_name?: string | null;
  historical_score: number;
  on_time_delivery_rate: number;
  sla_compliance: number;
  past_projects: number;
  risk_score: number;
  risk_level: RiskLevel;
  alerts: RiskAlert[];
  delay_probability: number;
  delay_risk: RiskLevel;
  prediction_reason: string;
  final_risk_score: number;
  final_risk_level: RiskLevel;
  created_at?: string;
}

export interface RiskTrendPoint {
  created_at: string;
  historical_score: number;
  risk_score: number;
  delay_probability: number;
  final_risk_score: number;
  final_risk_level: RiskLevel;
}

export interface RiskDashboardResponse {
  total_vendors_analyzed: number;
  high_risk_vendors: number;
  medium_risk_vendors: number;
  low_risk_vendors: number;
  average_final_risk_score: number;
  assessments: RiskAssessment[];
  trend: RiskTrendPoint[];
}
