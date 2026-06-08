import React from 'react';
import { NavLink } from 'react-router-dom';

const linkClass = (isActive: boolean) =>
  `px-3 py-2 text-sm ${isActive ? 'text-[#F1F5F9] border-b-2 border-[#3B82F6]' : 'text-[#6B7280] hover:text-[#F1F5F9] transition-colors'}`;

export default function Navbar() {
  return (
    <nav style={{ background: '#0D0D14', height: 56, borderBottom: '1px solid #1F1F2E', position: 'fixed', top: 0, width: '100%', zIndex: 100 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, background: '#3B82F6', borderRadius: 4 }} />
          <div style={{ color: '#FFFFFF', fontWeight: 700 }}>ProcureAI</div>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <NavLink to="/" className={({ isActive }) => linkClass(isActive)}>
            Vendors
          </NavLink>
          <NavLink to="/comparison" className={({ isActive }) => linkClass(isActive)}>
            Compare
          </NavLink>
          <NavLink to="/upload" className={({ isActive }) => linkClass(isActive)}>
            Upload Quote
          </NavLink>
        </div>
      </div>
    </nav>
  );
}
