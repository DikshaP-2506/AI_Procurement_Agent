import React, { createContext, useContext, useState, useEffect } from 'react';
import { getProcurements, ProcurementProject } from '../api/procurementApi';

interface ProcurementContextProps {
  selectedProcurementId: string;
  setSelectedProcurementId: (id: string) => void;
  selectedProcurement: ProcurementProject | null;
  procurements: ProcurementProject[];
  loading: boolean;
  error: string | null;
  refreshProcurements: () => Promise<void>;
}

const ProcurementContext = createContext<ProcurementContextProps | undefined>(undefined);

export const ProcurementProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [procurements, setProcurements] = useState<ProcurementProject[]>([]);
  const [selectedProcurementId, setSelectedProcurementIdState] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshProcurements = async () => {
    try {
      setError(null);
      const data = await getProcurements();
      setProcurements(data);
      
      // Load saved selection from localStorage if valid
      const savedId = localStorage.getItem('selected_procurement_id');
      const isValidSaved = savedId && data.some(p => p.id === savedId);
      
      if (isValidSaved) {
        setSelectedProcurementIdState(savedId);
      } else if (data.length > 0) {
        // Default to the first procurement project
        setSelectedProcurementIdState(data[0].id);
        localStorage.setItem('selected_procurement_id', data[0].id);
      } else {
        setSelectedProcurementIdState('');
      }
    } catch (err) {
      console.error('Failed to load procurements', err);
      setError('Could not connect to database to fetch procurement projects.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshProcurements();
  }, []);

  const setSelectedProcurementId = (id: string) => {
    setSelectedProcurementIdState(id);
    localStorage.setItem('selected_procurement_id', id);
  };

  const selectedProcurement = procurements.find(p => p.id === selectedProcurementId) || null;

  return (
    <ProcurementContext.Provider
      value={{
        selectedProcurementId,
        setSelectedProcurementId,
        selectedProcurement,
        procurements,
        loading,
        error,
        refreshProcurements
      }}
    >
      {children}
    </ProcurementContext.Provider>
  );
};

export const useProcurement = () => {
  const context = useContext(ProcurementContext);
  if (context === undefined) {
    throw new Error('useProcurement must be used within a ProcurementProvider');
  }
  return context;
};
