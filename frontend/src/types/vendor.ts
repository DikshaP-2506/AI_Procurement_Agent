// TypeScript type definitions for vendor domain.

export interface VendorCreate {
  procurement_id: string;
  vendor_name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  country?: string;
}

export interface Vendor extends VendorCreate {
  id: string;
  created_at: string;
  procurements?: {
    title: string;
  };
}

export interface VendorQuote {
  id: string;
  vendor_id: string;
  price: number;
  delivery_days: number;
  warranty_years: number;
  support_level: string;
  compliance_score: number;
  quote_file_url?: string;
  created_at: string;
}
