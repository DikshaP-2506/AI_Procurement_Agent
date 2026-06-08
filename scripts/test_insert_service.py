import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from backend.app.supabase_client import supabase_service

print('supabase_service is', bool(supabase_service))
if not supabase_service:
    raise SystemExit('no service client')

try:
    record = {
        'vendor_id': 'b0ff0e97-9eed-45d6-94a6-e9baf6142d2f',
        'quote_file_url': 'http://test.com/file.pdf',
        'price': 1000,
        'delivery_days': 7,
        'warranty_years': 1,
        'support_level': 'Standard',
        'payment_terms': 'N/A',
        'compliance_score': 80,
        'extracted_json': {'test': True}
    }
    resp = supabase_service.table('vendor_quotes').insert(record).execute()
    print('SUCCESS:', resp)
except Exception as e:
    print('INSERT ERROR:', e)
