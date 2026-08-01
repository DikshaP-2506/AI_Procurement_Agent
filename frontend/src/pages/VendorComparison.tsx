import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Vendor, VendorQuote } from '../types/vendor';
import { getVendors, getVendorQuotes } from '../api/vendorApi';
import { getRecommendations, applyRecommendation, Weights, VendorRecommendation, RecommendationResponse } from '../api/recommendationApi';
import Navbar from '../components/Navbar';
import { useProcurement } from '../context/ProcurementContext';

export default function VendorComparison() {
  const { selectedProcurementId } = useProcurement();

  // Existing state to preserve original table functionality
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [quotesMap, setQuotesMap] = useState<Record<string, VendorQuote[]>>({});

  // Simulator-specific state
  const [weights, setWeights] = useState<Weights>({ cost: 20, risk: 20, support: 20, delivery: 20, warranty: 10, esg: 10 });
  const [qualitativeAdjustments, setQualitativeAdjustments] = useState<Record<string, number>>({});
  const [rankedRecommendations, setRankedRecommendations] = useState<VendorRecommendation[]>([]);
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const [comparisonSummary, setComparisonSummary] = useState<string>('');
  const [recommendationData, setRecommendationData] = useState<RecommendationResponse | null>(null);
  const [activeExplainabilityTab, setActiveExplainabilityTab] = useState<'overview' | 'reasoning' | 'plan' | 'risks'>('overview');
  const [apiWarning, setApiWarning] = useState<string | null>(null);

  // Loading & Action states
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  // Apply reasoning modal state
  const [selectedVendorForApply, setSelectedVendorForApply] = useState<VendorRecommendation | null>(null);
  const [applyReasoning, setApplyReasoning] = useState<string>('');

  useEffect(() => {
    if (selectedProcurementId) {
      loadBaseData();
    }
  }, [selectedProcurementId]);

  // Fetch recommendations whenever weights, qualitative adjustments, or selected project change
  useEffect(() => {
    if (selectedProcurementId) {
      fetchSimulatedRankings();
    }
  }, [selectedProcurementId, weights, qualitativeAdjustments]);

  async function loadBaseData() {
    if (!selectedProcurementId) return;
    try {
      setLoading(true);
      const vs = await getVendors(selectedProcurementId);

      const map: Record<string, VendorQuote[]> = {};
      await Promise.all(vs.map(async v => {
        const q = await getVendorQuotes(v.id);
        map[v.id] = q;
      }));

      // Deduplicate vendors by name, preferring the one with quotes
      const uniqueVendorsMap: Record<string, Vendor> = {};
      vs.forEach(v => {
        const hasQuote = map[v.id] && map[v.id].length > 0;
        const existing = uniqueVendorsMap[v.vendor_name];

        if (!existing) {
          uniqueVendorsMap[v.vendor_name] = v;
        } else {
          const existingHasQuote = map[existing.id] && map[existing.id].length > 0;
          if (!existingHasQuote && hasQuote) {
            uniqueVendorsMap[v.vendor_name] = v;
          }
        }
      });

      const filteredVs = Object.values(uniqueVendorsMap);
      setVendors(filteredVs);
      setQuotesMap(map);

      // Initialize default qualitative adjustments to 0 for all vendors
      const initialOffsets: Record<string, number> = {};
      filteredVs.forEach(v => {
        initialOffsets[v.id] = 0;
      });
      setQualitativeAdjustments(initialOffsets);

    } catch (e) {
      console.error("Failed to load base comparison data", e);
    } finally {
      setLoading(false);
    }
  }

  async function fetchSimulatedRankings() {
    if (!selectedProcurementId) return;
    try {
      const res = await getRecommendations(selectedProcurementId, weights, qualitativeAdjustments);
      setRankedRecommendations(res.recommendations);
      setComparisonSummary(res.comparison_summary);
      setRecommendationData(res);
      setApiWarning(res.warning || null);
    } catch (e) {
      console.error("Failed to fetch simulated rankings", e);
    }
  }


  // Preset Handlers
  const applyPreset = (presetName: string) => {
    if (presetName === 'cost') {
      setWeights({ cost: 60, risk: 10, support: 10, delivery: 10, warranty: 5, esg: 5 });
    } else if (presetName === 'risk') {
      setWeights({ cost: 10, risk: 60, support: 10, delivery: 10, warranty: 5, esg: 5 });
    } else if (presetName === 'support') {
      setWeights({ cost: 10, risk: 10, support: 60, delivery: 10, warranty: 5, esg: 5 });
    } else if (presetName === 'delivery') {
      setWeights({ cost: 10, risk: 10, support: 10, delivery: 60, warranty: 5, esg: 5 });
    } else if (presetName === 'warranty') {
      setWeights({ cost: 10, risk: 10, support: 10, delivery: 10, warranty: 55, esg: 5 });
    } else if (presetName === 'esg') {
      setWeights({ cost: 10, risk: 10, support: 10, delivery: 10, warranty: 5, esg: 55 });
    } else {
      setWeights({ cost: 20, risk: 20, support: 20, delivery: 20, warranty: 10, esg: 10 });
    }
  };

  // Weight Slider Change Handler
  const handleWeightChange = (key: keyof Weights, value: number) => {
    setWeights(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // Qualitative Adjustment Change Handler
  const handleAdjustmentChange = (vendorId: string, value: number) => {
    setQualitativeAdjustments(prev => ({
      ...prev,
      [vendorId]: value
    }));
  };

  // Action Apply Decision Handler
  async function onApplyDecision(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedVendorForApply) return;

    try {
      setActionLoading(true);
      setMessage(null);

      const res = await applyRecommendation(
        selectedProcurementId,
        selectedVendorForApply.vendor_id,
        weights,
        applyReasoning || `Selected ${selectedVendorForApply.vendor_name} based on simulator scoring (Total Score: ${selectedVendorForApply.final_score}).`
      );

      setMessage({ text: `Decision Saved! Chosen vendor locked in. Logged to audit ID: ${res.audit_log_id.slice(0, 8)}...`, isError: false });
      setSelectedVendorForApply(null);
      setApplyReasoning('');

      // Reload base data to show completed status on procurements table
      loadBaseData();

      // Clear alert message after 6 seconds
      setTimeout(() => setMessage(null), 6000);

    } catch (err: any) {
      console.error(err);
      setMessage({ text: err.response?.data?.detail || "Failed to apply and save recommendation.", isError: true });
    } finally {
      setActionLoading(false);
    }
  }

  // Get score color
  const getScoreColor = (score: number) => {
    if (score >= 80) return '#10B981'; // Green
    if (score >= 50) return '#F59E0B'; // Amber
    return '#EF4444'; // Red
  };

  const renderFormattedField = (val: any, fallbackStr: string = '') => {
    if (!val) {
      return <p style={{ color: '#94A3B8', fontSize: 13.5, fontStyle: 'italic', margin: 0 }}>{fallbackStr || 'Not available'}</p>;
    }

    if (typeof val === 'string') {
      const trimmed = val.trim();
      if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
        try {
          const jsonVal = JSON.parse(trimmed.replace(/'/g, '"'));
          return renderFormattedField(jsonVal);
        } catch (e) {
          // Ignore and render as string
        }
      }

      return (
        <div style={{ color: '#E2E8F0', fontSize: 13.5, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
          {trimmed.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={index} style={{ color: '#FFFFFF', fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
            }
            return part;
          })}
        </div>
      );
    }

    if (Array.isArray(val)) {
      return (
        <ul style={{ margin: '8px 0', paddingLeft: 20, color: '#E2E8F0', fontSize: 13.5, lineHeight: 1.6 }}>
          {val.map((item, idx) => (
            <li key={idx} style={{ marginBottom: 6 }}>
              {typeof item === 'string' ? (
                item.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
                  if (part.startsWith('**') && part.endsWith('**')) {
                    return <strong key={index} style={{ color: '#FFFFFF', fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
                  }
                  return part;
                })
              ) : (
                JSON.stringify(item)
              )}
            </li>
          ))}
        </ul>
      );
    }

    if (typeof val === 'object') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
          {Object.entries(val).map(([key, value]: [string, any]) => {
            if (value && typeof value === 'object' && ('risk_score' in value || 'risks' in value)) {
              const score = value.risk_score;
              const risksList = value.risks;
              return (
                <div key={key} style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.05)', padding: 12, borderRadius: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, color: '#FFFFFF', fontSize: 14 }}>{key}</span>
                    {score !== undefined && (
                      <span style={{ fontSize: 11, fontWeight: 700, background: score > 40 ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.12)', color: score > 40 ? '#F87171' : '#34D399', border: score > 40 ? '1px solid rgba(239, 68, 68, 0.2)' : '1px solid rgba(16, 185, 129, 0.2)', padding: '2px 8px', borderRadius: 4 }}>
                        Risk Score: {score}/100
                      </span>
                    )}
                  </div>
                  {Array.isArray(risksList) && risksList.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: 18, color: '#94A3B8', fontSize: 12.5, lineHeight: 1.5 }}>
                      {risksList.map((r: string, i: number) => (
                        <li key={i} style={{ marginBottom: 4 }}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ color: '#10B981', fontSize: 12.5, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ fontSize: 14 }}>✓</span> No significant risk alerts flagged.
                    </div>
                  )}
                </div>
              );
            }

            return (
              <div key={key} style={{ background: 'rgba(255, 255, 255, 0.01)', border: '1px solid rgba(255, 255, 255, 0.04)', padding: 10, borderRadius: 8 }}>
                <span style={{ fontWeight: 700, color: '#60A5FA', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{key.replace(/_/g, ' ')}</span>
                <div style={{ marginTop: 4 }}>{renderFormattedField(value)}</div>
              </div>
            );
          })}
        </div>
      );
    }

    return <span style={{ color: '#E2E8F0', fontSize: 13.5 }}>{String(val)}</span>;
  };

  const defaultSelectedVendor = rankedRecommendations[0] || null;
  const currentSelectedVendor = rankedRecommendations.find(r => r.vendor_id === selectedVendorId) || defaultSelectedVendor;

  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh', paddingBottom: 80 }}>
      <Navbar />
      <div style={{ padding: '80px 16px 20px', maxWidth: 1200, margin: '0 auto' }}>

        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h1 style={{ fontSize: '2.5rem', fontWeight: 800, margin: 0, background: 'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Vendor Decision Simulator
            </h1>
            <p style={{ color: '#9CA3AF', marginTop: 4 }}>
              Deterministic trade-off simulator & explainability engine. Custom-weight parameters to rank quotes.
            </p>
          </div>
        </div>

        {/* Global Messages */}
        {message && (
          <div style={{
            marginTop: 16,
            padding: '12px 16px',
            borderRadius: 8,
            border: `1px solid ${message.isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
            background: message.isError ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)',
            color: message.isError ? '#FCA5A5' : '#D1FAE5',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 14
          }}>
            <span style={{ fontSize: 14, fontWeight: 700 }}>{message.isError ? 'Error: ' : 'Success: '}</span>
            {message.text}
          </div>
        )}

        {/* ========================================== */}
        {/* SIMULATOR TWO-COLUMN VIEW                  */}
        {/* ========================================== */}
        {loading ? (
          <div style={{ padding: 80, textAlign: 'center', color: '#94A3B8' }}>
            Loading simulation data...
          </div>
        ) : rankedRecommendations.length === 0 ? (
          <div className="card-glass" style={{
            marginTop: 48,
            padding: '80px 48px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 20,
            maxWidth: 600,
            margin: '40px auto 0'
          }}>
            <div style={{
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              width: 80,
              height: 80,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#3B82F6'
            }}>
              <svg style={{ width: 36, height: 36 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>

            <div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', marginBottom: 8 }}>
                No Active Quotes Found
              </h2>
              <p style={{ color: '#94A3B8', fontSize: 14, maxWidth: 440, margin: '0 auto', lineHeight: 1.6 }}>
                To use the Vendor Decision Simulator and run dynamic AI evaluations, you first need to upload quotation documents.
              </p>
            </div>

            <Link
              to="/upload"
              style={{
                background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                color: '#FFFFFF',
                textDecoration: 'none',
                padding: '12px 28px',
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 700,
                boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
                transition: 'all 0.2s'
              }}
            >
              Upload Vendor Quotes
            </Link>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* TOP SECTION: SPLIT LAYOUT GRID */}
            <div className="simulator-split-grid">

              {/* LEFT COLUMN: CRITERIA WEIGHT SLIDERS (40% width on Desktop) */}
              <div style={{
                background: 'rgba(16, 20, 38, 0.6)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 16,
                padding: 24,
                boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)'
              }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: 8 }}>
                  Trade-Off Weights
                </h2>
                <p style={{ color: '#94A3B8', fontSize: 13, marginBottom: 20 }}>
                  Adjust sliders to balance priorities. Sum: {weights.cost + weights.risk + weights.support + weights.delivery + (weights.warranty || 0) + (weights.esg || 0)}%
                </p>

                {/* Presets Grid */}
                <div style={{ marginBottom: 24 }}>
                  <div style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                    Quick Presets
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                    <button
                      onClick={() => applyPreset('cost')}
                      style={{
                        background: weights.cost === 60 ? 'rgba(59, 130, 246, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        border: `1px solid ${weights.cost === 60 ? '#3B82F6' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: weights.cost === 60 ? '#60A5FA' : '#94A3B8',
                        padding: '10px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        textAlign: 'left',
                        fontWeight: 600,
                        transition: 'all 0.2s'
                      }}
                    >
                      Minimize Cost
                    </button>
                    <button
                      onClick={() => applyPreset('risk')}
                      style={{
                        background: weights.risk === 60 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        border: `1px solid ${weights.risk === 60 ? '#10B981' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: weights.risk === 60 ? '#34D399' : '#94A3B8',
                        padding: '10px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        textAlign: 'left',
                        fontWeight: 600,
                        transition: 'all 0.2s'
                      }}
                    >
                      Low Risk Focus
                    </button>
                    <button
                      onClick={() => applyPreset('delivery')}
                      style={{
                        background: weights.delivery === 60 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        border: `1px solid ${weights.delivery === 60 ? '#F59E0B' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: weights.delivery === 60 ? '#FBBF24' : '#94A3B8',
                        padding: '10px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        textAlign: 'left',
                        fontWeight: 600,
                        transition: 'all 0.2s'
                      }}
                    >
                      Fast Delivery
                    </button>
                    <button
                      onClick={() => applyPreset('warranty')}
                      style={{
                        background: weights.warranty === 55 ? 'rgba(236, 72, 153, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        border: `1px solid ${weights.warranty === 55 ? '#EC4899' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: weights.warranty === 55 ? '#F472B6' : '#94A3B8',
                        padding: '10px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        textAlign: 'left',
                        fontWeight: 600,
                        transition: 'all 0.2s'
                      }}
                    >
                      Long Warranty
                    </button>
                    <button
                      onClick={() => applyPreset('esg')}
                      style={{
                        background: weights.esg === 55 ? 'rgba(20, 184, 166, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        border: `1px solid ${weights.esg === 55 ? '#14B8A6' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: weights.esg === 55 ? '#2DD4BF' : '#94A3B8',
                        padding: '10px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        textAlign: 'left',
                        fontWeight: 600,
                        transition: 'all 0.2s'
                      }}
                    >
                      Sustainable ESG
                    </button>
                    <button
                      onClick={() => applyPreset('balanced')}
                      style={{
                        background: (weights.cost === 20 && weights.risk === 20) ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        border: `1px solid ${(weights.cost === 20 && weights.risk === 20) ? '#8B5CF6' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: (weights.cost === 20 && weights.risk === 20) ? '#A78BFA' : '#94A3B8',
                        padding: '10px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        textAlign: 'left',
                        fontWeight: 600,
                        transition: 'all 0.2s'
                      }}
                    >
                      Balanced Split
                    </button>
                  </div>
                </div>

                {/* Sliders Stack */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

                  {/* Cost Weight */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: '#E2E8F0', fontWeight: 600 }}>Cost Weight</span>
                      <span style={{ color: '#60A5FA', fontWeight: 700 }}>{weights.cost}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100" step="5"
                      value={weights.cost}
                      onChange={e => handleWeightChange('cost', Number(e.target.value))}
                      style={{ accentColor: '#3B82F6', cursor: 'pointer', width: '100%' }}
                    />
                  </div>

                  {/* Risk Weight */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: '#E2E8F0', fontWeight: 600 }}>Risk Safety Weight</span>
                      <span style={{ color: '#34D399', fontWeight: 700 }}>{weights.risk}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100" step="5"
                      value={weights.risk}
                      onChange={e => handleWeightChange('risk', Number(e.target.value))}
                      style={{ accentColor: '#10B981', cursor: 'pointer', width: '100%' }}
                    />
                  </div>

                  {/* Support Weight */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: '#E2E8F0', fontWeight: 600 }}>Support Quality Weight</span>
                      <span style={{ color: '#8B5CF6', fontWeight: 700 }}>{weights.support}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100" step="5"
                      value={weights.support}
                      onChange={e => handleWeightChange('support', Number(e.target.value))}
                      style={{ accentColor: '#8B5CF6', cursor: 'pointer', width: '100%' }}
                    />
                  </div>

                  {/* Delivery Weight */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: '#E2E8F0', fontWeight: 600 }}>Delivery Speed Weight</span>
                      <span style={{ color: '#FBBF24', fontWeight: 700 }}>{weights.delivery}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100" step="5"
                      value={weights.delivery}
                      onChange={e => handleWeightChange('delivery', Number(e.target.value))}
                      style={{ accentColor: '#F59E0B', cursor: 'pointer', width: '100%' }}
                    />
                  </div>

                  {/* Warranty Weight */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: '#E2E8F0', fontWeight: 600 }}>Warranty Weight</span>
                      <span style={{ color: '#EC4899', fontWeight: 700 }}>{weights.warranty || 0}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100" step="5"
                      value={weights.warranty || 0}
                      onChange={e => handleWeightChange('warranty', Number(e.target.value))}
                      style={{ accentColor: '#EC4899', cursor: 'pointer', width: '100%' }}
                    />
                  </div>

                  {/* ESG Weight */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: '#E2E8F0', fontWeight: 600 }}>ESG Sustainability Weight</span>
                      <span style={{ color: '#14B8A6', fontWeight: 700 }}>{weights.esg || 0}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100" step="5"
                      value={weights.esg || 0}
                      onChange={e => handleWeightChange('esg', Number(e.target.value))}
                      style={{ accentColor: '#14B8A6', cursor: 'pointer', width: '100%' }}
                    />
                  </div>

                </div>

                {apiWarning && (
                  <div style={{ marginTop: 20, padding: 12, borderRadius: 8, background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', color: '#FBBF24', fontSize: 12 }}>
                    Warning: {apiWarning}
                  </div>
                )}
              </div>

              {/* RIGHT COLUMN: SELECTED VENDOR PROFILE CARD (60% width on Desktop) */}
              <div>
                {(() => {
                  if (rankedRecommendations.length === 0) {
                    return (
                      <div className="card-glass" style={{
                        padding: '40px 24px',
                        textAlign: 'center',
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 16
                      }}>
                        <div style={{
                          background: 'rgba(59, 130, 246, 0.1)',
                          border: '1px solid rgba(59, 130, 246, 0.2)',
                          width: 54,
                          height: 54,
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: '#3B82F6'
                        }}>
                          <svg style={{ width: 24, height: 24 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                        </div>
                        <div>
                          <h4 style={{ color: '#FFFFFF', margin: '0 0 4px 0', fontSize: 15, fontWeight: 700 }}>No Active Quotes</h4>
                          <p style={{ color: '#94A3B8', fontSize: 13, margin: 0, lineHeight: 1.5 }}>
                            No active quotations have been uploaded for the current project. Upload quotes to compare metrics.
                          </p>
                        </div>
                        <Link
                          to="/upload"
                          style={{
                            background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                            color: '#FFFFFF',
                            textDecoration: 'none',
                            padding: '8px 16px',
                            borderRadius: 8,
                            fontSize: 12,
                            fontWeight: 700
                          }}
                        >
                          Go to Upload Tab
                        </Link>
                      </div>
                    );
                  }

                  if (!currentSelectedVendor) {
                    return (
                      <div className="card-glass" style={{ padding: 48, textAlign: 'center', color: '#94A3B8', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        Please select a supplier from the ranking list below to inspect their detailed parameters.
                      </div>
                    );
                  }

                  const cardBorder = currentSelectedVendor.rank === 1 ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)';
                  const rankBadgeColor = currentSelectedVendor.rank === 1 ? '#3B82F6' : currentSelectedVendor.rank === 2 ? '#6B7280' : '#4B5563';
                  const rawPrice = Number(currentSelectedVendor.breakdown.cost.raw);
                  const rawDelivery = Number(currentSelectedVendor.breakdown.delivery.raw);
                  const rawRisk = Number(currentSelectedVendor.breakdown.risk.raw);
                  const rawSupport = String(currentSelectedVendor.breakdown.support.raw);

                  return (
                    <div
                      style={{
                        background: 'rgba(16, 20, 38, 0.6)',
                        backdropFilter: 'blur(20px)',
                        WebkitBackdropFilter: 'blur(20px)',
                        border: cardBorder,
                        borderRadius: 16,
                        padding: 24,
                        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
                        position: 'relative',
                        overflow: 'hidden'
                      }}
                    >
                      {/* Rank Badge */}
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        background: rankBadgeColor,
                        color: '#FFFFFF',
                        fontSize: 11,
                        fontWeight: 800,
                        padding: '5px 14px',
                        borderBottomRightRadius: 10,
                        letterSpacing: '0.05em'
                      }}>
                        RANK #{currentSelectedVendor.rank} (SELECTED VENDOR)
                      </div>

                      {/* Confidence Score Badge */}
                      {currentSelectedVendor.confidence_score !== undefined && (
                        <div style={{
                          position: 'absolute',
                          top: 0,
                          right: 0,
                          background: 'rgba(255, 255, 255, 0.05)',
                          borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
                          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                          color: currentSelectedVendor.confidence_score >= 0.8 ? '#34D399' : currentSelectedVendor.confidence_score >= 0.5 ? '#FBBF24' : '#FCA5A5',
                          fontSize: 11,
                          fontWeight: 700,
                          padding: '5px 12px',
                          borderBottomLeftRadius: 10
                        }}>
                          Confidence: {Math.round(currentSelectedVendor.confidence_score * 100)}%
                        </div>
                      )}

                      {/* Vendor title and final score */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, marginBottom: 18 }}>
                        <div style={{ marginLeft: 4 }}>
                          <h3 style={{ fontSize: 20, fontWeight: 800, color: '#FFFFFF', margin: 0 }}>{currentSelectedVendor.vendor_name}</h3>
                          <span style={{ fontSize: 12, color: '#94A3B8' }}>ID: {currentSelectedVendor.vendor_id.slice(0, 8)}...</span>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '2rem', fontWeight: 800, color: getScoreColor(currentSelectedVendor.final_score), lineHeight: 1 }}>
                            {currentSelectedVendor.final_score.toFixed(1)}
                          </div>
                          <span style={{ fontSize: 10, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Total Score</span>
                        </div>
                      </div>

                      {/* Missing Details Banner */}
                      {currentSelectedVendor.missing_information && currentSelectedVendor.missing_information.length > 0 && (
                        <div style={{
                          marginBottom: 16,
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: 'rgba(239, 68, 68, 0.05)',
                          border: '1px solid rgba(239, 68, 68, 0.15)',
                          color: '#FCA5A5',
                          fontSize: 12
                        }}>
                          <strong>Missing Details:</strong> {currentSelectedVendor.missing_information.join(', ')}
                        </div>
                      )}

                      {/* Normalization Progress Bars */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13 }}>

                        {/* Price bar */}
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                            <span>Cost: <strong style={{ color: '#FFFFFF' }}>${rawPrice.toLocaleString()}</strong></span>
                            <span style={{ color: '#60A5FA', fontWeight: 600 }}>Score: {currentSelectedVendor.breakdown.cost.score}</span>
                          </div>
                          <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${currentSelectedVendor.breakdown.cost.score}%`, background: 'linear-gradient(90deg, #3B82F6 0%, #60A5FA 100%)', borderRadius: 99 }} />
                          </div>
                        </div>

                        {/* Risk bar */}
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                            <span>Risk Profile: <strong style={{ color: '#FFFFFF' }}>{rawRisk} (out of 100)</strong></span>
                            <span style={{ color: '#34D399', fontWeight: 600 }}>Safety: {currentSelectedVendor.breakdown.risk.score}</span>
                          </div>
                          <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${currentSelectedVendor.breakdown.risk.score}%`, background: 'linear-gradient(90deg, #10B981 0%, #34D399 100%)', borderRadius: 99 }} />
                          </div>
                        </div>

                        {/* Delivery bar */}
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                            <span>Delivery Speed: <strong style={{ color: '#FFFFFF' }}>{rawDelivery} days</strong></span>
                            <span style={{ color: '#FBBF24', fontWeight: 600 }}>Score: {currentSelectedVendor.breakdown.delivery.score}</span>
                          </div>
                          <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${currentSelectedVendor.breakdown.delivery.score}%`, background: 'linear-gradient(90deg, #F59E0B 0%, #FBBF24 100%)', borderRadius: 99 }} />
                          </div>
                        </div>

                        {/* Support bar */}
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                            <span>Support Level: <strong style={{ color: '#FFFFFF' }}>{rawSupport}</strong></span>
                            <span style={{ color: '#A78BFA', fontWeight: 600 }}>Score: {currentSelectedVendor.breakdown.support.score}</span>
                          </div>
                          <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${currentSelectedVendor.breakdown.support.score}%`, background: 'linear-gradient(90deg, #8B5CF6 0%, #A78BFA 100%)', borderRadius: 99 }} />
                          </div>
                        </div>

                        {/* Warranty bar */}
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                            <span>Warranty: <strong style={{ color: '#FFFFFF' }}>{currentSelectedVendor.breakdown.warranty?.raw || 'Data Not Available'}</strong></span>
                            <span style={{ color: '#EC4899', fontWeight: 600 }}>Score: {currentSelectedVendor.breakdown.warranty?.score ?? 0}</span>
                          </div>
                          <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${currentSelectedVendor.breakdown.warranty?.score ?? 0}%`, background: 'linear-gradient(90deg, #EC4899 0%, #F472B6 100%)', borderRadius: 99 }} />
                          </div>
                        </div>

                        {/* ESG Sustainability bar */}
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                            <span>ESG / Sustainability: <strong style={{ color: '#FFFFFF' }}>{currentSelectedVendor.breakdown.esg?.raw || 'Data Not Available'}</strong></span>
                            <span style={{ color: '#14B8A6', fontWeight: 600 }}>Score: {currentSelectedVendor.breakdown.esg?.score ?? 0}</span>
                          </div>
                          <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${currentSelectedVendor.breakdown.esg?.score ?? 0}%`, background: 'linear-gradient(90deg, #14B8A6 0%, #2DD4BF 100%)', borderRadius: 99 }} />
                          </div>
                        </div>

                      </div>

                      {/* Qualitative Adjustment Offset slider */}
                      <div style={{
                        marginTop: 16,
                        padding: 12,
                        borderRadius: 10,
                        background: 'rgba(0,0,0,0.2)',
                        border: '1px solid rgba(255,255,255,0.04)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div style={{ fontSize: 13 }}>
                          <span style={{ color: '#E2E8F0', fontWeight: 600 }}>Qualitative Adjustment</span>
                          <p style={{ color: '#94A3B8', fontSize: 11, margin: 0 }}>Add score offset for unmeasured traits (USPs)</p>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          <input
                            type="range" min="-20" max="20" step="1"
                            value={qualitativeAdjustments[currentSelectedVendor.vendor_id] || 0}
                            onChange={e => handleAdjustmentChange(currentSelectedVendor.vendor_id, Number(e.target.value))}
                            style={{ width: 120, accentColor: '#8B5CF6', height: 4 }}
                          />
                          <span style={{
                            fontSize: 13,
                            fontWeight: 700,
                            color: (qualitativeAdjustments[currentSelectedVendor.vendor_id] || 0) > 0 ? '#34D399' : (qualitativeAdjustments[currentSelectedVendor.vendor_id] || 0) < 0 ? '#EF4444' : '#94A3B8',
                            minWidth: 32,
                            textAlign: 'right'
                          }}>
                            {(qualitativeAdjustments[currentSelectedVendor.vendor_id] || 0) > 0 ? '+' : ''}{qualitativeAdjustments[currentSelectedVendor.vendor_id] || 0}
                          </span>
                        </div>
                      </div>

                      {/* Action Panel */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                        <span style={{ fontSize: 11, color: '#94A3B8', fontStyle: 'italic', maxWidth: '65%' }}>
                          W. Contribution: Cost {currentSelectedVendor.breakdown.cost.weighted} | Risk {currentSelectedVendor.breakdown.risk.weighted} | Support {currentSelectedVendor.breakdown.support.weighted} | Deliv {currentSelectedVendor.breakdown.delivery.weighted} | Warr {currentSelectedVendor.breakdown.warranty?.weighted ?? 0} | ESG {currentSelectedVendor.breakdown.esg?.weighted ?? 0}
                        </span>
                        <button
                          onClick={() => setSelectedVendorForApply(currentSelectedVendor)}
                          style={{
                            background: currentSelectedVendor.rank === 1 ? '#3B82F6' : 'transparent',
                            color: currentSelectedVendor.rank === 1 ? '#FFFFFF' : '#3B82F6',
                            border: '1px solid #3B82F6',
                            padding: '8px 16px',
                            borderRadius: 8,
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            boxShadow: currentSelectedVendor.rank === 1 ? '0 4px 12px rgba(59, 130, 246, 0.3)' : 'none'
                          }}
                        >
                          Apply Decision
                        </button>
                      </div>

                    </div>
                  );
                })()}
              </div>

            </div>

            {/* DOWNWARDS ARROW CONNECTOR */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '16px 0' }}>
              <div style={{
                background: 'rgba(59, 130, 246, 0.1)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                borderRadius: '50%',
                width: 42,
                height: 42,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#60A5FA',
                boxShadow: '0 4px 12px rgba(59, 130, 246, 0.15)'
              }}>
                <svg style={{ width: 20, height: 20 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <polyline points="19 12 12 19 5 12" />
                </svg>
              </div>
            </div>

            {/* FULL WIDTH VENDOR RANKING TABLE */}
            <div className="card-glass" style={{ padding: 24 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: '#FFFFFF', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <svg style={{ width: 16, height: 16, color: '#3B82F6' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 20h9M3 20h4M3 12h18M3 4h18" />
                </svg>
                Vendor Ranking Table
              </h3>

              <div style={{ overflowX: 'auto' }}>
                <table className="premium-table">
                  <thead>
                    <tr>
                      <th style={{ width: 80 }}>Rank</th>
                      <th>Vendor Name</th>
                      <th>Confidence</th>
                      <th>Cost</th>
                      <th>Delivery</th>
                      <th>Risk Profile</th>
                      <th>Support</th>
                      <th style={{ textAlign: 'right' }}>Total Score</th>
                      <th style={{ textAlign: 'right', width: 140 }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankedRecommendations.length === 0 ? (
                      vendors.map((v) => (
                        <tr key={v.id}>
                          <td style={{ color: '#6B7280', fontWeight: 700 }}>-</td>
                          <td style={{ fontWeight: 700, color: '#FFFFFF' }}>{v.vendor_name}</td>
                          <td style={{ color: '#6B7280' }}>-</td>
                          <td style={{ color: '#6B7280' }}>-</td>
                          <td style={{ color: '#6B7280' }}>-</td>
                          <td style={{ color: '#6B7280' }}>-</td>
                          <td style={{ color: '#6B7280' }}>-</td>
                          <td style={{ textAlign: 'right', color: '#6B7280', fontWeight: 700 }}>-</td>
                          <td style={{ textAlign: 'right' }}>
                            <Link
                              to="/upload"
                              style={{
                                background: 'rgba(59, 130, 246, 0.1)',
                                border: '1px solid rgba(59, 130, 246, 0.2)',
                                color: '#60A5FA',
                                padding: '6px 12px',
                                borderRadius: 6,
                                fontSize: 11,
                                fontWeight: 700,
                                textDecoration: 'none',
                                display: 'inline-block'
                              }}
                            >
                              Upload Quote
                            </Link>
                          </td>
                        </tr>
                      ))
                    ) : (
                      rankedRecommendations.map((vendor) => {
                        const isSelected = currentSelectedVendor?.vendor_id === vendor.vendor_id;
                        const rawPrice = Number(vendor.breakdown.cost.raw);
                        const rawDelivery = Number(vendor.breakdown.delivery.raw);
                        const rawRisk = Number(vendor.breakdown.risk.raw);

                        return (
                          <tr
                            key={vendor.vendor_id}
                            style={{
                              background: isSelected ? 'rgba(59, 130, 246, 0.04)' : 'transparent',
                              borderLeft: isSelected ? '4px solid #3B82F6' : '4px solid transparent',
                              transition: 'all 0.2s'
                            }}
                          >
                            <td style={{ fontWeight: 800, color: vendor.rank === 1 ? '#3B82F6' : '#94A3B8', verticalAlign: 'middle' }}>
                              #{vendor.rank}
                            </td>
                            <td style={{ fontWeight: 700, color: '#FFFFFF', verticalAlign: 'middle' }}>
                              {vendor.vendor_name}
                            </td>
                            <td style={{ verticalAlign: 'middle' }}>
                              {vendor.confidence_score !== undefined ? (
                                <span style={{
                                  color: vendor.confidence_score >= 0.8 ? '#34D399' : vendor.confidence_score >= 0.5 ? '#FBBF24' : '#FCA5A5',
                                  fontWeight: 600
                                }}>
                                  {Math.round(vendor.confidence_score * 100)}%
                                </span>
                              ) : '-'}
                            </td>
                            <td style={{ verticalAlign: 'middle' }}>${rawPrice.toLocaleString()}</td>
                            <td style={{ verticalAlign: 'middle' }}>{rawDelivery} days</td>
                            <td style={{ verticalAlign: 'middle' }}>{rawRisk} (out of 100)</td>
                            <td style={{ verticalAlign: 'middle' }}>{vendor.breakdown.support.raw}</td>
                            <td style={{
                              textAlign: 'right',
                              fontWeight: 800,
                              fontSize: 15,
                              color: getScoreColor(vendor.final_score),
                              verticalAlign: 'middle'
                            }}>
                              {vendor.final_score.toFixed(1)}
                            </td>
                            <td style={{ textAlign: 'right', verticalAlign: 'middle' }}>
                              <button
                                onClick={() => setSelectedVendorId(vendor.vendor_id)}
                                style={{
                                  background: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                                  border: `1px solid ${isSelected ? '#3B82F6' : 'rgba(255, 255, 255, 0.08)'}`,
                                  color: isSelected ? '#60A5FA' : '#94A3B8',
                                  padding: '6px 12px',
                                  borderRadius: 6,
                                  fontSize: 12,
                                  fontWeight: 700,
                                  cursor: 'pointer',
                                  transition: 'all 0.2s'
                                }}
                              >
                                {isSelected ? 'Inspecting' : 'Inspect Details'}
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* EXPLAINABILITY / COMPARATIVE PANEL        */}
        {rankedRecommendations.length > 0 && (
          <div className="card-glass" style={{ marginTop: 24, padding: '24px 28px' }}>
            {/* Header section with winner and confidence badges */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: 16, marginBottom: 20 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: '#FFFFFF', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
                    <path d="M12 16v-4" />
                    <path d="M12 8h.01" />
                  </svg>
                  Decision Explainability Summary
                </h3>
                <p style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>
                  Transparent agentic audit trail mapping intents, trade-offs, and risk profiles.
                </p>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <div style={{ fontSize: 12, background: 'rgba(16, 185, 129, 0.12)', color: '#34D399', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '6px 12px', borderRadius: 8, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34D399' }}></span>
                  Top Winner: {recommendationData?.recommended_vendor || rankedRecommendations[0]?.vendor_name}
                </div>
                {recommendationData?.confidence_score !== undefined && (
                  <div style={{ fontSize: 12, background: 'rgba(59, 130, 246, 0.12)', color: '#60A5FA', border: '1px solid rgba(59, 130, 246, 0.25)', padding: '6px 12px', borderRadius: 8, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
                    Confidence Score: {Math.round(recommendationData.confidence_score * 100)}%
                  </div>
                )}
              </div>
            </div>

            {/* Tab navigation */}
            <div style={{ display: 'flex', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: 1, gap: 4, marginBottom: 20, overflowX: 'auto' }}>
              {(['overview', 'reasoning', 'plan', 'risks'] as const).map((tab) => {
                const isActive = activeExplainabilityTab === tab;
                const labels = {
                  overview: 'Overview',
                  reasoning: 'Agent Reasoning',
                  plan: 'Action Plan',
                  risks: 'Risks & Alternatives'
                };
                const icons = {
                  overview: (
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <line x1="9" y1="9" x2="15" y2="9" />
                      <line x1="9" y1="13" x2="15" y2="13" />
                      <line x1="9" y1="17" x2="13" y2="17" />
                    </svg>
                  ),
                  reasoning: (
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                      <line x1="12" y1="22.08" x2="12" y2="12" />
                    </svg>
                  ),
                  plan: (
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="9 11 12 14 22 4" />
                      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                    </svg>
                  ),
                  risks: (
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                      <line x1="12" y1="9" x2="12" y2="13" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                  )
                };

                return (
                  <button
                    key={tab}
                    onClick={() => setActiveExplainabilityTab(tab)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '10px 16px',
                      background: isActive ? 'rgba(59, 130, 246, 0.08)' : 'transparent',
                      color: isActive ? '#60A5FA' : '#94A3B8',
                      border: 'none',
                      borderBottom: isActive ? '2px solid #3B82F6' : '2px solid transparent',
                      fontSize: 13.5,
                      fontWeight: isActive ? 700 : 500,
                      borderRadius: '6px 6px 0 0',
                      transition: 'all 0.15s ease',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {icons[tab]}
                    {labels[tab]}
                  </button>
                );
              })}
            </div>

            {/* Tab content wrapper */}
            <div style={{ minHeight: 180 }}>
              {activeExplainabilityTab === 'overview' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <h4 style={{ fontSize: 13.5, color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                      Why Selected
                    </h4>
                    {renderFormattedField(recommendationData?.why_selected || rankedRecommendations[0]?.explanation)}
                  </div>
                  {recommendationData?.why_others_not_selected && (
                    <div>
                      <h4 style={{ fontSize: 13.5, color: '#E2E8F0', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                        Why Others Not Selected
                      </h4>
                      {renderFormattedField(recommendationData.why_others_not_selected)}
                    </div>
                  )}
                </div>
              )}

              {activeExplainabilityTab === 'reasoning' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <h4 style={{ fontSize: 13.5, color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                      Cognitive Decision Reasoning
                    </h4>
                    {renderFormattedField(recommendationData?.agent_reasoning, 'Decision calculated deterministically by category weights subtraction.')}
                  </div>
                  {recommendationData?.dynamic_priorities && (
                    <div>
                      <h4 style={{ fontSize: 13.5, color: '#E2E8F0', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                        Priorities & criterion importance
                      </h4>
                      <div style={{ background: 'rgba(255, 255, 255, 0.01)', border: '1px solid rgba(255, 255, 255, 0.04)', padding: 12, borderRadius: 10 }}>
                        <div style={{ fontSize: 13, color: '#E2E8F0', marginBottom: 6 }}>
                          <strong>Dynamic Priorities:</strong> {String(recommendationData.dynamic_priorities)}
                        </div>
                        {recommendationData.criterion_importance && (
                          <div style={{ fontSize: 13, color: '#E2E8F0' }}>
                            <strong>Criterion Importance:</strong> {String(recommendationData.criterion_importance)}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeExplainabilityTab === 'plan' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <h4 style={{ fontSize: 13.5, color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                      Action Plan
                    </h4>
                    {renderFormattedField(recommendationData?.agent_plan, 'No concrete action plan returned.')}
                  </div>
                  {recommendationData?.missing_information && recommendationData.missing_information.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: 13.5, color: '#E2E8F0', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                        Missing Information Impacts
                      </h4>
                      {renderFormattedField(recommendationData.missing_information)}
                    </div>
                  )}
                </div>
              )}

              {activeExplainabilityTab === 'risks' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <h4 style={{ fontSize: 13.5, color: '#EF4444', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                      Identified Vendor Risks
                    </h4>
                    {renderFormattedField(recommendationData?.risks || rankedRecommendations[0]?.explanation, 'No critical vendor risks identified.')}
                  </div>
                  {recommendationData?.alternative_recommendations && (
                    <div>
                      <h4 style={{ fontSize: 13.5, color: '#34D399', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700, marginBottom: 6 }}>
                        Alternative Recommendation & Trade-offs
                      </h4>
                      <div style={{ background: 'rgba(16, 185, 129, 0.02)', border: '1px solid rgba(16, 185, 129, 0.08)', padding: 12, borderRadius: 10 }}>
                        {renderFormattedField(recommendationData.alternative_recommendations)}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom audit information */}
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontSize: 11, color: '#64748B', display: 'flex', alignItems: 'center', gap: 4 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                Audit calculated: {new Date().toLocaleDateString()}
              </div>
              <div style={{ fontSize: 11.5, color: '#60A5FA', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span> Explanation calculated deterministically by category weights.</span>
              </div>
            </div>
          </div>
        )}

        {/* APPLY REASONING DIALOG / MODAL             */}
        {selectedVendorForApply && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            zIndex: 999, padding: 16, backdropFilter: 'blur(4px)'
          }}>
            <div style={{
              background: '#111118',
              border: '1px solid #1F1F2E',
              borderRadius: 16,
              padding: 24,
              maxWidth: 500,
              width: '100%',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)'
            }}>
              <h3 style={{ fontSize: 18, color: '#FFFFFF', margin: '0 0 8px 0' }}>
                Lock in Procurement Choice
              </h3>
              <p style={{ color: '#9CA3AF', fontSize: 13, marginBottom: 16 }}>
                You are setting the status of this procurement to <strong>completed</strong> and selecting <strong>{selectedVendorForApply.vendor_name}</strong>. Provide a brief explanation for audit purposes.
              </p>

              <form onSubmit={onApplyDecision}>
                <label style={{ display: 'block', fontSize: 12, color: '#E2E8F0', fontWeight: 600, marginBottom: 6 }}>
                  Reasoning / Decision Notes
                </label>
                <textarea
                  required
                  placeholder="e.g. Dell Technologies selected due to superior support levels and low risk safety profile which align with our FY26 support mandates."
                  value={applyReasoning}
                  onChange={e => setApplyReasoning(e.target.value)}
                  style={{
                    width: '100%',
                    height: 100,
                    background: '#07070A',
                    color: '#F1F5F9',
                    border: '1px solid #1F1F2E',
                    borderRadius: 8,
                    padding: 10,
                    fontSize: 13,
                    outline: 'none',
                    resize: 'none',
                    marginBottom: 20
                  }}
                />

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                  <button
                    type="button"
                    onClick={() => { setSelectedVendorForApply(null); setApplyReasoning(''); }}
                    style={{
                      background: 'transparent', color: '#9CA3AF', border: '1px solid #1F1F2E',
                      padding: '8px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    style={{
                      background: '#3B82F6', color: '#FFFFFF', border: 'none',
                      padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                      cursor: 'pointer', opacity: actionLoading ? 0.6 : 1
                    }}
                  >
                    {actionLoading ? 'Saving...' : 'Lock Choice'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ORIGINAL VENDOR COMPARISON TABLE (PRESERVED)*/}
        {rankedRecommendations.length > 0 && (
          <>
            <hr style={{ border: 'none', height: '1px', background: '#1F1F2E', margin: '48px 0 32px' }} />

            <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
              Original Vendor Comparison Matrix
            </h2>
            <p style={{ color: '#6B7280', fontSize: 13, marginTop: 4, marginBottom: 16 }}>
              Preserved raw metrics view as queried directly from database records.
            </p>

            <div className="premium-table-container">
              <table className="premium-table">
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th style={{ textAlign: 'center' }}>Price</th>
                    <th style={{ textAlign: 'center' }}>Delivery Days</th>
                    <th style={{ textAlign: 'center' }}>Warranty</th>
                    <th style={{ textAlign: 'center' }}>Support</th>
                    <th style={{ textAlign: 'center' }}>Compliance</th>
                    <th style={{ textAlign: 'center' }}>Risk Details</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.map(v => {
                    const q = quotesMap[v.id] && quotesMap[v.id][0];
                    if (!q) return (
                      <tr key={v.id}>
                        <td style={{ fontWeight: 600 }}>{v.vendor_name}</td>
                        <td colSpan={6} style={{ color: '#94A3B8', fontStyle: 'italic', textAlign: 'center' }}>
                          No quote uploaded yet
                        </td>
                      </tr>
                    );
                    const scoreColor = q.compliance_score >= 80 ? '#10B981' : q.compliance_score >= 60 ? '#F59E0B' : '#EF4444';
                    return (
                      <tr key={v.id}>
                        <td style={{ fontWeight: 600 }}>{v.vendor_name}</td>
                        <td style={{ textAlign: 'center' }}>${q.price.toLocaleString()}</td>
                        <td style={{ textAlign: 'center' }}>{q.delivery_days} days</td>
                        <td style={{ textAlign: 'center' }}>{q.warranty_years} yrs</td>
                        <td style={{ textAlign: 'center', fontSize: 12 }}>{q.support_level}</td>
                        <td style={{ textAlign: 'center', color: scoreColor, fontWeight: 700 }}>{q.compliance_score}</td>
                        <td style={{ textAlign: 'center' }}>
                          <Link to={`/risk/${v.id}`} style={{ color: '#3B82F6', textDecoration: 'none', fontWeight: 600 }}>
                            Open Dashboard
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

      </div>
    </div>
  );
}