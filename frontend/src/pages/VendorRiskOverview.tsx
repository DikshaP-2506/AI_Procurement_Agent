import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import Navbar from '../components/Navbar';
import RiskAlertsPanel from '../components/RiskAlertsPanel';
import RiskTrendVisualization from '../components/RiskTrendVisualization';
import { analyzeVendorRisk, getVendorRisk, getVendorRiskHistory } from '../api/riskApi';
import type { RiskAssessment, RiskTrendPoint } from '../types/risk';

function levelColor(level: RiskAssessment['final_risk_level']) {
  if (level === 'high') return '#F87171';
  if (level === 'medium') return '#F59E0B';
  return '#34D399';
}

export default function VendorRiskOverview() {
  const params = useParams<{ vendorId?: string }>();
  const [vendorId, setVendorId] = useState<string>(params.vendorId ?? '');
  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [history, setHistory] = useState<RiskTrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <div style={{ minHeight: '100vh' }}>
      <Navbar />
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '96px 16px 48px' }}>
        <div style={{ marginBottom: 24 }}>
          <p style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94A3B8', fontSize: 12 }}>Risk Intelligence</p>
          <h1 style={{ margin: '8px 0 10px', fontSize: 'clamp(2rem, 4vw, 3.4rem)', lineHeight: 1 }}>Vendor Risk Overview</h1>
          <p style={{ margin: 0, color: '#CBD5E1', maxWidth: 760 }}>Analyze historical performance, external risk signals, and delay probability for a single vendor snapshot.</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 16, marginBottom: 16 }}>
          <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
            <label style={{ display: 'block', marginBottom: 8 }}>Vendor ID</label>
            <div style={{ display: 'flex', gap: 12 }}>
              <input
                value={vendorId}
                onChange={(e: { target: { value: string } }) => setVendorId(e.target.value)}
                placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
              />
              <button
                onClick={() => vendorId && void loadVendorRisk(vendorId)}
                disabled={loading}
                style={{ background: '#60A5FA', color: '#081120', border: 'none', borderRadius: 10, padding: '10px 14px', fontWeight: 700, minWidth: 120 }}
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
            </div>
            {error && <div style={{ color: '#F87171', marginTop: 10 }}>{error}</div>}
          </div>

          <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16, display: 'grid', gap: 8 }}>
            <div style={{ color: '#94A3B8', fontSize: 12 }}>Current risk</div>
            <div style={{ fontSize: 34, fontWeight: 800, color: summaryTone }}>{assessment ? assessment.final_risk_score : '--'}</div>
            <div style={{ color: '#CBD5E1' }}>{assessment ? assessment.final_risk_level.toUpperCase() : 'No vendor selected'}</div>
          </div>
        </div>

        {assessment ? (
          <div style={{ display: 'grid', gap: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 16 }}>
              {[
                ['Historical Score', assessment.historical_score],
                ['Market Risk', assessment.risk_score],
                ['Delay Probability', `${Math.round(assessment.delay_probability * 100)}%`],
                ['Projects Tracked', assessment.past_projects],
              ].map(([label, value]) => (
                <div key={String(label)} style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
                  <div style={{ color: '#94A3B8', fontSize: 12 }}>{label}</div>
                  <div style={{ marginTop: 8, fontSize: 28, fontWeight: 800, color: '#F8FAFC' }}>{String(value)}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
                <h3 style={{ marginTop: 0 }}>Prediction Reason</h3>
                <p style={{ color: '#CBD5E1', lineHeight: 1.7, marginBottom: 0 }}>{assessment.prediction_reason}</p>
              </div>
              <RiskAlertsPanel alerts={assessment.alerts} />
            </div>

            <RiskTrendVisualization trend={history} />
          </div>
        ) : (
          <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 20, color: '#94A3B8' }}>
            Enter a vendor id to view the risk overview.
          </div>
        )}
      </div>
    </div>
  );
}
