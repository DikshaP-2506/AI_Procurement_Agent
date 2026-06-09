import React from 'react';
import type { RiskAlert } from '../types/risk';

function severityColor(severity: RiskAlert['severity']) {
  if (severity === 'high') return '#F87171';
  if (severity === 'medium') return '#F59E0B';
  return '#34D399';
}

export default function RiskAlertsPanel({ alerts }: { alerts: RiskAlert[] }) {
  return (
    <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>Risk Alerts</h3>
        <span style={{ color: '#94A3B8', fontSize: 12 }}>{alerts.length} signals</span>
      </div>
      {alerts.length === 0 ? (
        <div style={{ color: '#94A3B8' }}>No risk alerts found for this vendor.</div>
      ) : (
        <div style={{ display: 'grid', gap: 10 }}>
          {alerts.map((alert, index) => (
            <div key={`${alert.alert_type}-${index}`} style={{ padding: 12, borderRadius: 12, border: '1px solid #1F1F2E', background: '#0C0C12' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <strong style={{ color: '#F8FAFC' }}>{alert.alert_type.replace(/_/g, ' ')}</strong>
                <span style={{ color: severityColor(alert.severity), textTransform: 'uppercase', fontSize: 12 }}>{alert.severity}</span>
              </div>
              <div style={{ color: '#CBD5E1', marginTop: 6, lineHeight: 1.5 }}>{alert.message}</div>
              <div style={{ color: '#64748B', fontSize: 12, marginTop: 8 }}>Source: {alert.source}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
