import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import RiskAlertsPanel from '../components/RiskAlertsPanel';
import RiskTrendVisualization from '../components/RiskTrendVisualization';
import { getRiskDashboard } from '../api/riskApi';
import type { RiskDashboardResponse } from '../types/risk';

function levelColor(level: 'low' | 'medium' | 'high') {
  if (level === 'high') return '#F87171';
  if (level === 'medium') return '#F59E0B';
  return '#34D399';
}

export default function RiskDashboard() {
  const [dashboard, setDashboard] = useState<RiskDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const response = await getRiskDashboard();
      setDashboard(response);
    } catch (err) {
      setError('Unable to load the risk dashboard. Create a vendor analysis first or verify the backend is running.');
    }
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      <Navbar />
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 16px 48px' }}>
        <div style={{ marginBottom: 24 }}>
          <p style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94A3B8', fontSize: 12 }}>Risk Intelligence</p>
          <h1 style={{ margin: '8px 0 10px', fontSize: 'clamp(2rem, 4vw, 3.4rem)', lineHeight: 1 }}>Risk Dashboard</h1>
          <p style={{ margin: 0, color: '#CBD5E1', maxWidth: 760 }}>A combined view of vendor risk snapshots, delays, and external signals designed for Member 2’s recommendation pipeline.</p>
        </div>

        {error && <div style={{ marginBottom: 16, color: '#F87171' }}>{error}</div>}

        {dashboard ? (
          <div style={{ display: 'grid', gap: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 16 }}>
              {[
                ['Analyzed', dashboard.total_vendors_analyzed],
                ['High Risk', dashboard.high_risk_vendors],
                ['Medium Risk', dashboard.medium_risk_vendors],
                ['Low Risk', dashboard.low_risk_vendors],
              ].map(([label, value]) => (
                <div key={String(label)} style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
                  <div style={{ color: '#94A3B8', fontSize: 12 }}>{label}</div>
                  <div style={{ marginTop: 8, fontSize: 30, fontWeight: 800, color: '#F8FAFC' }}>{String(value)}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 0.95fr', gap: 16 }}>
              <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h3 style={{ margin: 0 }}>Latest Assessments</h3>
                  <span style={{ color: '#94A3B8', fontSize: 12 }}>Top {dashboard.assessments.length}</span>
                </div>
                <div style={{ display: 'grid', gap: 10 }}>
                  {dashboard.assessments.slice(0, 8).map(assessment => (
                    <div key={`${assessment.vendor_id}-${assessment.created_at || assessment.final_risk_score}`} style={{ border: '1px solid #1F1F2E', borderRadius: 12, padding: 12, background: '#0C0C12' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                        <div>
                          <div style={{ color: '#F8FAFC', fontWeight: 700 }}>{assessment.vendor_name || assessment.vendor_id}</div>
                          <div style={{ color: '#94A3B8', fontSize: 12 }}>{assessment.vendor_id}</div>
                        </div>
                        <div style={{ color: levelColor(assessment.final_risk_level), fontWeight: 800 }}>{assessment.final_risk_score}</div>
                      </div>
                      <div style={{ color: '#CBD5E1', marginTop: 8, lineHeight: 1.5 }}>{assessment.prediction_reason}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'grid', gap: 16 }}>
                <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
                  <div style={{ color: '#94A3B8', fontSize: 12 }}>Average Final Risk Score</div>
                  <div style={{ marginTop: 8, fontSize: 40, fontWeight: 800, color: '#F8FAFC' }}>{dashboard.average_final_risk_score}</div>
                </div>
                <RiskAlertsPanel alerts={dashboard.assessments.flatMap(item => item.alerts).slice(0, 6)} />
              </div>
            </div>

            <RiskTrendVisualization trend={dashboard.trend} />
          </div>
        ) : (
          <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 20, color: '#94A3B8' }}>
            Loading risk dashboard...
          </div>
        )}
      </div>
    </div>
  );
}
