import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import { generateNegotiationEmail, getStrategyRecommendation } from '../api/negotiationApi';
import type {
  NegotiationEmail,
  NegotiationHistoryRecord,
  NegotiationStrategy,
} from '../types/negotiation';

export default function NegotiationIntelligence() {
  const [vendorName, setVendorName] = useState('');
  const [productCategory, setProductCategory] = useState('');
  const [quoteValue, setQuoteValue] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  const [historical, setHistorical] = useState<NegotiationHistoryRecord[]>([]);
  const [strategy, setStrategy] = useState<NegotiationStrategy | null>(null);
  const [email, setEmail] = useState<NegotiationEmail | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();

    const parsedQuote = Number(quoteValue);
    if (!vendorName.trim() || !productCategory.trim() || !Number.isFinite(parsedQuote) || parsedQuote <= 0) {
      setError('Enter vendor name, product category, and a valid quote value greater than 0.');
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);
    setHistorical([]);
    setStrategy(null);
    setEmail(null);

    try {
      const strategyResponse = await getStrategyRecommendation({
        vendor_name: vendorName.trim(),
        product_category: productCategory.trim(),
        quote_value: parsedQuote,
      });

      setHistorical(strategyResponse.historical || []);
      setStrategy(strategyResponse.strategy);

      const emailResponse = await generateNegotiationEmail({
        vendor_name: vendorName.trim(),
        recommended_strategy: strategyResponse.strategy.recommended_strategy,
        expected_discount_range: strategyResponse.strategy.expected_discount_range,
      });

      setEmail(emailResponse.email);
    } catch (err) {
      setError('Unable to generate negotiation intelligence. Verify backend availability and try again.');
    } finally {
      setLoading(false);
    }
  }

  async function onCopyEmail() {
    if (!email) return;

    try {
      await navigator.clipboard.writeText(`Subject: ${email.subject}\n\n${email.body}`);
      setMessage({ text: 'Negotiation email copied to clipboard.', isError: false });
      setTimeout(() => setMessage(null), 3000);
    } catch {
      setMessage({ text: 'Unable to copy email. Clipboard permissions may be blocked.', isError: true });
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0A0A0F' }}>
      <Navbar />
      <div className="app-container" style={{ maxWidth: 1200, paddingBottom: 80 }}>

        {/* Page Header */}
        <div style={{ marginBottom: 24 }}>
          <p style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94A3B8', fontSize: 11, fontWeight: 700 }}>
            Negotiation Intelligence
          </p>
          <h1 style={{ margin: '8px 0 10px', background: 'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Negotiation Intelligence
          </h1>
          <p style={{ margin: 0, color: '#94A3B8', maxWidth: 760 }}>
            Generate strategy recommendations from similar negotiations and prepare a vendor outreach email.
          </p>
        </div>

        {/* Input Form */}
        <div className="card-glass" style={{ marginBottom: 24 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Negotiation Input Form</h3>
          <form onSubmit={onSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14, marginTop: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#94A3B8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Vendor Name
              </label>
              <input
                value={vendorName}
                onChange={(e) => setVendorName(e.target.value)}
                placeholder="e.g. Dell"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#94A3B8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Product Category
              </label>
              <input
                value={productCategory}
                onChange={(e) => setProductCategory(e.target.value)}
                placeholder="e.g. Laptops"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#94A3B8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Quote Value
              </label>
              <input
                value={quoteValue}
                onChange={(e) => setQuoteValue(e.target.value)}
                placeholder="e.g. 120000"
                type="number"
                min="0"
                step="0.01"
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'end' }}>
              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                  color: '#fff',
                  padding: '12px',
                  borderRadius: 10,
                  border: 'none',
                  fontSize: 14,
                  fontWeight: 700,
                  boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
                  opacity: loading ? 0.7 : 1,
                }}
              >
                {loading ? 'Generating...' : 'Generate Negotiation Strategy'}
              </button>
            </div>
          </form>

          {error && (
            <div style={{ marginTop: 14, padding: '10px 12px', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 8, color: '#FCA5A5', fontSize: 13 }}>
              {error}
            </div>
          )}

          {message && (
            <div style={{ marginTop: 14, padding: '10px 12px', background: message.isError ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)', border: `1px solid ${message.isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`, borderRadius: 8, color: message.isError ? '#FCA5A5' : '#D1FAE5', fontSize: 13 }}>
              {message.text}
            </div>
          )}
        </div>

        {/* Historical Negotiations */}
        <div className="card-glass" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Historical Negotiations</h3>
            <span style={{ color: '#94A3B8', fontSize: 12, fontWeight: 600 }}>
              {historical.length} record(s)
            </span>
          </div>

          {historical.length === 0 ? (
            <div style={{ marginTop: 14, color: '#94A3B8', fontSize: 13 }}>
              No historical negotiations to display yet.
            </div>
          ) : (
            <div className="premium-table-container" style={{ marginTop: 14 }}>
              <table className="premium-table">
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th>Category</th>
                    <th>Strategy Used</th>
                    <th>Outcome</th>
                    <th>Discount Received</th>
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
                      <td>{typeof row.discount_received === 'number' ? `${row.discount_received}%` : '-'}</td>
                      <td>{typeof row.success_score === 'number' ? row.success_score : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recommended Strategy */}
        <div className="card-glass" style={{ marginBottom: 24 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Recommended Strategy</h3>

          {!strategy ? (
            <div style={{ marginTop: 14, color: '#94A3B8', fontSize: 13 }}>
              Strategy recommendation will appear after form submission.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14, marginTop: 14 }}>
              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14 }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Recommended Strategy</div>
                <div style={{ marginTop: 8, color: '#F8FAFC', fontSize: 14, fontWeight: 600 }}>{strategy.recommended_strategy}</div>
              </div>

              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14 }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Expected Discount Range</div>
                <div style={{ marginTop: 8, color: '#34D399', fontSize: 14, fontWeight: 700 }}>{strategy.expected_discount_range}</div>
              </div>

              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14 }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Confidence Score</div>
                <div style={{ marginTop: 8, color: '#60A5FA', fontSize: 14, fontWeight: 700 }}>{strategy.confidence_score}%</div>
              </div>

              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14, gridColumn: '1 / -1' }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Reasoning</div>
                <div style={{ marginTop: 8, color: '#CBD5E1', fontSize: 13.5, lineHeight: 1.6 }}>{strategy.reasoning}</div>
              </div>

              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14, gridColumn: '1 / -1' }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Risks</div>
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {(strategy.risks || []).length > 0 ? (
                    strategy.risks.map((risk, index) => (
                      <span
                        key={`${risk}-${index}`}
                        style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#FCA5A5', padding: '4px 10px', borderRadius: 999, fontSize: 12, fontWeight: 600 }}
                      >
                        {risk}
                      </span>
                    ))
                  ) : (
                    <span style={{ color: '#94A3B8', fontSize: 13 }}>No specific risks provided.</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Negotiation Email */}
        <div className="card-glass">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>Negotiation Email</h3>
            <button
              onClick={onCopyEmail}
              disabled={!email}
              style={{
                background: 'rgba(59, 130, 246, 0.12)',
                color: '#60A5FA',
                border: '1px solid rgba(59, 130, 246, 0.2)',
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

          {!email ? (
            <div style={{ marginTop: 14, color: '#94A3B8', fontSize: 13 }}>
              Generated email will appear after strategy generation.
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14 }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Email Subject</div>
                <div style={{ marginTop: 8, color: '#F8FAFC', fontSize: 14, fontWeight: 600 }}>{email.subject}</div>
              </div>

              <div style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 14 }}>
                <div style={{ color: '#94A3B8', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Email Body</div>
                <div style={{ marginTop: 8, color: '#CBD5E1', fontSize: 13.5, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{email.body}</div>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
