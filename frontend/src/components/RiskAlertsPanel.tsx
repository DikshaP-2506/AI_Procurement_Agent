import React from 'react';
import type { RiskAlert } from '../types/risk';

function severityColor(severity: RiskAlert['severity']) {
  if (severity === 'high') return '#F87171';
  if (severity === 'medium') return '#F59E0B';
  return '#34D399';
}

export default function RiskAlertsPanel({ alerts }: { alerts: RiskAlert[] }) {
  return (
    <div className="card-glass">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Risk Alerts</h3>
        <span style={{ color: '#94A3B8', fontSize: 12, background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: 4 }}>
          {alerts.length} signals
        </span>
      </div>
      {alerts.length === 0 ? (
        <div style={{ color: '#94A3B8', fontSize: 13.5 }}>No risk alerts found.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {alerts.map((alert, index) => (
            <div key={`${alert.alert_type}-${index}`} style={{ padding: 14, borderRadius: 12, border: '1px solid rgba(255, 255, 255, 0.04)', background: 'rgba(0, 0, 0, 0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                <strong style={{ color: '#F8FAFC', fontSize: 14.5 }}>{alert.alert_type.replace(/_/g, ' ')}</strong>
                <span style={{ 
                  color: severityColor(alert.severity), 
                  textTransform: 'uppercase', 
                  fontSize: 11, 
                  fontWeight: 700,
                  background: 'rgba(0,0,0,0.2)',
                  padding: '2px 6px',
                  borderRadius: 6,
                  border: `1px solid ${severityColor(alert.severity)}33`
                }}>
                  {alert.severity}
                </span>
              </div>
              <div style={{ color: '#94A3B8', marginTop: 8, lineHeight: 1.5, fontSize: 13 }}>{alert.message}</div>
              <div style={{ color: '#64748B', fontSize: 11, marginTop: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Source: {alert.source}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
