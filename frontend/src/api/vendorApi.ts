import axios from 'axios';
import { VendorCreate, Vendor, VendorQuote } from '../types/vendor';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  headers: { 'Content-Type': 'application/json' },
});

export async function createVendor(data: VendorCreate): Promise<Vendor> {
  try {
    const res = await api.post('/vendors/', data);
    return res.data as Vendor;
  } catch (err) {
    console.error('createVendor error', err);
    throw err;
  }
}

export async function getVendors(procurementId: string): Promise<Vendor[]> {
  try {
    const res = await api.get('/vendors', { params: { procurement_id: procurementId } });
    return res.data as Vendor[];
  } catch (err) {
    console.error('getVendors error', err);
    throw err;
  }
}

export async function getVendorById(id: string): Promise<Vendor> {
  try {
    const res = await api.get(`/vendors/${id}`);
    return res.data as Vendor;
  } catch (err) {
    console.error('getVendorById error', err);
    throw err;
  }
}

export async function getVendorQuotes(vendorId: string): Promise<VendorQuote[]> {
  try {
    const res = await api.get('/quotes/', { params: { vendor_id: vendorId } });
    return res.data as VendorQuote[];
  } catch (err) {
    console.error('getVendorQuotes error', err);
    throw err;
  }
}

export default api;
