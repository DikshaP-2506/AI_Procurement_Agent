import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import VendorManagement from './pages/VendorManagement';
import VendorComparison from './pages/VendorComparison';
import QuoteUpload from './pages/QuoteUpload';
import Navbar from './components/Navbar';
import './styles.css';

export default function App() {
  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh' }}>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={<VendorManagement />} />
          <Route path="/comparison" element={<VendorComparison />} />
          <Route path="/upload" element={<QuoteUpload />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}
// Note: single default export `App` is defined above.