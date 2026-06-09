import api from './vendorApi';
import type { HistoricalPerformance, RiskAssessment, RiskDashboardResponse, RiskTrendPoint } from '../types/risk';

export async function analyzeVendorRisk(vendorId: string): Promise<RiskAssessment> {
  const response = await api.post('/risk/analyze', { vendor_id: vendorId });
  return response.data as RiskAssessment;
}

export async function getVendorRisk(vendorId: string): Promise<RiskAssessment> {
  const response = await api.get(`/risk/vendor/${vendorId}`);
  return response.data as RiskAssessment;
}

export async function getVendorRiskHistory(vendorId: string): Promise<HistoricalPerformance & { history: RiskTrendPoint[] }> {
  const response = await api.get(`/risk/history/${vendorId}`);
  return response.data as HistoricalPerformance & { history: RiskTrendPoint[] };
}

export async function getRiskDashboard(): Promise<RiskDashboardResponse> {
  const response = await api.get('/risk/dashboard');
  return response.data as RiskDashboardResponse;
}
