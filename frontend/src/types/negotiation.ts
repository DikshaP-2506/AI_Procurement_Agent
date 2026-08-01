export interface NegotiationRequest {
  procurement_id?: string;
  quote_id?: string;
  vendor_name?: string;
  product_category?: string;
  quote_value?: number;
}

export interface NegotiationHistoryRecord {
  id: string;
  vendor_id: string;
  vendor_name?: string | null;
  product_category?: string | null;
  strategy_used?: string | null;
  outcome?: string | null;
  discount_received?: number | null;
  success_score?: number | null;
}

export interface NegotiationRetrievalResponse {
  similar_negotiations: NegotiationHistoryRecord[];
}

export interface NegotiationStrategy {
  recommended_strategy: string;
  expected_discount_range: string;
  confidence_score: number;
  reasoning: string;
  risks: string[];
}

export interface NegotiationStrategyResponse {
  status: string;
  strategy: NegotiationStrategy;
  historical: NegotiationHistoryRecord[];
}

export interface NegotiationEmail {
  subject: string;
  body: string;
}

export interface NegotiationEmailResponse {
  status: string;
  email: NegotiationEmail;
}

export interface EmailRequest {
  procurement_id?: string;
  quote_id?: string;
  vendor_name?: string;
  recommended_strategy: string;
  expected_discount_range: string;
}

export interface UseStrategyRequest {
  procurement_id?: string;
  quote_id?: string;
  recommended_strategy: string;
  expected_discount_range: string;
  generated_email?: {
    subject: string;
    body: string;
  };
  risk_score?: number;
  vendor_rank?: number;
}
