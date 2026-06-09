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
    <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>Risk Trend</h3>
        <span style={{ color: '#94A3B8', fontSize: 12 }}>{points.length} snapshots</span>
      </div>
      {points.length === 0 ? (
        <div style={{ color: '#94A3B8' }}>No trend data yet. Run an analysis to generate history.</div>
      ) : (
        <>
          <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="220" role="img" aria-label="Risk trend chart">
            <defs>
              <linearGradient id="riskTrendStroke" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#60A5FA" />
                <stop offset="100%" stopColor="#A78BFA" />
              </linearGradient>
            </defs>
            <path d={path} fill="none" stroke="url(#riskTrendStroke)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            {points.map((point, index) => {
              const x = index * step;
              const y = height - (point.final_risk_score / max) * (height - 24) - 8;
              return <circle key={`${point.created_at}-${index}`} cx={x} cy={y} r="5" fill={colorForLevel(point.final_risk_level)} />;
            })}
          </svg>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 8, color: '#94A3B8', fontSize: 12 }}>
            <span>High risk = red</span>
            <span>Medium risk = amber</span>
            <span>Low risk = green</span>
          </div>
        </>
      )}
    </div>
  );
}
