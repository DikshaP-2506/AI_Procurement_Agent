import api from './vendorApi';

export interface Weights {
  cost: number;
  risk: number;
  support: number;
  delivery: number;
  warranty?: number;
  esg?: number;
}

export interface ScoreComponent {
  raw: string | number;
  score: number;
  weighted: number;
}

export interface ScoreBreakdown {
  cost: ScoreComponent;
  risk: ScoreComponent;
  support: ScoreComponent;
  delivery: ScoreComponent;
  warranty?: ScoreComponent;
  esg?: ScoreComponent;
}

export interface VendorRecommendation {
  vendor_id: string;
  vendor_name: string;
  final_score: number;
  rank: number;
  breakdown: ScoreBreakdown;
  explanation: string;
  qualitative_adjustment: number;
  missing_information?: string[];
  confidence_score?: number;
}

export interface RecommendationResponse {
  recommendations: VendorRecommendation[];
  comparison_summary: string;
  warning?: string;
  
  // Agentic AI Recommendation Fields
  recommended_vendor?: string;
  why_selected?: string;
  why_others_not_selected?: string;
  dynamic_priorities?: string;
  criterion_importance?: string;
  confidence_score?: number;
  missing_information?: string[];
  risks?: string;
  alternative_recommendations?: string;
  agent_reasoning?: string;
  agent_plan?: string;
}

export interface ApplyRecommendationResponse {
  status: string;
  message: string;
  procurement_id: string;
  selected_vendor_id: string;
  audit_log_id: string;
}

export async function getRecommendations(
  procurementId: string,
  weights: Weights,
  qualitativeAdjustments?: Record<string, number>,
  skipAi?: boolean
): Promise<RecommendationResponse> {
  const response = await api.post('/recommendation/', {
    procurement_id: procurementId,
    weights,
    qualitative_adjustments: qualitativeAdjustments || null,
    skip_ai: skipAi ?? false,
  });
  return response.data as RecommendationResponse;
}

export async function applyRecommendation(
  procurementId: string,
  selectedVendorId: string,
  weights: Weights,
  reasoning: string
): Promise<ApplyRecommendationResponse> {
  const response = await api.post('/recommendation/apply', {
    procurement_id: procurementId,
    selected_vendor_id: selectedVendorId,
    weights,
    reasoning,
  });
  return response.data as ApplyRecommendationResponse;
}
