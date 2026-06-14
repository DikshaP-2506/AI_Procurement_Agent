import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useProcurement } from '../context/ProcurementContext';
import { createProcurement } from '../api/procurementApi';

export default function Navbar() {
  const { selectedProcurementId, setSelectedProcurementId, procurements, refreshProcurements } = useProcurement();
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Modal form states
  const [title, setTitle] = useState('');
  const [department, setDepartment] = useState('IT');
  const [category, setCategory] = useState('Software');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const linkStyle = (isActive: boolean) => ({
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 600,
    textDecoration: 'none',
    color: isActive ? '#FFFFFF' : '#94A3B8',
    borderBottom: isActive ? '2px solid #3B82F6' : '2px solid transparent',
    transition: 'all 0.2s ease',
    display: 'inline-flex',
    alignItems: 'center',
    height: '100%'
  });

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    try {
      setSubmitting(true);
      setError(null);
      const newProject = await createProcurement({
        title: title.trim(),
        department,
        category
      });
      
      // Refresh context list and automatically select the new project
      await refreshProcurements();
      setSelectedProcurementId(newProject.id);
      
      // Reset form and close modal
      setTitle('');
      setDepartment('IT');
      setCategory('Software');
      setIsModalOpen(false);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to create procurement project.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <nav style={{ 
      background: 'rgba(8, 10, 20, 0.75)', 
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      height: 60, 
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)', 
      position: 'fixed', 
      top: 0, 
      width: '100%', 
      zIndex: 100 
    }}>
      <div style={{ 
        width: '100%', 
        height: '100%', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        padding: '0 40px' 
      }}>
        
        {/* Left Side: Logo & Dynamic Project Selector */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {/* Brand Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ 
              width: 10, 
              height: 10, 
              background: 'linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%)', 
              borderRadius: '50%',
              boxShadow: '0 0 10px rgba(59, 130, 246, 0.8)' 
            }} />
            <div style={{ 
              color: '#FFFFFF', 
              fontWeight: 800, 
              fontSize: '18px', 
              letterSpacing: '-0.02em',
              background: 'linear-gradient(90deg, #FFFFFF 50%, #94A3B8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              ProcureAI
            </div>
          </div>

          {/* Vertical Divider */}
          <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.15)', margin: '0 16px' }} />

          {/* Selector & Add Button Container */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <select
              value={selectedProcurementId}
              onChange={(e) => setSelectedProcurementId(e.target.value)}
              style={{
                background: 'rgba(16, 20, 38, 0.8)',
                color: '#FFFFFF',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRadius: '8px',
                padding: '6px 14px',
                fontSize: '13px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
              }}
            >
              {procurements.length === 0 ? (
                <option value="">No active projects</option>
              ) : (
                procurements.map((p) => (
                  <option key={p.id} value={p.id} style={{ background: '#0A0A0F', color: '#FFFFFF' }}>
                    {p.title}
                  </option>
                ))
              )}
            </select>

            {/* "+" Add Project Button */}
            <button
              onClick={() => setIsModalOpen(true)}
              title="Create New Project"
              style={{
                background: 'rgba(59, 130, 246, 0.1)',
                color: '#60A5FA',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRadius: '8px',
                width: 30,
                height: 30,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '16px',
                fontWeight: 'bold',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                outline: 'none'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)';
                e.currentTarget.style.boxShadow = '0 0 8px rgba(59, 130, 246, 0.4)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              +
            </button>
          </div>
        </div>

        {/* Right Side: Links Navigation */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', height: '100%' }}>
          <NavLink to="/" style={({ isActive }) => linkStyle(isActive)}>
            Vendors
          </NavLink>
          <NavLink to="/comparison" style={({ isActive }) => linkStyle(isActive)}>
            Compare
          </NavLink>
          <NavLink to="/upload" style={({ isActive }) => linkStyle(isActive)}>
            Upload Quote
          </NavLink>
          <NavLink to="/risk" style={({ isActive }) => linkStyle(isActive)}>
            Risk Dashboard
          </NavLink>
          <NavLink to="/optimization" style={({ isActive }) => linkStyle(isActive)}>
            Optimization
          </NavLink>
          <NavLink to="/negotiation" style={({ isActive }) => linkStyle(isActive)}>
            Negotiation Intelligence
          </NavLink>
        </div>

      </div>
    </nav>

      {/* Glassmorphic Project Creation Modal */}
      {isModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          zIndex: 999, padding: 16, backdropFilter: 'blur(6px)'
        }}>
          <div style={{
            background: 'rgba(16, 20, 38, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: 16,
            padding: 24,
            maxWidth: 450,
            width: '100%',
            maxHeight: 'calc(100vh - 32px)',
            overflowY: 'auto',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16
          }}>
            <h3 style={{ fontSize: 18, color: '#FFFFFF', margin: 0, fontWeight: 700 }}>
              Create Procurement Project
            </h3>
            
            <form onSubmit={handleCreateProject} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Project Title */}
              <div>
                <label style={{ display: 'block', fontSize: 12, color: '#E2E8F0', fontWeight: 600, marginBottom: 6 }}>
                  Project Title
                </label>
                <input
                  required
                  type="text"
                  placeholder="e.g. Software Licenses - Security"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(0, 0, 0, 0.35)',
                    color: '#F8FAFC',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    fontSize: 13.5,
                    outline: 'none'
                  }}
                />
              </div>

              {/* Department Selector */}
              <div>
                <label style={{ display: 'block', fontSize: 12, color: '#E2E8F0', fontWeight: 600, marginBottom: 6 }}>
                  Department
                </label>
                <select
                  value={department}
                  onChange={e => setDepartment(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(0, 0, 0, 0.35)',
                    color: '#F8FAFC',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    fontSize: 13.5,
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  {['IT', 'Finance', 'HR', 'Operations', 'Marketing', 'Security', 'Legal', 'Sales'].map(dept => (
                    <option key={dept} value={dept} style={{ background: '#0A0A0F', color: '#FFFFFF' }}>
                      {dept}
                    </option>
                  ))}
                </select>
              </div>

              {/* Category Selector */}
              <div>
                <label style={{ display: 'block', fontSize: 12, color: '#E2E8F0', fontWeight: 600, marginBottom: 6 }}>
                  Category
                </label>
                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(0, 0, 0, 0.35)',
                    color: '#F8FAFC',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    fontSize: 13.5,
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  {['Software', 'Hardware', 'Networking', 'Consulting', 'Services', 'Leases'].map(cat => (
                    <option key={cat} value={cat} style={{ background: '#0A0A0F', color: '#FFFFFF' }}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {error && (
                <div style={{ 
                  padding: '8px 10px', 
                  background: 'rgba(239, 68, 68, 0.08)', 
                  border: '1px solid rgba(239, 68, 68, 0.2)', 
                  borderRadius: 8, 
                  color: '#FCA5A5', 
                  fontSize: 12.5 
                }}>
                  {error}
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
                <button 
                  type="button" 
                  onClick={() => { setIsModalOpen(false); setTitle(''); setError(null); }}
                  style={{
                    background: 'transparent', color: '#9CA3AF', border: '1px solid rgba(255,255,255,0.08)',
                    padding: '8px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={submitting || !title.trim()}
                  style={{
                    background: '#3B82F6', color: '#FFFFFF', border: 'none',
                    padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                    cursor: 'pointer', opacity: submitting ? 0.6 : 1,
                    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                  }}
                >
                  {submitting ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
