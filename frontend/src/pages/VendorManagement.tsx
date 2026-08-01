import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Vendor, VendorCreate } from '../types/vendor';
import { createVendor, getVendors } from '../api/vendorApi';
import Navbar from '../components/Navbar';
import { useProcurement } from '../context/ProcurementContext';

export default function VendorManagement() {
  const { selectedProcurementId } = useProcurement();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [form, setForm] = useState<VendorCreate>({ procurement_id: selectedProcurementId, vendor_name: '', contact_person: '', email: '', phone: '', country: '' });
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (selectedProcurementId) {
      fetchVendors();
      setForm(prev => ({ ...prev, procurement_id: selectedProcurementId }));
    }
  }, [selectedProcurementId]);

  async function fetchVendors() {
    if (!selectedProcurementId) return;
    try {
      const data = await getVendors(selectedProcurementId);
      setVendors(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.vendor_name.trim() || !selectedProcurementId) return;
    
    try {
      setSubmitting(true);
      setMessage(null);
      await createVendor({ ...form, procurement_id: selectedProcurementId });
      setMessage({ text: 'Vendor registered successfully', isError: false });
      setForm({ procurement_id: selectedProcurementId, vendor_name: '', contact_person: '', email: '', phone: '', country: '' });
      fetchVendors();
      setTimeout(() => setMessage(null), 4000);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error creating vendor. Please check connection.';
      setMessage({ text: errorMsg, isError: true });
    } finally {
      setSubmitting(false);
    }
  }


  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh' }}>
      <Navbar />
      <div className="app-container">
        
        {/* Header Section */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ background: 'linear-gradient(90deg, #F1F5F9 30%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Vendor Directory
          </h1>
          <p style={{ marginTop: 4 }}>
            Register and manage your procurement suppliers in the active intelligence database.
          </p>
        </div>

        {/* Form and List Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, marginTop: 16 }}>
          
          {/* LEFT COLUMN: Add Supplier Form + Insights Card */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            
            {/* Add Vendor Form */}
            <div className="card-glass" style={{ height: 'fit-content' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: '#FFFFFF' }}>
                Add Supplier
              </h3>
              
              <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <input 
                    required
                    placeholder="Vendor Name (e.g. Apple Inc)" 
                    value={form.vendor_name} 
                    onChange={e => setForm({ ...form, vendor_name: e.target.value })} 
                  />
                </div>
                
                <div>
                  <input 
                    required
                    placeholder="Contact Person (e.g. John Doe)" 
                    value={form.contact_person} 
                    onChange={e => setForm({ ...form, contact_person: e.target.value })} 
                  />
                </div>
                
                <div>
                  <input 
                    required
                    type="email"
                    placeholder="Email Address (e.g. sales@vendor.com)" 
                    value={form.email} 
                    onChange={e => setForm({ ...form, email: e.target.value })} 
                  />
                </div>
                
                <div>
                  <input 
                    required
                    placeholder="Phone Number (e.g. +1 555-0199)" 
                    value={form.phone} 
                    onChange={e => setForm({ ...form, phone: e.target.value })} 
                  />
                </div>
                
                <div>
                  <input 
                    required
                    placeholder="Country (e.g. United States)" 
                    value={form.country} 
                    onChange={e => setForm({ ...form, country: e.target.value })} 
                  />
                </div>

                <button 
                  type="submit" 
                  disabled={submitting}
                  style={{ 
                    background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)', 
                    color: '#fff', 
                    padding: '12px', 
                    borderRadius: 10, 
                    border: 'none',
                    fontSize: 14,
                    fontWeight: 700,
                    marginTop: 8,
                    boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
                    opacity: submitting ? 0.7 : 1
                  }}
                >
                  {submitting ? 'Registering...' : 'Register Vendor'}
                </button>

                {message && (
                  <div style={{ 
                    marginTop: 10, 
                    padding: '10px 12px',
                    borderRadius: 8,
                    fontSize: 13,
                    background: message.isError ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                    border: `1px solid ${message.isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
                    color: message.isError ? '#FCA5A5' : '#D1FAE5'
                  }}>
                    {message.text}
                  </div>
                )}
              </form>
            </div>

            {/* Supplier Directory Insights */}
            <div className="card-glass" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                Supplier Database Insights
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <div style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Suppliers</div>
                  <div style={{ color: '#60A5FA', fontSize: 24, fontWeight: 850, marginTop: 4, lineHeight: 1 }}>{vendors.length}</div>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px 14px', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <div style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Global Coverage</div>
                  <div style={{ color: '#34D399', fontSize: 24, fontWeight: 850, marginTop: 4, lineHeight: 1 }}>
                    {new Set(vendors.map(v => v.country?.trim().toLowerCase()).filter(Boolean)).size} {new Set(vendors.map(v => v.country?.trim().toLowerCase()).filter(Boolean)).size === 1 ? 'Country' : 'Countries'}
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Vendors List */}
          <div className="card-glass" style={{ display: 'flex', flexDirection: 'column', gap: 16, maxHeight: 600 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                Registered suppliers ({vendors.length})
              </h3>
            </div>

            {/* Real-time search filter */}
            <div style={{ position: 'relative' }}>
              <input 
                type="text"
                placeholder="Search by supplier name, contact, or country..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  paddingLeft: 38,
                  fontSize: 13,
                  height: 38,
                  border: '1px solid rgba(255, 255, 255, 0.08)'
                }}
              />
              <svg style={{ position: 'absolute', left: 14, top: 12, width: 14, height: 14, color: '#94A3B8' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', flex: 1, paddingRight: 4 }}>
              {(() => {
                const filtered = vendors.filter(v => 
                  v.vendor_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                  (v.country && v.country.toLowerCase().includes(searchQuery.toLowerCase())) ||
                  (v.contact_person && v.contact_person.toLowerCase().includes(searchQuery.toLowerCase()))
                );
                
                if (filtered.length === 0) {
                  return (
                    <div style={{ color: '#6B7280', textAlign: 'center', padding: '48px 0', fontSize: 14 }}>
                      {vendors.length === 0 ? 'No suppliers registered yet.' : 'No matching suppliers found.'}
                    </div>
                  );
                }

                return filtered.map(v => (
                  <div 
                    key={v.id} 
                    style={{ 
                      background: 'rgba(0, 0, 0, 0.2)', 
                      border: '1px solid rgba(255, 255, 255, 0.04)', 
                      padding: 16, 
                      borderRadius: 12,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ color: '#FFFFFF', fontWeight: 700, fontSize: 15 }}>{v.vendor_name}</div>
                      <div style={{ 
                        background: 'rgba(59, 130, 246, 0.1)', 
                        color: '#60A5FA', 
                        padding: '2px 8px', 
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600
                      }}>
                        {v.country}
                      </div>
                    </div>
                    
                    <div style={{ color: '#94A3B8', fontSize: 13, display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <svg style={{ width: 14, height: 14, marginRight: 8, color: '#3B82F6', flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                        {v.contact_person}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <svg style={{ width: 14, height: 14, marginRight: 8, color: '#8B5CF6', flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                          <polyline points="22,6 12,13 2,6" />
                        </svg>
                        {v.email}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <svg style={{ width: 14, height: 14, marginRight: 8, color: '#10B981', flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                        </svg>
                        {v.phone}
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: 10 }}>
                      <span style={{ fontSize: 11, color: '#6B7280' }}>ID: {v.id.slice(0, 8)}...</span>
                      <Link 
                        to={`/risk/${v.id}`} 
                        style={{ 
                          color: '#34D399', 
                          fontSize: 12, 
                          textDecoration: 'none',
                          fontWeight: 600,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        Risk Analysis
                      </Link>
                    </div>
                  </div>
                ));
              })()}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
