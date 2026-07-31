import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import RiskAlertsPanel from '../components/RiskAlertsPanel';
import RiskTrendVisualization from '../components/RiskTrendVisualization';
import { getRiskDashboard } from '../api/riskApi';
import type { RiskDashboardResponse } from '../types/risk';
import { useProcurement } from '../context/ProcurementContext';

function levelColor(level: 'low' | 'medium' | 'high') {
  if (level === 'high') return '#F87171';
  if (level === 'medium') return '#F59E0B';
  return '#34D399';
}

export default function RiskDashboard() {
  const { selectedProcurementId } = useProcurement();
  const [dashboard, setDashboard] = useState<RiskDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, [selectedProcurementId]);

  async function load() {
    try {
      const response = await getRiskDashboard(selectedProcurementId || undefined);
      setDashboard(response);
    } catch (err) {
      setError('Unable to load the risk dashboard. Create a vendor analysis first or verify the backend is running.');
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0A0A0F' }}>
      <Navbar />
      <div className="app-container" style={{ maxWidth: 1280 }}>
        
        {/* Page Header */}
        <div style={{ marginBottom: 24 }}>
          <p style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94A3B8', fontSize: 11, fontWeight: 700 }}>
            Risk Intelligence
          </p>
          <h1 style={{ margin: '8px 0 10px', background: 'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Risk Dashboard
          </h1>
          <p style={{ margin: 0, color: '#94A3B8', maxWidth: 760 }}>
            A combined view of vendor risk snapshots, delays, and external signals designed for the active recommendation pipeline.
          </p>
        </div>

        {error && (
          <div style={{ 
            marginBottom: 20, 
            padding: '12px 14px', 
            background: 'rgba(239, 68, 68, 0.08)', 
            border: '1px solid rgba(239, 68, 68, 0.2)', 
            borderRadius: 10, 
            color: '#FCA5A5', 
            fontSize: 14 
          }}>
            {error}
          </div>
        )}

        {dashboard ? (
          <div style={{ display: 'grid', gap: 24 }}>
            
            {/* Top Stat Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
              {[
                ['Analyzed Vendors', dashboard.total_vendors_analyzed, '#3B82F6'],
                ['High Risk Vendors', dashboard.high_risk_vendors, '#EF4444'],
                ['Medium Risk Vendors', dashboard.medium_risk_vendors, '#F59E0B'],
                ['Low Risk Vendors', dashboard.low_risk_vendors, '#10B981'],
              ].map(([label, value, color]) => (
                <div key={String(label)} className="card-glass" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ color: '#94A3B8', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 36, fontWeight: 800, color: String(color), lineHeight: 1 }}>
                    {String(value)}
                  </div>
                </div>
              ))}
            </div>

            {/* Split Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, alignItems: 'start' }}>
              
              {/* Left Box: Latest Assessments */}
              <div className="card-glass">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Latest Assessments</h3>
                  <span style={{ color: '#94A3B8', fontSize: 12, background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: 4 }}>
                    Top {dashboard.assessments.length}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {dashboard.assessments.slice(0, 8).map(assessment => (
                    <div 
                      key={`${assessment.vendor_id}-${assessment.created_at || assessment.final_risk_score}`} 
                      style={{ 
                        border: '1px solid rgba(255, 255, 255, 0.04)', 
                        borderRadius: 12, 
                        padding: 14, 
                        background: 'rgba(0, 0, 0, 0.2)',
                        transition: 'border-color 0.2s ease'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                        <div>
                          <div style={{ color: '#F8FAFC', fontWeight: 700, fontSize: 14.5 }}>
                            {assessment.vendor_name || assessment.vendor_id}
                          </div>
                          <div style={{ color: '#94A3B8', fontSize: 11, marginTop: 2 }}>
                            ID: {assessment.vendor_id.slice(0, 8)}...
                          </div>
                        </div>
                        <div style={{ 
                          color: levelColor(assessment.final_risk_level), 
                          fontWeight: 800, 
                          fontSize: 18,
                          background: 'rgba(0,0,0,0.3)',
                          padding: '4px 10px',
                          borderRadius: 8,
                          border: `1px solid ${levelColor(assessment.final_risk_level)}44`
                        }}>
                          {assessment.final_risk_score}
                        </div>
                      </div>
                      <div style={{ color: '#94A3B8', marginTop: 10, lineHeight: 1.5, fontSize: 13 }}>
                        {assessment.prediction_reason}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Box: Average Score & Alerts */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <div className="card-glass" style={{ display: 'flex', flexDirection: 'column', gap: 10, background: 'linear-gradient(135deg, rgba(16, 20, 38, 0.6) 0%, rgba(59, 130, 246, 0.05) 100%)' }}>
                  <div style={{ color: '#94A3B8', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Average Final Risk Score
                  </div>
                  <div style={{ fontSize: 48, fontWeight: 800, color: '#3B82F6', lineHeight: 1 }}>
                    {dashboard.average_final_risk_score}
                  </div>
                  <p style={{ margin: 0, fontSize: 12, color: '#94A3B8' }}>
                    Calculated dynamically across all registered procurement vendors.
                  </p>
                </div>
                
                <RiskAlertsPanel alerts={dashboard.assessments.flatMap(item => item.alerts).slice(0, 6)} />
              </div>

            </div>

            <RiskTrendVisualization trend={dashboard.trend} />
          </div>
        ) : (
          <div className="card-glass" style={{ padding: 48, textAlign: 'center', color: '#94A3B8' }}>
            Loading risk dashboard...
          </div>
        )}
      </div>
    </div>
  );
}
