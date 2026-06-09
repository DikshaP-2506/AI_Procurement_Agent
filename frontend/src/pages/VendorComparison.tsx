import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Vendor, VendorQuote } from '../types/vendor';
import { getVendors, getVendorQuotes } from '../api/vendorApi';
import Navbar from '../components/Navbar';

const PROCUREMENT_ID = '8ea2d01d-2137-4e83-8875-eb6a28d6e0c6';

export default function VendorComparison() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [quotesMap, setQuotesMap] = useState<Record<string, VendorQuote[]>>({});

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const vs = await getVendors(PROCUREMENT_ID);
    setVendors(vs);
    const map: Record<string, VendorQuote[]> = {};
    await Promise.all(vs.map(async v => {
      const q = await getVendorQuotes(v.id);
      console.log(`Quotes for ${v.vendor_name} (${v.id}):`, q);
      map[v.id] = q;
    }));
    setQuotesMap(map);
  }

  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh' }}>
      <Navbar />
      <div style={{ padding: '72px 16px', maxWidth: 1200, margin: '0 auto' }}>
        <h1>Vendor Comparison</h1>
        <p style={{ color: '#9CA3AF' }}>AI-ready vendor intelligence overview</p>

        <div style={{ background: '#111118', border: '1px solid #1F1F2E', borderRadius: 12, overflow: 'hidden', marginTop: 16 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ background: '#0D0D14', color: '#6B7280', textTransform: 'uppercase', fontSize: 11 }}>
              <tr>
                <th style={{ padding: 12, textAlign: 'left' }}>Vendor</th>
                <th style={{ padding: 12 }}>Price</th>
                <th style={{ padding: 12 }}>Delivery Days</th>
                <th style={{ padding: 12 }}>Warranty</th>
                <th style={{ padding: 12 }}>Support</th>
                <th style={{ padding: 12 }}>Compliance</th>
                <th style={{ padding: 12 }}>Risk</th>
              </tr>
            </thead>
            <tbody>
              {vendors.map(v => {
                const q = quotesMap[v.id] && quotesMap[v.id][0];
                if (!q) return (
                  <tr key={v.id}><td colSpan={7} style={{ padding: 12 }}>No quotes for {v.vendor_name}</td></tr>
                );
                const scoreColor = q.compliance_score >= 80 ? '#10B981' : q.compliance_score >= 60 ? '#F59E0B' : '#F87171';
                return (
                  <tr key={v.id} style={{ borderTop: '1px solid #1F1F2E' }}>
                    <td style={{ padding: 12 }}>{v.vendor_name}</td>
                    <td style={{ padding: 12 }}>{q.price}</td>
                    <td style={{ padding: 12 }}>{q.delivery_days}</td>
                    <td style={{ padding: 12 }}>{q.warranty_years} yrs</td>
                    <td style={{ padding: 12 }}>{q.support_level}</td>
                    <td style={{ padding: 12, color: scoreColor }}>{q.compliance_score}</td>
                    <td style={{ padding: 12 }}><Link to={`/risk/${v.id}`} style={{ color: '#60A5FA', textDecoration: 'none' }}>Open</Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
