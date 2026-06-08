import api from './vendorApi';

export async function uploadQuote(vendorId: string, file: File) {
  try {
    const form = new FormData();
    form.append('vendor_id', vendorId);
    form.append('file', file);
    const res = await api.post('/quotes/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return res.data;
  } catch (err) {
    console.error('uploadQuote error', err);
    throw err;
  }
}

export default uploadQuote;
