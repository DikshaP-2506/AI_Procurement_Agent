import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import {
  generateNegotiationEmail,
  getStrategyRecommendation,
  useNegotiationStrategy,
} from '../api/negotiationApi';
import { useProcurement } from '../context/ProcurementContext';
import type {
  NegotiationEmail,
  NegotiationHistoryRecord,
  NegotiationStrategy,
} from '../types/negotiation';

export default function NegotiationIntelligence() {
  const { selectedProcurementId } = useProcurement();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    text: string;
    isError: boolean;
  } | null>(null);

  const [historical, setHistorical] = useState<
    NegotiationHistoryRecord[]
  >([]);
  const [strategy, setStrategy] =
    useState<NegotiationStrategy | null>(null);
  const [email, setEmail] =
    useState<NegotiationEmail | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!selectedProcurementId) {
      setError(
        'Select a procurement project before generating negotiation intelligence.'
      );
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);
    setHistorical([]);
    setStrategy(null);
    setEmail(null);

    try {
      /*
       * The backend now runs an autonomous tool-using agent.
       * The frontend still makes the same API calls, so no new frontend
       * API file is required.
       */
      const strategyResponse =
        await getStrategyRecommendation({
          procurement_id: selectedProcurementId,
        });

      setHistorical(strategyResponse.historical || []);
      setStrategy(strategyResponse.strategy);

      const emailResponse =
        await generateNegotiationEmail({
          procurement_id: selectedProcurementId,
          recommended_strategy:
            strategyResponse.strategy.recommended_strategy,
          expected_discount_range:
            strategyResponse.strategy.expected_discount_range,
        });

      setEmail(emailResponse.email);
    } catch (err) {
      setError(
        'Unable to generate negotiation intelligence. Verify backend availability and try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function onCopyEmail() {
    if (!email) return;

    try {
      await navigator.clipboard.writeText(
        `Subject: ${email.subject}\n\n${email.body}`
      );

      setMessage({
        text: 'Negotiation email copied to clipboard.',
        isError: false,
      });

      setTimeout(() => setMessage(null), 3000);
    } catch {
      setMessage({
        text: 'Unable to copy email. Clipboard permissions may be blocked.',
        isError: true,
      });
    }
  }

  async function onUseStrategy() {
    if (!strategy || !email || !selectedProcurementId) return;

    try {
      const result = await useNegotiationStrategy({
        procurement_id: selectedProcurementId,
        recommended_strategy: strategy.recommended_strategy,
        expected_discount_range: strategy.expected_discount_range,
        generated_email: email,
      });

      setMessage({
        text:
          result?.outcome_recorded === false
            ? 'Strategy approved and saved. Actual negotiation outcome is still pending.'
            : 'Negotiation strategy saved successfully.',
        isError: false,
      });

      setTimeout(() => setMessage(null), 4000);
    } catch {
      setMessage({
        text: 'Unable to save the approved negotiation strategy.',
        isError: true,
      });
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0A0A0F' }}>
      <Navbar />

      <div
        className="app-container"
        style={{ maxWidth: 1200, paddingBottom: 80 }}
      >
        <div style={{ marginBottom: 24 }}>
          <p
            style={{
              margin: 0,
              textTransform: 'uppercase',
              letterSpacing: '0.18em',
              color: '#94A3B8',
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            Autonomous Negotiation Intelligence
          </p>

          <h1
            style={{
              margin: '8px 0 10px',
              background:
                'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Negotiation Intelligence
          </h1>

          <p
            style={{
              margin: 0,
              color: '#94A3B8',
              maxWidth: 820,
              lineHeight: 1.7,
            }}
          >
            The negotiation agent autonomously decides which procurement,
            historical, contract, risk, and benchmarking information it needs
            before recommending a strategy.
          </p>
        </div>

        <div className="card-glass" style={{ marginBottom: 24 }}>
          <h3
            style={{
              margin: 0,
              fontSize: 16,
              fontWeight: 700,
              color: '#FFFFFF',
            }}
          >
            Agentic Investigation
          </h3>

          <div
            style={{
              marginTop: 14,
              display: 'grid',
              gridTemplateColumns:
                'repeat(auto-fit, minmax(170px, 1fr))',
              gap: 10,
            }}
          >
            {[
              ['1', 'Observe procurement'],
              ['2', 'Select useful tools'],
              ['3', 'Investigate evidence'],
              ['4', 'Evaluate strategy'],
              ['5', 'Human approval'],
            ].map(([number, label]) => (
              <div
                key={number}
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.05)',
                  borderRadius: 10,
                  padding: 12,
                }}
              >
                <div
                  style={{
                    color: '#60A5FA',
                    fontSize: 11,
                    fontWeight: 800,
                  }}
                >
                  STEP {number}
                </div>
                <div
                  style={{
                    marginTop: 6,
                    color: '#E2E8F0',
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  {label}
                </div>
              </div>
            ))}
          </div>

          <form onSubmit={onSubmit} style={{ marginTop: 18 }}>
            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                background:
                  'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                color: '#fff',
                padding: '12px',
                borderRadius: 10,
                border: 'none',
                fontSize: 14,
                fontWeight: 700,
                boxShadow:
                  '0 4px 14px rgba(59, 130, 246, 0.4)',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading
                ? 'Agent Investigating...'
                : 'Run Autonomous Negotiation Agent'}
            </button>
          </form>

          {error && (
            <div
              style={{
                marginTop: 14,
                padding: '10px 12px',
                background: 'rgba(239, 68, 68, 0.08)',
                border:
                  '1px solid rgba(239, 68, 68, 0.2)',
                borderRadius: 8,
                color: '#FCA5A5',
                fontSize: 13,
              }}
            >
              {error}
            </div>
          )}

          {message && (
            <div
              style={{
                marginTop: 14,
                padding: '10px 12px',
                background: message.isError
                  ? 'rgba(239, 68, 68, 0.08)'
                  : 'rgba(16, 185, 129, 0.08)',
                border: `1px solid ${
                  message.isError
                    ? 'rgba(239, 68, 68, 0.2)'
                    : 'rgba(16, 185, 129, 0.2)'
                }`,
                borderRadius: 8,
                color: message.isError
                  ? '#FCA5A5'
                  : '#D1FAE5',
                fontSize: 13,
              }}
            >
              {message.text}
            </div>
          )}
        </div>

        <div className="card-glass" style={{ marginBottom: 24 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
              flexWrap: 'wrap',
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: 16,
                fontWeight: 700,
                color: '#FFFFFF',
              }}
            >
              Historical Evidence Selected by Agent
            </h3>

            <span
              style={{
                color: '#94A3B8',
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {historical.length} record(s)
            </span>
          </div>

          {historical.length === 0 ? (
            <div
              style={{
                marginTop: 14,
                color: '#94A3B8',
                fontSize: 13,
              }}
            >
              The agent has not retrieved historical evidence yet.
            </div>
          ) : (
            <div
              className="premium-table-container"
              style={{ marginTop: 14 }}
            >
              <table className="premium-table">
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th>Category</th>
                    <th>Strategy</th>
                    <th>Outcome</th>
                    <th>Discount</th>
                    <th>Success Score</th>
                  </tr>
                </thead>

                <tbody>
                  {historical.map((row) => (
                    <tr key={row.id}>
                      <td>{row.vendor_name || '-'}</td>
                      <td>{row.product_category || '-'}</td>
                      <td>{row.strategy_used || '-'}</td>
                      <td>{row.outcome || '-'}</td>
                      <td>
                        {typeof row.discount_received === 'number'
                          ? `${row.discount_received}%`
                          : '-'}
                      </td>
                      <td>
                        {typeof row.success_score === 'number'
                          ? row.success_score
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card-glass" style={{ marginBottom: 24 }}>
          <h3
            style={{
              margin: 0,
              fontSize: 16,
              fontWeight: 700,
              color: '#FFFFFF',
            }}
          >
            Recommended Strategy
          </h3>

          {!strategy ? (
            <div
              style={{
                marginTop: 14,
                color: '#94A3B8',
                fontSize: 13,
              }}
            >
              The autonomous agent will investigate the procurement before
              producing a recommendation.
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  'repeat(auto-fit, minmax(240px, 1fr))',
                gap: 14,
                marginTop: 14,
              }}
            >
              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Recommended Strategy
                </div>

                <div
                  style={{
                    marginTop: 8,
                    color: '#F8FAFC',
                    fontSize: 14,
                    fontWeight: 600,
                    lineHeight: 1.6,
                  }}
                >
                  {strategy.recommended_strategy}
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Evidence-Based Discount
                </div>

                <div
                  style={{
                    marginTop: 8,
                    color: '#34D399',
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  {strategy.expected_discount_range}
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Confidence
                </div>

                <div
                  style={{
                    marginTop: 8,
                    color: '#60A5FA',
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  {strategy.confidence_score}%
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                  gridColumn: '1 / -1',
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Agent Reasoning & Evidence
                </div>

                <div
                  style={{
                    marginTop: 8,
                    color: '#CBD5E1',
                    fontSize: 13.5,
                    lineHeight: 1.7,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {strategy.reasoning}
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                  gridColumn: '1 / -1',
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Risks
                </div>

                <ul
                  style={{
                    margin: '8px 0 0',
                    paddingLeft: 18,
                    color: '#CBD5E1',
                    fontSize: 13.5,
                    lineHeight: 1.7,
                  }}
                >
                  {(strategy.risks || []).map(
                    (risk, index) => (
                      <li key={`${risk}-${index}`}>
                        {risk}
                      </li>
                    )
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>

        <div className="card-glass">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
              flexWrap: 'wrap',
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: 16,
                fontWeight: 700,
                color: '#FFFFFF',
              }}
            >
              Negotiation Email
            </h3>

            <div
              style={{
                display: 'flex',
                gap: 8,
                flexWrap: 'wrap',
              }}
            >
              <button
                onClick={onUseStrategy}
                disabled={!email || !strategy}
                style={{
                  background: 'rgba(16, 185, 129, 0.12)',
                  color: '#34D399',
                  border:
                    '1px solid rgba(16, 185, 129, 0.2)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  fontSize: 12,
                  fontWeight: 700,
                  opacity: email && strategy ? 1 : 0.6,
                }}
              >
                Approve Strategy
              </button>

              <button
                onClick={onCopyEmail}
                disabled={!email}
                style={{
                  background: 'rgba(59, 130, 246, 0.12)',
                  color: '#60A5FA',
                  border:
                    '1px solid rgba(59, 130, 246, 0.2)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  fontSize: 12,
                  fontWeight: 700,
                  opacity: email ? 1 : 0.6,
                }}
              >
                Copy Email
              </button>
            </div>
          </div>

          {!email ? (
            <div
              style={{
                marginTop: 14,
                color: '#94A3B8',
                fontSize: 13,
              }}
            >
              The communication agent will generate the email after the
              strategy is produced.
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gap: 12,
                marginTop: 14,
              }}
            >
              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Email Subject
                </div>

                <div
                  style={{
                    marginTop: 8,
                    color: '#F8FAFC',
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {email.subject}
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border:
                    '1px solid rgba(255,255,255,0.04)',
                  borderRadius: 12,
                  padding: 14,
                }}
              >
                <div
                  style={{
                    color: '#94A3B8',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                  }}
                >
                  Email Body
                </div>

                <div
                  style={{
                    marginTop: 8,
                    color: '#CBD5E1',
                    fontSize: 13.5,
                    lineHeight: 1.7,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {email.body}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
