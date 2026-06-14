import React, { useState, useEffect, useRef } from 'react';
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

  // Searchable dropdown states & refs
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedProject = procurements.find(p => p.id === selectedProcurementId);
  const filteredProjects = procurements.filter(p => 
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.department.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
            <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }}>
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
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
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  minWidth: 320,
                  justifyContent: 'space-between'
                }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }}>
                  {selectedProject ? selectedProject.title : 'Select Project...'}
                </span>
                <svg 
                  style={{ 
                    width: 10, 
                    height: 10, 
                    transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)', 
                    transition: 'transform 0.2s ease',
                    color: '#94A3B8',
                    flexShrink: 0
                  }} 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="3" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {isDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  left: 0,
                  background: 'rgba(16, 20, 38, 0.96)',
                  backdropFilter: 'blur(20px)',
                  WebkitBackdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  width: 350,
                  boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                  zIndex: 200,
                  padding: 10,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8
                }}>
                  {/* Search Input */}
                  <div style={{ position: 'relative' }}>
                    <input
                      type="text"
                      placeholder="Search projects..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      autoFocus
                      style={{
                        width: '100%',
                        background: 'rgba(0, 0, 0, 0.3)',
                        color: '#FFFFFF',
                        border: '1px solid rgba(59, 130, 246, 0.2)',
                        borderRadius: '6px',
                        padding: '6px 10px 6px 28px',
                        fontSize: '12px',
                        outline: 'none',
                        transition: 'border-color 0.2s'
                      }}
                    />
                    <svg 
                      style={{ position: 'absolute', left: 8, top: 9, width: 12, height: 12, color: '#64748B' }} 
                      viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                    >
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                  </div>

                  {/* List Container */}
                  <div style={{
                    maxHeight: 220,
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    paddingRight: 2
                  }}>
                    {filteredProjects.length === 0 ? (
                      <div style={{ color: '#64748B', fontSize: '12px', padding: '12px 8px', textAlign: 'center' }}>
                        No projects found
                      </div>
                    ) : (
                      filteredProjects.map((p) => {
                        const isSelected = p.id === selectedProcurementId;
                        return (
                          <div
                            key={p.id}
                            onClick={() => {
                              setSelectedProcurementId(p.id);
                              setIsDropdownOpen(false);
                              setSearchQuery('');
                            }}
                            style={{
                              padding: '8px 10px',
                              borderRadius: '6px',
                              fontSize: '12.5px',
                              cursor: 'pointer',
                              color: isSelected ? '#3B82F6' : '#E2E8F0',
                              background: isSelected ? 'rgba(59, 130, 246, 0.08)' : 'transparent',
                              transition: 'all 0.15s ease',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 2,
                              textAlign: 'left'
                            }}
                            onMouseEnter={(e) => {
                              if (!isSelected) {
                                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                                e.currentTarget.style.color = '#FFFFFF';
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (!isSelected) {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.color = '#E2E8F0';
                              }
                            }}
                          >
                            <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.title}</div>
                            <div style={{ fontSize: '10.5px', color: '#64748B' }}>
                              {p.department} • {p.category}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

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
