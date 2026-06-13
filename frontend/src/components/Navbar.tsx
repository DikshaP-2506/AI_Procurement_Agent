import React from 'react';
import { NavLink } from 'react-router-dom';

export default function Navbar() {
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

  return (
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
        maxWidth: 1200, 
        margin: '0 auto', 
        height: '100%', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        padding: '0 20px' 
      }}>
        
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

        {/* Links Navigation */}
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
  );
}
