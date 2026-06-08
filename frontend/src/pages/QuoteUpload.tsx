import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { getVendors } from '../api/vendorApi';
import uploadQuote from '../api/quoteApi';
import { Vendor } from '../types/vendor';

const PROCUREMENT_ID = '8ea2d01d-2137-4e83-8875-eb6a28d6e0c6';

export default function QuoteUpload() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [selectedVendor, setSelectedVendor] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const vs = await getVendors(PROCUREMENT_ID);
        setVendors(vs);
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);

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
      <div style={{ padding: '72px 16px', maxWidth: 800, margin: '0 auto' }}>
        <h1>Quote Intelligence</h1>
        <p style={{ color: '#9CA3AF' }}>Upload vendor quotes for AI extraction</p>

        <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 12, padding: 16 }}>
          <label style={{ display: 'block', marginBottom: 8 }}>Select Vendor</label>
          <select value={selectedVendor} onChange={e => setSelectedVendor(e.target.value)}>
            <option value="">-- select vendor --</option>
            {vendors.map(v => <option key={v.id} value={v.id}>{v.vendor_name}</option>)}
          </select>

          <div style={{ height: 12 }} />

          <label style={{ display: 'block', marginBottom: 8 }}>Upload PDF</label>
          <div style={{ border: '2px dashed #1F1F2E', padding: 16, borderRadius: 8 }} onClick={() => { }}>
            <input type="file" accept="application/pdf" onChange={e => setFile(e.target.files ? e.target.files[0] : null)} />
            {file && <div style={{ marginTop: 8 }}>{file.name}</div>}
          </div>

          <div style={{ height: 12 }} />
          <button onClick={onUpload} style={{ background: '#3B82F6', color: '#fff', padding: 12, width: '100%', borderRadius: 8, border: 'none' }}>
            {loading ? 'Uploading...' : 'Extract Quote with AI'}
          </button>

          {error && <div style={{ color: '#F87171', marginTop: 8 }}>{error}</div>}

          {result && (
            <div style={{ marginTop: 16, background: '#111118', border: '1px solid #10B981', padding: 16, borderRadius: 8 }}>
              <h3 style={{ margin: '0 0 12px 0', color: '#10B981' }}>Extraction Complete</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', fontSize: '14px' }}>
                <div><strong>Price:</strong> ${result.extracted_data?.price ?? 'N/A'}</div>
                <div><strong>Delivery:</strong> {result.extracted_data?.delivery_days ?? 'N/A'} days</div>
                <div><strong>Warranty:</strong> {result.extracted_data?.warranty_years ?? 'N/A'} years</div>
                <div><strong>Compliance:</strong> {result.extracted_data?.compliance_score ?? 'N/A'}/100</div>
              </div>
              <div style={{ marginTop: 12, fontSize: '14px' }}><strong>Terms:</strong> {result.extracted_data?.payment_terms || 'N/A'}</div>
              <div style={{ marginTop: 12, display: 'block' }}>
                <strong>File:</strong> <a href={result.file_url} target="_blank" rel="noreferrer" style={{ color: '#60A5FA', marginLeft: 8 }}>View Document</a>
              </div>
              <div style={{ marginTop: 12, background: '#09090B', padding: 8, borderRadius: 4, height: 60, overflowY: 'auto', fontSize: '12px' }}>
                {result.text_preview}...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
