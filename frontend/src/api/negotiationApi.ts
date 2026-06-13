import api from './vendorApi';
import type {
  EmailRequest,
  NegotiationRequest,
  NegotiationRetrievalResponse,
  NegotiationStrategyResponse,
  NegotiationEmailResponse,
} from '../types/negotiation';

export async function retrieveNegotiations(payload: NegotiationRequest): Promise<NegotiationRetrievalResponse> {
  const response = await api.post('/negotiation/negotiation-retrieval', payload);
  return response.data as NegotiationRetrievalResponse;
}

export async function getStrategyRecommendation(payload: NegotiationRequest): Promise<NegotiationStrategyResponse> {
  const response = await api.post('/negotiation/strategy-recommendation', payload);
  return response.data as NegotiationStrategyResponse;
}

export async function generateNegotiationEmail(payload: EmailRequest): Promise<NegotiationEmailResponse> {
  const response = await api.post('/negotiation/email-generation', payload);
  return response.data as NegotiationEmailResponse;
}
