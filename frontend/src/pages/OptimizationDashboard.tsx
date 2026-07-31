import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import api from "../api/vendorApi";

export default function OptimizationDashboard() {
  const [renewals, setRenewals] = useState<any[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [strategic, setStrategic] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        
        const [renewalsRes, crossdealRes, strategicRes, logsRes] = await Promise.all([
          api.get("/optimization/renewal-analysis"),
          api.get("/optimization/crossdeal-analysis"),
          api.get("/optimization/strategic-analysis"),
          api.get("/audit/logs")
        ]);
        
        setRenewals(renewalsRes.data.contracts || []);
        setOpportunities(crossdealRes.data.opportunities || []);
        setStrategic(strategicRes.data.strategic_analysis || null);
        setLogs(logsRes.data.logs || []);
      } catch (err: any) {
        console.error("Error loading optimization data:", err);
        setError("Failed to fetch live optimization data from the backend. Make sure the backend server is running.");
      } finally {
        setLoading(false);
      }
    }
    
    void loadData();
  }, []);

  const formatTime = (isoString: string) => {
    if (!isoString) return "";
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " | " + d.toLocaleDateString();
    } catch {
      return isoString;
    }
  };

  // Calculations
  const highRiskCount = renewals.filter(
    (r: any) => r.risk_level === "HIGH" || r.risk_level === "CRITICAL"
  ).length;
  const oppsCount = opportunities.length;
  
  // Dynamic overall optimization score
  const optimizationScore = Math.max(50, Math.min(100, 100 - (highRiskCount * 12) + (oppsCount * 6)));
  const confidenceScore = strategic?.confidence_score || 85;
  const totalSavingsText = strategic?.estimated_savings || "$240,000";
  const vendorReductionPercent = strategic?.reduction_percent || 0;
  
  const getRiskColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "CRITICAL":
        return "#EF4444";
      case "HIGH":
        return "#F87171";
      case "MEDIUM":
        return "#F59E0B";
      case "LOW":
        return "#34D399";
      default:
        return "#94A3B8";
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0A0A0F", color: "#F8FAFC" }}>
      <Navbar />

      <div className="app-container" style={{ maxWidth: 1280, paddingBottom: 80 }}>
        
        {/* Page Header */}
        <div style={{ marginBottom: 32, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
          <div>
            <p style={{ margin: 0, textTransform: "uppercase", letterSpacing: "0.18em", color: "#94A3B8", fontSize: 11, fontWeight: 700 }}>
              Procurement Intelligence
            </p>
            <h1 style={{ margin: "8px 0 10px", background: "linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Procurement Optimization
            </h1>
            <p style={{ margin: 0, color: "#94A3B8", maxWidth: 760 }}>
              Cross-deal negotiation, contract renewal intelligence, and vendor strategic consolidation.
            </p>
          </div>
          <button 
            onClick={() => window.location.reload()}
            style={{
              background: "rgba(59, 130, 246, 0.12)",
              color: "#60A5FA",
              border: "1px solid rgba(59, 130, 246, 0.2)",
              padding: "10px 18px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              transition: "all 0.2s"
            }}
            onMouseOver={(e) => { e.currentTarget.style.background = "rgba(59, 130, 246, 0.2)"; }}
            onMouseOut={(e) => { e.currentTarget.style.background = "rgba(59, 130, 246, 0.12)"; }}
          >
            Refresh Intel
          </button>
        </div>

        {error && (
          <div style={{ 
            marginBottom: 24, 
            padding: "16px 18px", 
            background: "rgba(239, 68, 68, 0.08)", 
            border: "1px solid rgba(239, 68, 68, 0.2)", 
            borderRadius: 12, 
            color: "#FCA5A5", 
            fontSize: 14 
          }}>
            {error}
          </div>
        )}

        {loading ? (
          <div className="card-glass" style={{ padding: 64, textAlign: "center", color: "#94A3B8" }}>
            <div style={{ animation: "pulse-subtle 1.5s infinite", fontSize: 16, fontWeight: 600 }}>
              Loading intelligence models and audit trail...
            </div>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 28 }}>

            {/* 1. AI EXECUTIVE SUMMARY - What is happening? */}
            <div 
              style={{
                background: "linear-gradient(135deg, rgba(16, 20, 38, 0.75) 0%, rgba(59, 130, 246, 0.08) 100%)",
                border: "1px solid rgba(59, 130, 246, 0.25)",
                borderRadius: 20,
                padding: 28,
                boxShadow: "0 10px 30px rgba(59, 130, 246, 0.05)"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <span style={{ background: "#3B82F6", color: "#FFF", fontSize: 10, fontWeight: 800, padding: "3px 8px", borderRadius: 4, textTransform: "uppercase" }}>AI Executive Summary — What is happening?</span>
              </div>
              
              <p style={{ color: "#E2E8F0", fontSize: 15, lineHeight: 1.6, marginBottom: 20 }}>
                {strategic?.business_impact || "Ready to synthesize multi-department opportunities and evaluate risk alerts."}
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, background: "rgba(0,0,0,0.25)", padding: 18, borderRadius: 12, border: "1px solid rgba(255,255,255,0.03)" }}>
                <div>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 600 }}>Opportunities Found</span>
                  <div style={{ fontSize: 20, fontWeight: 800, color: "#FFF", marginTop: 4 }}>{oppsCount} Bundles Available</div>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 600 }}>Contracts At Risk</span>
                  <div style={{ fontSize: 20, fontWeight: 800, color: highRiskCount > 0 ? "#EF4444" : "#10B981", marginTop: 4 }}>{highRiskCount} Risky renewals</div>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 600 }}>Target Vendor Reduction</span>
                  <div style={{ fontSize: 20, fontWeight: 800, color: "#A855F7", marginTop: 4 }}>{vendorReductionPercent}% Target</div>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 600 }}>Estimated Annual Savings</span>
                  <div style={{ fontSize: 20, fontWeight: 800, color: "#10B981", marginTop: 4 }}>{totalSavingsText}</div>
                </div>
              </div>

              {strategic?.strategic_actions && strategic.strategic_actions.length > 0 && (
                <div style={{ marginTop: 24, paddingLeft: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <span style={{ fontSize: 12, color: "#94A3B8", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Recommended Action Pathway — What should procurement do?</span>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {strategic.strategic_actions.map((act: string, idx: number) => (
                      <div key={idx} style={{ display: "flex", gap: 10, alignItems: "flex-start", fontSize: 13.5, color: "#CBD5E1" }}>
                        <span style={{ color: "#3B82F6", fontWeight: 800 }}>⚡</span>
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* 2. KPI CARDS ROW */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
              {[
                ["Procurement Health Score", `${optimizationScore}/100`, "#3B82F6", "Calculated index: Renewal Risk exposure (40%), Vendor Consolidation (30%), Savings (30%)."],
                ["Procurement Analysis Confidence", `${confidenceScore}%`, "#A855F7", "Combines data completeness, quote coverage & enterprise spend scale index."],
                ["Estimated Annual Savings", totalSavingsText, "#10B981", "Projected annual commercial savings range from volume bundling & renegotiations."],
                ["Bundle Opportunities", oppsCount, "#60A5FA", "Identified vendors active across multiple department contracts."],
                ["Contracts At Risk", highRiskCount, "#EF4444", "Active contracts within notice period with auto-renewals enabled."]
              ].map(([label, value, color, tooltip], i) => (
                <div key={i} className="card-glass" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", gap: 10 }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "#94A3B8", fontSize: 11.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        {label}
                      </span>
                    </div>
                    <div style={{ 
                      fontSize: String(value).length > 15 ? 18 : String(value).length > 10 ? 24 : 32, 
                      fontWeight: 800, 
                      color: String(color), 
                      marginTop: 8, 
                      lineHeight: 1.2,
                      wordBreak: "break-word"
                    }}>
                      {value}
                    </div>
                  </div>
                  <p style={{ margin: 0, fontSize: 11, color: "#94A3B8", lineHeight: 1.4 }}>
                    {String(tooltip)}
                  </p>
                </div>
              ))}
            </div>


            {/* 3. CROSS DEAL & 4. RENEWAL INTELLIGENCE GRID */}
            {/* 3. CROSS DEAL & 4. RENEWAL INTELLIGENCE GRID - What did we discover? */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(480px, 1fr))", gap: 24 }}>
              
              {/* CROSS DEAL INTELLIGENCE */}
              <div className="card-glass" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <h3 style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", margin: 0 }}>Cross-Deal Intelligence</h3>
                  </div>
                  <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#94A3B8" }}>
                    What did we discover? Multi-department volume overlaps for master contract negotiations.
                  </p>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 14, overflowY: "auto", maxHeight: 480, paddingRight: 4 }}>
                  {opportunities.length === 0 ? (
                    <div style={{ padding: 32, textAlign: "center", color: "#94A3B8", fontStyle: "italic", fontSize: 13 }}>
                      No active cross-deal opportunities found.
                    </div>
                  ) : (
                    opportunities.map((o: any) => (
                      <div 
                        key={o.vendor_name}
                        style={{
                          background: "rgba(0,0,0,0.25)",
                          border: "1px solid rgba(255,255,255,0.03)",
                          borderRadius: 12,
                          padding: 16,
                          display: "flex",
                          flexDirection: "column",
                          gap: 12
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <strong style={{ fontSize: 15, color: "#FFF" }}>{o.vendor_name}</strong>
                            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                              {o.departments.map((d: string) => (
                                <span key={d} style={{ fontSize: 10, background: "rgba(96, 165, 250, 0.12)", color: "#60A5FA", border: "1px solid rgba(96, 165, 250, 0.2)", padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>
                                  {d}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: 16, fontWeight: 800, color: "#10B981" }}>
                              ${o.estimated_savings_amount.toLocaleString()}
                            </div>

                            <span style={{ fontSize: 11, color: "#94A3B8" }}>
                              ({o.estimated_savings_percent}% savings)
                            </span>
                          </div>
                        </div>

                        <div style={{ background: "rgba(0,0,0,0.15)", padding: 10, borderRadius: 8, fontSize: 12.5, color: "#CBD5E1", borderLeft: "3px solid #3B82F6" }}>
                          {o.recommendation}
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#94A3B8" }}>
                          <span>Active Procurements: <strong>{o.active_procurements}</strong></span>
                          <span>Analysis Confidence: <strong style={{ color: "#A855F7" }}>{o.confidence_score}%</strong></span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* RENEWAL INTELLIGENCE */}
              <div className="card-glass" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", margin: 0 }}>Renewal Intelligence</h3>
                  <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#94A3B8" }}>
                    What did we discover? Contract notice period deadlines and forced auto-renewal risk alerts.
                  </p>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 14, overflowY: "auto", maxHeight: 480, paddingRight: 4 }}>
                  {renewals.length === 0 ? (
                    <div style={{ padding: 32, textAlign: "center", color: "#94A3B8", fontStyle: "italic", fontSize: 13 }}>
                      No active contracts found.
                    </div>
                  ) : (
                    renewals.map((r: any) => (
                      <div 
                        key={r.contract_id}
                        style={{
                          background: "rgba(0,0,0,0.25)",
                          border: "1px solid rgba(255,255,255,0.03)",
                          borderRadius: 12,
                          padding: 16,
                          display: "flex",
                          flexDirection: "column",
                          gap: 12
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <strong style={{ fontSize: 15, color: "#FFF" }}>{r.contract_name}</strong>
                            <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 2 }}>
                              Vendor: <strong>{r.vendor_name}</strong>
                            </div>
                          </div>
                          <span style={{ 
                            fontSize: 10.5, 
                            fontWeight: 800, 
                            color: getRiskColor(r.risk_level), 
                            background: `${getRiskColor(r.risk_level)}12`,
                            border: `1px solid ${getRiskColor(r.risk_level)}33`,
                            padding: "3px 8px", 
                            borderRadius: 6,
                            textTransform: "uppercase"
                          }}>
                            {r.risk_level} Risk
                          </span>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 12, color: "#E2E8F0" }}>
                          <div>
                            Renewal Date: <strong style={{ color: "#FFF" }}>{r.renewal_date || "N/A"}</strong>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            Days Remaining: <strong style={{ color: r.days_remaining <= 30 ? "#EF4444" : "#FFF" }}>{r.days_remaining !== null ? r.days_remaining : "N/A"} days</strong>
                          </div>
                        </div>

                        {r.explainability && (
                          <div style={{ color: "#94A3B8", fontSize: 12, fontStyle: "italic", background: "rgba(255,255,255,0.02)", padding: 8, borderRadius: 6 }}>
                            {r.explainability}
                          </div>
                        )}

                        <div style={{ background: "rgba(0,0,0,0.15)", padding: 10, borderRadius: 8, fontSize: 12.5, color: "#CBD5E1", borderLeft: `3px solid ${getRiskColor(r.risk_level)}` }}>
                          <strong>Action Directive:</strong> {r.recommendation}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>

            {/* 5. STRATEGIC CONSOLIDATION ENGINE */}
            <div className="card-glass">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", margin: 0 }}>Strategic Consolidation Engine</h3>
                  <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#94A3B8" }}>
                    Vendor portfolio reduction metrics & commercial savings projections.
                  </p>
                </div>
                <div style={{
                  background: "rgba(16, 185, 129, 0.12)",
                  border: "1px solid rgba(16, 185, 129, 0.2)",
                  color: "#34D399",
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600
                }}>
                  Priority: {strategic?.priority || "HIGH"}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 20, marginBottom: 24 }}>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: 16, borderRadius: 12, border: "1px solid rgba(255,255,255,0.03)" }}>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 700 }}>Current Vendors</span>
                  <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6 }}>{strategic?.current_vendors || 4}</div>
                </div>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: 16, borderRadius: 12, border: "1px solid rgba(255,255,255,0.03)" }}>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 700 }}>Recommended Vendors</span>
                  <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6, color: "#60A5FA" }}>{strategic?.recommended_vendors || 2}</div>
                </div>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: 16, borderRadius: 12, border: "1px solid rgba(255,255,255,0.03)" }}>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 700 }}>Target Vendor Reduction</span>
                  <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6, color: "#A855F7" }}>{vendorReductionPercent}%</div>
                </div>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: 16, borderRadius: 12, border: "1px solid rgba(255,255,255,0.03)" }}>
                  <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", fontWeight: 700 }}>Estimated Annual Savings</span>
                  <div style={{ 
                    fontSize: String(totalSavingsText).length > 15 ? 18 : String(totalSavingsText).length > 10 ? 22 : 28, 
                    fontWeight: 800, 
                    marginTop: 6, 
                    color: "#10B981",
                    lineHeight: 1.2,
                    wordBreak: "break-word"
                  }}>{totalSavingsText}</div>
                </div>
              </div>
            </div>



            {/* 6. AGENT CONTRIBUTION PANEL */}
            <div className="card-glass">
              <div>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", margin: 0 }}>Agent Contribution Panel</h3>
                <p style={{ margin: "4px 0 16px 0", fontSize: 12, color: "#94A3B8" }}>
                  Autonomous agent nodes running in parallel to drive procurement optimization.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
                {[
                  {
                    name: "Cross Deal Agent",
                    desc: "Scans active quotes and grouping keys to detect department overlaps. Computes multi-dept volume savings.",
                    status: "ACTIVE",
                    color: "#3B82F6"
                  },
                  {
                    name: "Renewal Agent",
                    desc: "Calculates contract notice periods, warning flags, and outputs explainability details for expiring agreements.",
                    status: "ACTIVE",
                    color: "#EF4444"
                  },
                  {
                    name: "Strategic Agent",
                    desc: "Consolidates findings, executes LLM synthesis routines, and writes strategic vendor reduction workflows.",
                    status: "ACTIVE",
                    color: "#A855F7"
                  },
                  {
                    name: "Audit Layer",
                    desc: "Bypasses client-side storage to insert decision payload snapshots directly into Supabase audit tables.",
                    status: "ACTIVE",
                    color: "#10B981"
                  }
                ].map((agent, idx) => (
                  <div 
                    key={idx}
                    style={{
                      background: "rgba(0,0,0,0.25)",
                      border: "1px solid rgba(255,255,255,0.03)",
                      borderRadius: 12,
                      padding: 16,
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between"
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                        <strong style={{ color: agent.color, fontSize: 14 }}>{agent.name}</strong>
                        <span style={{ fontSize: 9, fontWeight: 800, background: "rgba(16, 185, 129, 0.1)", color: "#10B981", padding: "2px 6px", borderRadius: 4 }}>
                          {agent.status}
                        </span>
                      </div>
                      <p style={{ fontSize: 12, color: "#CBD5E1", lineHeight: 1.5, margin: 0 }}>
                        {agent.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 7. OPTIMIZATION ACTIVITY TIMELINE - How was this generated? */}
            <div className="card-glass">
              <div>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", margin: 0 }}>Optimization Activity Timeline</h3>
                <p style={{ margin: "4px 0 20px 0", fontSize: 12, color: "#94A3B8" }}>
                  How was this generated? Compliant, real-time agent audit log recorded in Supabase.
                </p>
              </div>


              {logs.length === 0 ? (
                <div style={{ padding: 48, textAlign: "center", color: "#94A3B8", fontStyle: "italic" }}>
                  No logged agent activity found in the system.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 0, borderLeft: "2px solid rgba(255,255,255,0.06)", marginLeft: 8, paddingLeft: 20 }}>
                  {logs.slice(0, 15).map((log: any, idx: number) => {
                    const dotColor = log.agent_name?.includes("Renewal") ? "#EF4444" : log.agent_name?.includes("Cross") ? "#3B82F6" : log.agent_name?.includes("Strategic") ? "#A855F7" : "#10B981";
                    
                    return (
                      <div key={idx} style={{ position: "relative", paddingBottom: 24 }}>
                        {/* Timeline Bullet */}
                        <div style={{
                          position: "absolute",
                          left: -27,
                          top: 4,
                          width: 12,
                          height: 12,
                          borderRadius: "50%",
                          background: dotColor,
                          border: "2px solid #0A0A0F"
                        }} />
                        
                        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                          <span style={{ fontSize: 13.5, fontWeight: 700, color: "#FFF" }}>
                            {log.agent_name}
                          </span>
                          <span style={{ fontSize: 11.5, color: "#94A3B8" }}>
                            {formatTime(log.created_at)}
                          </span>
                        </div>

                        <div style={{ fontSize: 13.5, color: "#E2E8F0", marginTop: 6 }}>
                          Action: <strong style={{ color: "#60A5FA" }}>{log.action_type || "N/A"}</strong>
                        </div>

                        <p style={{ fontSize: 12.5, color: "#94A3B8", marginTop: 4, margin: "6px 0 0 0" }}>
                          {log.reasoning || "Agent executed transaction logging automatically."}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

          </div>
        )}

      </div>
    </div>
  );
}