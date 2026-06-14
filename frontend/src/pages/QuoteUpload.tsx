import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { getVendors } from '../api/vendorApi';
import uploadQuote from '../api/quoteApi';
import { Vendor } from '../types/vendor';
import { useProcurement } from '../context/ProcurementContext';

export default function QuoteUpload() {
  const { selectedProcurementId } = useProcurement();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [selectedVendor, setSelectedVendor] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedProcurementId) {
      (async () => {
        try {
          const vs = await getVendors(selectedProcurementId);
          setVendors(vs);
          setSelectedVendor(''); // Reset vendor selection when project changes
        } catch (e) {
          console.error(e);
        }
      })();
    }
  }, [selectedProcurementId]);

  async function onUpload() {
    if (!selectedVendor || !file) {
      setError('Select vendor and file');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await uploadQuote(selectedVendor, file);
      setResult(res);
    } catch (e) {
      setError('Upload failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh' }}>
      <Navbar />
      <div className="app-container" style={{ maxWidth: 800 }}>
        
        {/* Page Header */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ background: 'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Quote Intelligence
          </h1>
          <p style={{ marginTop: 4 }}>
            Upload vendor quotes for automated AI extraction, analysis, and metric normalization.
          </p>
        </div>

        {/* Upload Form Area */}
        <div className="card-glass" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 700, color: '#E2E8F0', marginBottom: 8 }}>
              Select Vendor
            </label>
            <select 
              value={selectedVendor} 
              onChange={e => setSelectedVendor(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.35)',
                color: '#F8FAFC',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 10,
                padding: '12px 14px',
                fontSize: 14,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="">-- select vendor --</option>
              {vendors.map(v => {
                const suffix = v.procurements?.title ? ` (${v.procurements.title})` : '';
                return <option key={v.id} value={v.id}>{v.vendor_name}{suffix}</option>;
              })}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 700, color: '#E2E8F0', marginBottom: 8 }}>
              Upload Quote PDF
            </label>
            <div style={{ 
              border: '2px dashed rgba(59, 130, 246, 0.25)', 
              background: 'rgba(0, 0, 0, 0.2)',
              padding: '24px 16px', 
              borderRadius: 12,
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              position: 'relative'
            }}>
              <input 
                type="file" 
                accept="application/pdf" 
                onChange={e => setFile(e.target.files ? e.target.files[0] : null)}
                style={{
                  position: 'absolute',
                  top: 0, left: 0, width: '100%', height: '100%',
                  opacity: 0, cursor: 'pointer'
                }}
              />
              <svg style={{ width: 36, height: 36, color: '#3B82F6', marginBottom: 8, opacity: 0.8 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div style={{ color: '#E2E8F0', fontSize: 14, fontWeight: 600 }}>
                {file ? file.name : 'Click to select or drag PDF quote here'}
              </div>
              <div style={{ color: '#94A3B8', fontSize: 12, marginTop: 4 }}>
                Supports standard PDF documents up to 10MB
              </div>
            </div>
          </div>

          <button 
            onClick={onUpload} 
            disabled={loading}
            style={{ 
              background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)', 
              color: '#fff', 
              padding: '12px', 
              width: '100%', 
              borderRadius: 10, 
              border: 'none',
              fontSize: 14,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Extracting with AI...' : 'Extract Quote with AI'}
          </button>

          {error && (
            <div style={{ 
              padding: '10px 12px', 
              background: 'rgba(239, 68, 68, 0.08)', 
              border: '1px solid rgba(239, 68, 68, 0.2)', 
              borderRadius: 8, 
              color: '#FCA5A5', 
              fontSize: 13 
            }}>
              {error}
            </div>
          )}

          {result && (
            <div style={{ 
              marginTop: 12, 
              background: 'rgba(16, 185, 129, 0.04)', 
              border: '1px solid rgba(16, 185, 129, 0.25)', 
              padding: 20, 
              borderRadius: 12 
            }}>
              <h3 style={{ margin: '0 0 14px 0', color: '#34D399', fontSize: 16, fontWeight: 700 }}>
                Extraction Complete
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '16px', fontSize: '14px' }}>
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: 10, borderRadius: 8, border: '1px solid rgba(255,255,255,0.02)' }}>
                  <span style={{ color: '#94A3B8', fontSize: 11, display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Price</span>
                  <strong style={{ color: '#F8FAFC', fontSize: 16 }}>${result.extracted_data?.price ?? 'N/A'}</strong>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: 10, borderRadius: 8, border: '1px solid rgba(255,255,255,0.02)' }}>
                  <span style={{ color: '#94A3B8', fontSize: 11, display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Delivery</span>
                  <strong style={{ color: '#F8FAFC', fontSize: 16 }}>{result.extracted_data?.delivery_days ?? 'N/A'} days</strong>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: 10, borderRadius: 8, border: '1px solid rgba(255,255,255,0.02)' }}>
                  <span style={{ color: '#94A3B8', fontSize: 11, display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Warranty</span>
                  <strong style={{ color: '#F8FAFC', fontSize: 16 }}>{result.extracted_data?.warranty_years ?? 'N/A'} years</strong>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: 10, borderRadius: 8, border: '1px solid rgba(255,255,255,0.02)' }}>
                  <span style={{ color: '#94A3B8', fontSize: 11, display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Compliance</span>
                  <strong style={{ color: '#34D399', fontSize: 16 }}>{result.extracted_data?.compliance_score ?? 'N/A'}/100</strong>
                </div>
              </div>
              
              <div style={{ marginTop: 14, fontSize: '13.5px', color: '#E2E8F0' }}>
                <strong>Payment Terms:</strong> {result.extracted_data?.payment_terms || 'N/A'}
              </div>
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, fontSize: '13.5px' }}>
                <strong>Uploaded File:</strong> 
                <a href={result.file_url} target="_blank" rel="noreferrer" style={{ color: '#3B82F6', fontWeight: 600, textDecoration: 'none' }}>
                  View Document
                </a>
              </div>
              
              {result.text_preview && (
                <div style={{ 
                  marginTop: 16, 
                  background: '#04050a', 
                  border: '1px solid rgba(255,255,255,0.04)',
                  padding: 12, 
                  borderRadius: 8, 
                  maxHeight: 90, 
                  overflowY: 'auto', 
                  fontSize: '12.5px',
                  color: '#94A3B8',
                  lineHeight: 1.6,
                  fontFamily: 'monospace'
                }}>
                  {result.text_preview}...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
