import api from './vendorApi';

export interface Weights {
  cost: number;
  risk: number;
  support: number;
  delivery: number;
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
}

export interface VendorRecommendation {
  vendor_id: string;
  vendor_name: string;
  final_score: number;
  rank: number;
  breakdown: ScoreBreakdown;
  explanation: string;
  qualitative_adjustment: number;
}

export interface RecommendationResponse {
  recommendations: VendorRecommendation[];
  comparison_summary: string;
  warning?: string;
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
  qualitativeAdjustments?: Record<string, number>
): Promise<RecommendationResponse> {
  const response = await api.post('/recommendation/', {
    procurement_id: procurementId,
    weights,
    qualitative_adjustments: qualitativeAdjustments || null,
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
