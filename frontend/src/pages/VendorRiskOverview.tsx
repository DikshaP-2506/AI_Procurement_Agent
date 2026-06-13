import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import Navbar from '../components/Navbar';
import RiskAlertsPanel from '../components/RiskAlertsPanel';
import RiskTrendVisualization from '../components/RiskTrendVisualization';
import { analyzeVendorRisk, getVendorRisk, getVendorRiskHistory } from '../api/riskApi';
import { getVendors } from '../api/vendorApi';
import type { RiskAssessment, RiskTrendPoint } from '../types/risk';

const PROCUREMENT_ID = '8ea2d01d-2137-4e83-8875-eb6a28d6e0c6';

function levelColor(level: RiskAssessment['final_risk_level']) {
  if (level === 'high') return '#EF4444';
  if (level === 'medium') return '#F59E0B';
  return '#10B981';
}

export default function VendorRiskOverview() {
  const params = useParams<{ vendorId?: string }>();
  const [vendors, setVendors] = useState<any[]>([]);
  const [vendorId, setVendorId] = useState<string>(params.vendorId ?? '');
  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [history, setHistory] = useState<RiskTrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const vs = await getVendors(PROCUREMENT_ID);
        setVendors(vs);
      } catch (e) {
        console.error("Failed to load vendors selector list", e);
      }
    })();
  }, []);

  useEffect(() => {
    if (vendorId) {
      void loadVendorRisk(vendorId);
    }
  }, [vendorId]);

  async function loadVendorRisk(id: string) {
    setLoading(true);
    setError(null);
    try {
      let current: RiskAssessment;
      try {
        current = await getVendorRisk(id);
      } catch {
        current = await analyzeVendorRisk(id);
      }
      const historyResponse = await getVendorRiskHistory(id);
      setAssessment(current);
      setHistory(historyResponse.history || []);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string' && detail.trim()) {
          setError(detail);
        } else if (err.code === 'ERR_NETWORK') {
          setError('Unable to reach the backend at http://127.0.0.1:8000. Make sure the API is running.');
        } else {
          setError(`Unable to load vendor risk data (${err.response?.status ?? 'unknown error'}).`);
        }
      } else {
        setError('Unable to load vendor risk data. Check the vendor id and backend availability.');
      }
      setAssessment(null);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }

  const summaryTone = assessment ? levelColor(assessment.final_risk_level) : '#94A3B8';

  return (
    <div style={{ minHeight: '100vh', background: '#0A0A0F' }}>
      <Navbar />
      <div className="app-container" style={{ maxWidth: 1200 }}>
        
        {/* Page Header */}
        <div style={{ marginBottom: 24 }}>
          <p style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94A3B8', fontSize: 11, fontWeight: 700 }}>
            Risk Intelligence
          </p>
          <h1 style={{ margin: '8px 0 10px', background: 'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Vendor Risk Overview
          </h1>
          <p style={{ margin: 0, color: '#94A3B8', maxWidth: 760 }}>
            Analyze historical performance, external risk signals, and delay probability for a single vendor snapshot.
          </p>
        </div>

        {/* Top Control Panel */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20, marginBottom: 24 }}>
          
          <div className="card-glass">
            <label style={{ display: 'block', fontSize: 13, fontWeight: 700, color: '#E2E8F0', marginBottom: 8 }}>
              Select Vendor to Analyze
            </label>
            <div style={{ display: 'flex', gap: 12 }}>
              <select
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value)}
                style={{
                  flex: 1,
                  background: 'rgba(0, 0, 0, 0.35)',
                  color: '#F8FAFC',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 10,
                  padding: '12px 14px',
                  fontSize: 14,
                  cursor: 'pointer',
                  outline: 'none'
                }}
              >
                <option value="">-- select registered vendor --</option>
                {vendors.map(v => (
                  <option key={v.id} value={v.id}>{v.vendor_name} ({v.country})</option>
                ))}
              </select>
              <button
                onClick={() => vendorId && void loadVendorRisk(vendorId)}
                disabled={loading || !vendorId}
                style={{
                  background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 10,
                  padding: '10px 20px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)',
                  opacity: (loading || !vendorId) ? 0.6 : 1
                }}
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
            {error && (
              <div style={{ 
                marginTop: 12, 
                padding: '8px 10px', 
                background: 'rgba(239, 68, 68, 0.08)', 
                border: '1px solid rgba(239, 68, 68, 0.2)', 
                borderRadius: 8, 
                color: '#FCA5A5', 
                fontSize: 13 
              }}>
                {error}
              </div>
            )}
          </div>

          <div className="card-glass" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ color: '#94A3B8', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Current Risk Rating
              </div>
              <div style={{ fontSize: 14, color: '#E2E8F0', marginTop: 4, fontWeight: 600 }}>
                {assessment ? assessment.final_risk_level.toUpperCase() : 'No vendor selected'}
              </div>
            </div>
            <div style={{ 
              fontSize: 38, 
              fontWeight: 800, 
              color: summaryTone,
              background: 'rgba(0,0,0,0.3)',
              padding: '8px 16px',
              borderRadius: 12,
              border: assessment ? `1px solid ${summaryTone}33` : '1px solid rgba(255,255,255,0.04)'
            }}>
              {assessment ? assessment.final_risk_score : '--'}
            </div>
          </div>
        </div>

        {assessment ? (
          <div style={{ display: 'grid', gap: 24 }}>
            
            {/* Stats Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
              {[
                ['Historical Score', assessment.historical_score],
                ['Market Risk', assessment.risk_score],
                ['Delay Probability', `${Math.round(assessment.delay_probability * 100)}%`],
                ['Projects Tracked', assessment.past_projects],
              ].map(([label, value]) => (
                <div key={String(label)} className="card-glass" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ color: '#94A3B8', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: '#F8FAFC', lineHeight: 1 }}>{String(value)}</div>
                </div>
              ))}
            </div>

            {/* Split layout: Reason & Alerts */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, alignItems: 'start' }}>
              
              <div className="card-glass" style={{ minHeight: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
                <h3 style={{ marginTop: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Prediction Reason</h3>
                <p style={{ color: '#94A3B8', lineHeight: 1.7, fontSize: 13.5, margin: 0 }}>
                  {assessment.prediction_reason}
                </p>
              </div>
              
              <RiskAlertsPanel alerts={assessment.alerts} />
            </div>

            <RiskTrendVisualization trend={history} />
          </div>
        ) : (
          <div className="card-glass" style={{ padding: 48, textAlign: 'center', color: '#94A3B8' }}>
            Select a registered supplier from the dropdown above to view their comprehensive risk analysis.
          </div>
        )}
      </div>
    </div>
  );
}
