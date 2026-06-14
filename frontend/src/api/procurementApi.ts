import api from './vendorApi';

export interface ProcurementProject {
  id: string;
  title: string;
  department: string;
  category: string;
  status: string;
  created_at?: string;
  description?: string;
}

export async function getProcurements(): Promise<ProcurementProject[]> {
  try {
    const res = await api.get('/procurements/');
    return res.data as ProcurementProject[];
  } catch (err) {
    console.error('getProcurements error', err);
    throw err;
  }
}

export async function createProcurement(data: { title: string; department: string; category: string }): Promise<ProcurementProject> {
  try {
    const res = await api.post('/procurements/', data);
    return res.data as ProcurementProject;
  } catch (err) {
    console.error('createProcurement error', err);
    throw err;
  }
}

