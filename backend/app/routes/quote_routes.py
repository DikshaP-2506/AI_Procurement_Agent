from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from ..supabase_client import supabase, supabase_service
from ..services.pdf_parser import extract_text_from_pdf
from ..agents.quote_agent import extract_quote_data

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post('/upload')
async def upload_quote(vendor_id: str = Form(...), file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # Use service role client for storage if available to avoid RLS issues
        client = supabase_service if supabase_service else supabase
        
        # Upload to Supabase storage
        path = f"quotes/{vendor_id}/{file.filename}"
        upload_res = client.storage.from_("quote-files").upload(path, contents)

        # get public url (handle string or object response variants)
        public_res = client.storage.from_("quote-files").get_public_url(path)
        public_url = public_res if isinstance(public_res, str) else getattr(public_res, 'public_url', str(public_res))

        # extract text
        text = extract_text_from_pdf(contents)

        # Call AI agent to extract structured fields
        ai_result = extract_quote_data(text)

        # insert into vendor_quotes including AI-extracted fields
        record = {
            'vendor_id': vendor_id,
            'quote_file_url': public_url,
            'price': ai_result.get('price'),
            'delivery_days': ai_result.get('delivery_days'),
            'warranty_years': ai_result.get('warranty_years'),
            'support_level': ai_result.get('support_level'),
            'payment_terms': ai_result.get('payment_terms'),
            'compliance_score': ai_result.get('compliance_score'),
            'extracted_json': {
                'raw_text': text,
                'full_ai_result': ai_result,
            },
        }
        # Use service-role client for inserts to bypass RLS if available
        if supabase_service:
            resp = supabase_service.table('vendor_quotes').insert(record).execute()
        else:
            resp = supabase.table('vendor_quotes').insert(record).execute()
        if not resp.data:
            raise HTTPException(status_code=500, detail='Failed to insert quote record')
        inserted = resp.data[0]
        quote_id = inserted.get('id')

        # insert audit log for agent run
        try:
            if supabase_service:
                supabase_service.table('audit_logs').insert({
                    'agent_name': 'Quote Extraction Agent',
                    'action_type': 'quote_extraction',
                    'input_payload': {'vendor_id': vendor_id, 'filename': file.filename},
                    'output_payload': ai_result,
                    'reasoning': 'Extracted via Groq llama3',
                }).execute()
            else:
                supabase.table('audit_logs').insert({
                    'agent_name': 'Quote Extraction Agent',
                    'action_type': 'quote_extraction',
                    'input_payload': {'vendor_id': vendor_id, 'filename': file.filename},
                    'output_payload': ai_result,
                    'reasoning': 'Extracted via Groq llama3',
                }).execute()
        
        except Exception:
            pass

        return {
            'message': 'Quote uploaded successfully',
            'file_url': public_url,
            'vendor_id': vendor_id,
            'quote_id': quote_id,
            'text_preview': text[:200],
            'extracted_data': ai_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def get_quotes(vendor_id: str):
    client = supabase_service if supabase_service else supabase
    result = client.table("vendor_quotes")\
        .select("*")\
        .eq("vendor_id", vendor_id)\
        .execute()
    return result.data
