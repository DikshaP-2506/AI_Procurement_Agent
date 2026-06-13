import React from 'react';
import type { RiskTrendPoint } from '../types/risk';

function colorForLevel(level: RiskTrendPoint['final_risk_level']) {
  if (level === 'high') return '#F87171';
  if (level === 'medium') return '#F59E0B';
  return '#34D399';
}

export default function RiskTrendVisualization({ trend }: { trend: RiskTrendPoint[] }) {
  const width = 720;
  const height = 220;
  const points = trend.slice().reverse();
  const values = points.map(point => point.final_risk_score);
  const max = Math.max(100, ...values, 1);
  const step = points.length > 1 ? width / (points.length - 1) : width;

  const path = points
    .map((point, index) => {
      const x = index * step;
      const y = height - (point.final_risk_score / max) * (height - 24) - 8;
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');

  return (
    <div className="card-glass">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Risk Trend</h3>
        <span style={{ color: '#94A3B8', fontSize: 12, background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: 4 }}>
          {points.length} snapshots
        </span>
      </div>
      {points.length === 0 ? (
        <div style={{ color: '#94A3B8', fontSize: 13.5 }}>No trend data yet. Run an analysis to generate history.</div>
      ) : (
        <>
          <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '16px', borderRadius: 12, border: '1px solid rgba(255, 255, 255, 0.04)', overflow: 'hidden' }}>
            <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="220" role="img" aria-label="Risk trend chart">
              <defs>
                <linearGradient id="riskTrendStroke" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#3B82F6" />
                  <stop offset="100%" stopColor="#8B5CF6" />
                </linearGradient>
              </defs>
              <path d={path} fill="none" stroke="url(#riskTrendStroke)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              {points.map((point, index) => {
                const x = index * step;
                const y = height - (point.final_risk_score / max) * (height - 24) - 8;
                return <circle key={`${point.created_at}-${index}`} cx={x} cy={y} r="5" fill={colorForLevel(point.final_risk_level)} stroke="rgba(0,0,0,0.5)" strokeWidth="1.5" />;
              })}
            </svg>
          </div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 14, color: '#94A3B8', fontSize: 12, justifyContent: 'center' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#EF4444', display: 'inline-block' }} /> High Risk
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#F59E0B', display: 'inline-block' }} /> Medium Risk
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} /> Low Risk
            </span>
          </div>
        </>
      )}
    </div>
  );
}
