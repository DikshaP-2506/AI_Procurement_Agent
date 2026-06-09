import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Vendor, VendorCreate } from '../types/vendor';
import { createVendor, getVendors } from '../api/vendorApi';
import Navbar from '../components/Navbar';

const PROCUREMENT_ID = '8ea2d01d-2137-4e83-8875-eb6a28d6e0c6';

export default function VendorManagement() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [form, setForm] = useState<VendorCreate>({ procurement_id: PROCUREMENT_ID, vendor_name: '', contact_person: '', email: '', phone: '', country: '' });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchVendors();
  }, []);

  async function fetchVendors() {
    try {
      const data = await getVendors(PROCUREMENT_ID);
      setVendors(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createVendor(form);
      setMessage('Vendor created successfully');
      setForm({ ...form, vendor_name: '', contact_person: '', email: '', phone: '', country: '' });
      fetchVendors();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage('Error creating vendor');
    }
  }

  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh' }}>
      <Navbar />
      <div style={{ padding: '72px 16px', maxWidth: 1200, margin: '0 auto' }}>
        <h1 style={{ fontSize: 24 }}>Vendor Intelligence</h1>
        <p style={{ color: '#9CA3AF' }}>Manage your procurement vendors</p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginTop: 16 }}>
          <div>
            <div style={{ background: '#111118', border: '1px solid #1F1F2E', padding: 16, borderRadius: 10 }}>
              <h3 style={{ marginBottom: 8 }}>Add Vendor</h3>
              <form onSubmit={onSubmit}>
                <input placeholder="Vendor Name" value={form.vendor_name} onChange={e => setForm({ ...form, vendor_name: e.target.value })} />
                <div style={{ height: 8 }} />
                <input placeholder="Contact Person" value={form.contact_person} onChange={e => setForm({ ...form, contact_person: e.target.value })} />
                <div style={{ height: 8 }} />
                <input placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                <div style={{ height: 8 }} />
                <input placeholder="Phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
                <div style={{ height: 8 }} />
                <input placeholder="Country" value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} />
                <div style={{ height: 12 }} />
                <button style={{ background: '#3B82F6', color: '#fff', padding: '10px 12px', borderRadius: 8, width: '100%', border: 'none' }}>Add Vendor</button>
                {message && <div style={{ marginTop: 8, color: message.includes('Error') ? '#F87171' : '#10B981' }}>{message}</div>}
              </form>
            </div>
          </div>

          <div>
            <div style={{ background: '#111118', border: '1px solid #1F1F2E', padding: 16, borderRadius: 10 }}>
              <h3>Vendors</h3>
              {vendors.length === 0 ? (
                <div style={{ color: '#6B7280', textAlign: 'center', padding: 24 }}>No vendors added yet</div>
              ) : (
                vendors.map(v => (
                  <div key={v.id} style={{ background: '#111118', border: '1px solid #1F1F2E', padding: 12, borderRadius: 8, marginBottom: 8 }}>
                    <div style={{ color: '#FFFFFF', fontWeight: 700 }}>{v.vendor_name}</div>
                    <div style={{ color: '#6B7280', fontSize: 13 }}>{v.contact_person} • {v.email}</div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8, flexWrap: 'wrap' }}>
                      <div style={{ display: 'inline-block', background: '#1A2744', color: '#60A5FA', padding: '4px 8px', borderRadius: 6 }}>{v.country}</div>
                      <Link to={`/risk/${v.id}`} style={{ color: '#34D399', fontSize: 13, textDecoration: 'none' }}>View Risk</Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
