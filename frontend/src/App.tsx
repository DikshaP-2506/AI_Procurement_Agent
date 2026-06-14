import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import VendorManagement from './pages/VendorManagement';
import VendorComparison from './pages/VendorComparison';
import QuoteUpload from './pages/QuoteUpload';
import RiskDashboard from './pages/RiskDashboard';
import VendorRiskOverview from './pages/VendorRiskOverview';
import OptimizationDashboard from "./pages/OptimizationDashboard";
import NegotiationIntelligence from './pages/NegotiationIntelligence';
import { ProcurementProvider } from './context/ProcurementContext';
import './styles.css';

export default function App() {
  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh' }}>
      <ProcurementProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<VendorManagement />} />
            <Route path="/comparison" element={<VendorComparison />} />
            <Route path="/upload" element={<QuoteUpload />} />
            <Route path="/risk" element={<RiskDashboard />} />
            <Route path="/risk/:vendorId" element={<VendorRiskOverview />} />
            <Route path="/optimization" element={<OptimizationDashboard />} />
            <Route path="/negotiation" element={<NegotiationIntelligence />} />
          </Routes>
        </BrowserRouter>
      </ProcurementProvider>
    </div>
  );
}
// Note: single default export `App` is defined above.