import requests
import uuid
url='http://127.0.0.1:8000/quotes/upload'
# Use more realistic text for testing
fake_pdf_content = b"""
Dell Technologies Quote
Subtotal: $15,400.00
Delivery: 10 working days
Warranty: 3 Year ProSupport
Terms: Net 30 days
Compliance: 100%
"""
filename = f'test_quote_{uuid.uuid4().hex[:8]}.pdf'
files={'file':(filename, fake_pdf_content, 'application/pdf')}
data={'vendor_id':'b0ff0e97-9eed-45d6-94a6-e9baf6142d2f'}
try:
    r=requests.post(url, files=files, data=data, timeout=30)
    print('STATUS', r.status_code)
    print(r.text)
except Exception as e:
    print('ERROR', e)
