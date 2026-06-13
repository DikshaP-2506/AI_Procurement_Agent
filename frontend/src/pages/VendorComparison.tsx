import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Vendor, VendorQuote } from '../types/vendor';
import { getVendors, getVendorQuotes } from '../api/vendorApi';
import { getRecommendations, applyRecommendation, Weights, VendorRecommendation } from '../api/recommendationApi';
import Navbar from '../components/Navbar';

const PROCUREMENT_ID = '8ea2d01d-2137-4e83-8875-eb6a28d6e0c6';

export default function VendorComparison() {
  // Existing state to preserve original table functionality
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [quotesMap, setQuotesMap] = useState<Record<string, VendorQuote[]>>({});

  // Simulator-specific state
  const [weights, setWeights] = useState<Weights>({ cost: 25, risk: 25, support: 25, delivery: 25 });
  const [qualitativeAdjustments, setQualitativeAdjustments] = useState<Record<string, number>>({});
  const [rankedRecommendations, setRankedRecommendations] = useState<VendorRecommendation[]>([]);
  const [comparisonSummary, setComparisonSummary] = useState<string>('');
  const [apiWarning, setApiWarning] = useState<string | null>(null);
  
  // Loading & Action states
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);
  
  // Apply reasoning modal state
  const [selectedVendorForApply, setSelectedVendorForApply] = useState<VendorRecommendation | null>(null);
  const [applyReasoning, setApplyReasoning] = useState<string>('');

  useEffect(() => {
    loadBaseData();
  }, []);

  // Fetch recommendations whenever weights or qualitative adjustments change
  useEffect(() => {
    fetchSimulatedRankings();
  }, [weights, qualitativeAdjustments]);

  async function loadBaseData() {
    try {
      setLoading(true);
      const vs = await getVendors(PROCUREMENT_ID);
      
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
    try {
      const res = await getRecommendations(PROCUREMENT_ID, weights, qualitativeAdjustments);
      setRankedRecommendations(res.recommendations);
      setComparisonSummary(res.comparison_summary);
      setApiWarning(res.warning || null);
    } catch (e) {
      console.error("Failed to fetch simulated rankings", e);
    }
  }

  // Preset Handlers
  const applyPreset = (presetName: string) => {
    if (presetName === 'cost') {
      setWeights({ cost: 70, risk: 10, support: 10, delivery: 10 });
    } else if (presetName === 'risk') {
      setWeights({ cost: 10, risk: 70, support: 10, delivery: 10 });
    } else if (presetName === 'support') {
      setWeights({ cost: 10, risk: 10, support: 70, delivery: 10 });
    } else if (presetName === 'delivery') {
      setWeights({ cost: 10, risk: 10, support: 10, delivery: 70 });
    } else {
      setWeights({ cost: 25, risk: 25, support: 25, delivery: 25 });
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
        PROCUREMENT_ID,
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24, marginTop: 24, alignItems: 'start' }}>
          
          {/* LEFT COLUMN: CRITERIA WEIGHT SLIDERS */}
          <div style={{ 
            background: 'rgba(16, 20, 38, 0.6)', 
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.08)', 
            borderRadius: 16, 
            padding: 24,
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
            position: 'sticky',
            top: 96,
            zIndex: 10
          }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: 8 }}>
              Trade-Off Weights
            </h2>
            <p style={{ color: '#94A3B8', fontSize: 13, marginBottom: 20 }}>
              Adjust sliders to balance procurement priorities. Sum: {weights.cost + weights.risk + weights.support + weights.delivery}%
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
                    background: weights.cost === 70 ? 'rgba(59, 130, 246, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                    border: `1px solid ${weights.cost === 70 ? '#3B82F6' : 'rgba(255, 255, 255, 0.08)'}`,
                    color: weights.cost === 70 ? '#60A5FA' : '#94A3B8',
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
                    background: weights.risk === 70 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                    border: `1px solid ${weights.risk === 70 ? '#10B981' : 'rgba(255, 255, 255, 0.08)'}`,
                    color: weights.risk === 70 ? '#34D399' : '#94A3B8',
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
                    background: weights.delivery === 70 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                    border: `1px solid ${weights.delivery === 70 ? '#F59E0B' : 'rgba(255, 255, 255, 0.08)'}`,
                    color: weights.delivery === 70 ? '#FBBF24' : '#94A3B8',
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
                  onClick={() => applyPreset('balanced')}
                  style={{
                    background: (weights.cost === 25 && weights.risk === 25) ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                    border: `1px solid ${(weights.cost === 25 && weights.risk === 25) ? '#8B5CF6' : 'rgba(255, 255, 255, 0.08)'}`,
                    color: (weights.cost === 25 && weights.risk === 25) ? '#A78BFA' : '#94A3B8',
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

            </div>

            {apiWarning && (
              <div style={{ marginTop: 20, padding: 12, borderRadius: 8, background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', color: '#FBBF24', fontSize: 12 }}>
                Warning: {apiWarning}
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: DYNAMIC RANKINGS */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            
            {loading ? (
              <div style={{ padding: 48, textAlign: 'center', color: '#6B7280' }}>Loading simulation data...</div>
            ) : rankedRecommendations.length === 0 ? (
              <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 16, padding: 48, textAlign: 'center', color: '#6B7280' }}>
                No active quotes found to run the simulator. Upload quotes in the 'Upload Quote' tab first.
              </div>
            ) : (
              rankedRecommendations.map((vendor) => {
                const cardBorder = vendor.rank === 1 ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)';
                const rankBadgeColor = vendor.rank === 1 ? '#3B82F6' : vendor.rank === 2 ? '#6B7280' : '#4B5563';
                const rawPrice = Number(vendor.breakdown.cost.raw);
                const rawDelivery = Number(vendor.breakdown.delivery.raw);
                const rawRisk = Number(vendor.breakdown.risk.raw);
                const rawSupport = String(vendor.breakdown.support.raw);

                return (
                  <div 
                    key={vendor.vendor_id}
                    style={{
                      background: 'rgba(16, 20, 38, 0.6)',
                      backdropFilter: 'blur(20px)',
                      WebkitBackdropFilter: 'blur(20px)',
                      border: cardBorder,
                      borderRadius: 16,
                      padding: 24,
                      boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
                      transition: 'all 0.3s ease',
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
                      RANK #{vendor.rank}
                    </div>

                    {/* Vendor title and final score */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, marginBottom: 18 }}>
                      <div style={{ marginLeft: 4 }}>
                        <h3 style={{ fontSize: 20, fontWeight: 800, color: '#FFFFFF', margin: 0 }}>{vendor.vendor_name}</h3>
                        <span style={{ fontSize: 12, color: '#94A3B8' }}>ID: {vendor.vendor_id.slice(0, 8)}...</span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 800, color: getScoreColor(vendor.final_score), lineHeight: 1 }}>
                          {vendor.final_score.toFixed(1)}
                        </div>
                        <span style={{ fontSize: 10, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Total Score</span>
                      </div>
                    </div>

                    {/* Normalization Progress Bars (Uniform layout in single stack) */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13 }}>
                      
                      {/* Price bar */}
                      <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                          <span>Cost: <strong style={{ color: '#FFFFFF' }}>${rawPrice.toLocaleString()}</strong></span>
                          <span style={{ color: '#60A5FA', fontWeight: 600 }}>Score: {vendor.breakdown.cost.score}</span>
                        </div>
                        <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${vendor.breakdown.cost.score}%`, background: 'linear-gradient(90deg, #3B82F6 0%, #60A5FA 100%)', borderRadius: 99 }} />
                        </div>
                      </div>

                      {/* Risk bar */}
                      <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                          <span>Risk Profile: <strong style={{ color: '#FFFFFF' }}>{rawRisk} (out of 100)</strong></span>
                          <span style={{ color: '#34D399', fontWeight: 600 }}>Safety: {vendor.breakdown.risk.score}</span>
                        </div>
                        <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${vendor.breakdown.risk.score}%`, background: 'linear-gradient(90deg, #10B981 0%, #34D399 100%)', borderRadius: 99 }} />
                        </div>
                      </div>

                      {/* Delivery bar */}
                      <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                          <span>Delivery Speed: <strong style={{ color: '#FFFFFF' }}>{rawDelivery} days</strong></span>
                          <span style={{ color: '#FBBF24', fontWeight: 600 }}>Score: {vendor.breakdown.delivery.score}</span>
                        </div>
                        <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${vendor.breakdown.delivery.score}%`, background: 'linear-gradient(90deg, #F59E0B 0%, #FBBF24 100%)', borderRadius: 99 }} />
                        </div>
                      </div>

                      {/* Support bar */}
                      <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.03)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#E2E8F0', marginBottom: 6, gap: 12 }}>
                          <span>Support Level: <strong style={{ color: '#FFFFFF' }}>{rawSupport}</strong></span>
                          <span style={{ color: '#A78BFA', fontWeight: 600 }}>Score: {vendor.breakdown.support.score}</span>
                        </div>
                        <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${vendor.breakdown.support.score}%`, background: 'linear-gradient(90deg, #8B5CF6 0%, #A78BFA 100%)', borderRadius: 99 }} />
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
                          value={qualitativeAdjustments[vendor.vendor_id] || 0}
                          onChange={e => handleAdjustmentChange(vendor.vendor_id, Number(e.target.value))}
                          style={{ width: 120, accentColor: '#8B5CF6', height: 4 }}
                        />
                        <span style={{ 
                          fontSize: 13, 
                          fontWeight: 700, 
                          color: (qualitativeAdjustments[vendor.vendor_id] || 0) > 0 ? '#34D399' : (qualitativeAdjustments[vendor.vendor_id] || 0) < 0 ? '#EF4444' : '#94A3B8',
                          minWidth: 32,
                          textAlign: 'right'
                        }}>
                          {(qualitativeAdjustments[vendor.vendor_id] || 0) > 0 ? '+' : ''}{qualitativeAdjustments[vendor.vendor_id] || 0}
                        </span>
                      </div>
                    </div>

                    {/* Action Panel */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                      <span style={{ fontSize: 11, color: '#94A3B8', fontStyle: 'italic' }}>
                        W. Contribution: Cost {vendor.breakdown.cost.weighted} | Risk {vendor.breakdown.risk.weighted} | Support {vendor.breakdown.support.weighted} | Deliv {vendor.breakdown.delivery.weighted}
                      </span>
                      <button 
                        onClick={() => setSelectedVendorForApply(vendor)}
                        style={{
                          background: vendor.rank === 1 ? '#3B82F6' : 'transparent',
                          color: vendor.rank === 1 ? '#FFFFFF' : '#3B82F6',
                          border: '1px solid #3B82F6',
                          padding: '8px 16px',
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          boxShadow: vendor.rank === 1 ? '0 4px 12px rgba(59, 130, 246, 0.3)' : 'none'
                        }}
                      >
                        Apply Decision
                      </button>
                    </div>

                  </div>
                );
              })
            )}

          </div>

        </div>

        {/* ========================================== */}
        {/* EXPLAINABILITY / COMPARATIVE PANEL        */}
        {/* ========================================== */}
        {rankedRecommendations.length > 0 && (
          <div className="card-glass" style={{ marginTop: 24 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#FFFFFF', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: 6 }}>
              Decision Explainability Summary
            </h3>
            <p style={{ color: '#E2E8F0', fontSize: 14, lineHeight: 1.6, margin: 0, fontStyle: 'italic' }}>
              "{comparisonSummary}"
            </p>
            <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{ fontSize: 11, background: 'rgba(59, 130, 246, 0.12)', color: '#60A5FA', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '4px 8px', borderRadius: 4, fontWeight: 600 }}>
                Explanation calculated deterministically by category weights subtraction.
              </div>
              <div style={{ fontSize: 11, background: 'rgba(16, 185, 129, 0.12)', color: '#34D399', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '4px 8px', borderRadius: 4, fontWeight: 600 }}>
                Top Winner: {rankedRecommendations[0]?.vendor_name}
              </div>
            </div>
          </div>
        )}

        {/* ========================================== */}
        {/* APPLY REASONING DIALOG / MODAL             */}
        {/* ========================================== */}
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

        {/* ========================================== */}
        {/* ORIGINAL VENDOR COMPARISON TABLE (PRESERVED)*/}
        {/* ========================================== */}
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
              {vendors.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: 24, textAlign: 'center', color: '#94A3B8' }}>
                    No vendors configured for comparison.
                  </td>
                </tr>
              ) : (
                vendors.map(v => {
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
                })
              )}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}
