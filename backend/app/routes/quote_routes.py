from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
import traceback
from ..supabase_client import supabase, supabase_service
from ..services.pdf_parser import extract_text_from_pdf
from ..agents.quote_agent import extract_quote_data

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post('/upload')
async def upload_quote(vendor_id: str = Form(...), file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    last_step = None
    try:
        contents = await file.read()

        # Use service role client for storage if available to avoid RLS issues
        client = supabase_service if supabase_service else supabase
        
        # Upload to Supabase storage (upsert/overwrite if duplicate file exists)
        path = f"quotes/{vendor_id}/{file.filename}"
        # 1) Upload file to storage
        last_step = "storage_upload"
        try:
            upload_res = client.storage.from_("quote-files").upload(path, contents)
        except Exception as upload_err:
            # If file exists, try update; otherwise surface error
            if "already exists" in str(upload_err) or "Duplicate" in str(upload_err) or "409" in str(upload_err):
                last_step = "storage_update"
                upload_res = client.storage.from_("quote-files").update(path, contents)
            else:
                raise

        # 2) Get public URL for uploaded file
        last_step = "get_public_url"
        public_res = client.storage.from_("quote-files").get_public_url(path)
        public_url = public_res if isinstance(public_res, str) else getattr(public_res, 'public_url', str(public_res))

        # Fetch vendor name to personalize contract default name
        vendor_name = "Vendor"
        try:
            vendor_resp = client.table("vendors").select("vendor_name").eq("id", vendor_id).execute()
            if vendor_resp.data:
                vendor_name = vendor_resp.data[0].get("vendor_name", "Vendor").strip()
        except Exception as ve:
            print(f"Warning: Failed to fetch vendor name: {ve}")

        # extract text
        text = extract_text_from_pdf(contents)

        # 3) Fetch existing quotes for this vendor to perform duplicate check
        existing_quotes = []
        try:
            last_step = "fetch_existing_quotes"
            eq_resp = client.table("vendor_quotes").select("id, invoice_number, quote_number, extracted_json").eq("vendor_id", vendor_id).execute()
            existing_quotes = eq_resp.data or []
        except Exception:
            try:
                last_step = "fetch_existing_quotes_fallback"
                eq_resp = client.table("vendor_quotes").select("*").eq("vendor_id", vendor_id).execute()
                existing_quotes = eq_resp.data or []
            except Exception as eq_err2:
                print(f"Warning: Failed to fetch existing quotes for duplicate check: {eq_err2}")

        # 4) Call AI agent to extract structured fields (passing current date as baseline)
        from datetime import datetime
        today_str = datetime.now().date().isoformat()
        last_step = "ai_extraction"
        ai_result = extract_quote_data(text, today_str, existing_quotes=existing_quotes)

        # Extract flat dictionary for database insertions & backward-compatible return values
        extracted_data = ai_result.get('extracted_data', {})

        # Safe casting functions to prevent database column insertion type errors
        def clean_numeric(val):
            if val == "Data Not Available" or val is None:
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        def clean_int(val, default=None):
            if val == "Data Not Available" or val is None:
                return default
            try:
                # Accept floats and float-strings like '10.0' by converting to int
                if isinstance(val, float):
                    return int(val)
                if isinstance(val, str):
                    # strip whitespace
                    s = val.strip()
                    # handle float strings
                    if s.replace('.', '', 1).isdigit():
                        return int(float(s))
                return int(val)
            except (ValueError, TypeError):
                return default

        def clean_str(val, default=None):
            if val == "Data Not Available" or val is None:
                return default
            return str(val)

        def clean_bool(val, default=True):
            if val == "Data Not Available" or val is None:
                return default
            if isinstance(val, bool):
                return val
            if str(val).lower() in ("true", "1", "yes"):
                return True
            if str(val).lower() in ("false", "0", "no"):
                return False
            return default

        # insert into vendor_quotes including AI-extracted fields (always insert, multiple quotes allowed)
        record = {
            'vendor_id': vendor_id,
            'quote_file_url': public_url,
            'price': clean_numeric(extracted_data.get('price')),
            'delivery_days': clean_int(extracted_data.get('delivery_days')),
            'warranty_years': clean_int(extracted_data.get('warranty_years')),
            'support_level': clean_str(extracted_data.get('support_level')),
            'payment_terms': clean_str(extracted_data.get('payment_terms')),
            'compliance_score': clean_numeric(extracted_data.get('compliance_score')),
            'extracted_json': {
                'raw_text': text,
                'full_ai_result': ai_result,
            },
        }

        # Prepare payload with only the necessary new database columns (avoiding schema bloat)
        db_record = record.copy()
        db_record.update({
            'extraction_confidence_score': clean_numeric(ai_result.get('extraction_confidence_score')),
        })

        # 5) Insert vendor quote record into DB
        try:
            last_step = "db_insert_with_confidence"
            # Defensive coercion for integer fields to avoid Postgres '10.0' parse errors
            try:
                if 'delivery_days' in db_record and db_record['delivery_days'] is not None:
                    v = db_record['delivery_days']
                    if isinstance(v, float):
                        db_record['delivery_days'] = int(v)
                    elif isinstance(v, str) and v.replace('.', '', 1).isdigit():
                        db_record['delivery_days'] = int(float(v))
                if 'warranty_years' in db_record and db_record['warranty_years'] is not None:
                    w = db_record['warranty_years']
                    if isinstance(w, float):
                        db_record['warranty_years'] = int(w)
                    elif isinstance(w, str) and w.replace('.', '', 1).isdigit():
                        db_record['warranty_years'] = int(float(w))
                # ensure extraction_confidence_score is numeric (float)
                if 'extraction_confidence_score' in db_record and db_record['extraction_confidence_score'] is not None:
                    try:
                        db_record['extraction_confidence_score'] = float(db_record['extraction_confidence_score'])
                    except Exception:
                        db_record['extraction_confidence_score'] = None
            except Exception as coercion_err:
                print(f"Warning: coercion step failed: {coercion_err}")

            # Temporary debug logging to help diagnose insert failures
            try:
                print(f"DEBUG: vendor_quotes insert payload: {db_record}")
            except Exception:
                print("DEBUG: vendor_quotes insert payload: <unserializable>")

            resp = client.table('vendor_quotes').insert(db_record).execute()
        except Exception as e:
            error_str = str(e)
            # If confidence column doesn't exist, try inserting core columns
            if "column" in error_str or "does not exist" in error_str or "42703" in error_str:
                print(f"Warning: Confidence column not found, falling back to core columns. Error: {e}")
                last_step = "db_insert_core"
                try:
                    print(f"DEBUG: vendor_quotes fallback insert payload: {record}")
                except Exception:
                    print("DEBUG: vendor_quotes fallback insert payload: <unserializable>")
                resp = client.table('vendor_quotes').insert(record).execute()
            else:
                # Print diagnostics to server logs: exception, traceback, and field types
                print("ERROR: vendor_quotes primary insert failed:", e)
                traceback.print_exc()
                try:
                    print("DEBUG: db_record contents before failing insert:")
                    for k, v in db_record.items():
                        try:
                            print(f" - {k}: value={repr(v)} type={type(v)}")
                        except Exception as field_err:
                            print(f" - {k}: <unserializable> ({field_err})")
                except Exception as dump_err:
                    print(f"Failed to dump db_record: {dump_err}")
                try:
                    dd = db_record.get('delivery_days')
                except Exception:
                    dd = '<unavailable>'
                raise Exception(f"{e} | debug_db_delivery_days={repr(dd)}")

        if not resp.data:
            raise HTTPException(status_code=500, detail='Failed to insert quote record')
        inserted = resp.data[0]
        quote_id = inserted.get('id')

        # Automatically insert or update a contract record in 'contracts' table with the dates
        # 6) Upsert contract record (non-fatal)
        try:
            # Personalize contract name if default was returned
            contract_name = clean_str(extracted_data.get('contract_name'), 'Vendor Agreement')
            if contract_name == "Vendor Agreement":
                current_year = datetime.now().year
                contract_name = f"{vendor_name} Agreement {current_year}"

            contract_payload = {
                "vendor_id": vendor_id,
                "contract_name": contract_name,
                "start_date": clean_str(extracted_data.get("start_date"), today_str),
                "end_date": clean_str(extracted_data.get("end_date")),
                "renewal_date": clean_str(extracted_data.get("renewal_date")),
                "auto_renewal": clean_bool(extracted_data.get("auto_renewal"), True),
                "notice_period_days": clean_int(extracted_data.get("notice_period_days"), 30)
            }

            # Check if vendor already has an existing contract
            existing_contract = client.table("contracts").select("id").eq("vendor_id", vendor_id).execute()
            if existing_contract.data:
                # Update existing contract with new dates and terms
                client.table("contracts").update(contract_payload).eq("vendor_id", vendor_id).execute()
                print(f"Updated contract for vendor {vendor_name}")
            else:
                # Insert a new contract
                client.table("contracts").insert(contract_payload).execute()
                print(f"Created new contract for vendor {vendor_name}")
        except Exception as contract_err:
            print(f"Warning: Failed to save contract record: {contract_err}")

        # Automatically re-run vendor risk analysis to keep the scores and alerts updated
        # 7) Trigger risk analysis (non-fatal)
        try:
            from ..services.risk_service import analyze_vendor_risk
            if background_tasks:
                background_tasks.add_task(analyze_vendor_risk, vendor_id, persist=True)
                print(f"Backgrounded risk analysis for vendor {vendor_id}")
            else:
                await analyze_vendor_risk(vendor_id, persist=True)
                print(f"Automatically updated risk analysis for vendor {vendor_id}")
        except Exception as risk_err:
            print(f"Warning: Failed to auto-update vendor risk analysis: {risk_err}")

        # insert audit log for agent run
        # 8) Insert audit log (non-fatal)
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
        
        except Exception as audit_err:
            print(f"Warning: Failed to insert audit log: {audit_err}")

        return {
            'message': 'Quote uploaded successfully',
            'file_url': public_url,
            'vendor_id': vendor_id,
            'quote_id': quote_id,
            'text_preview': text[:200],
            'extracted_data': extracted_data,
            'validation_status': ai_result.get('validation_status'),
            'duplicate_detection_status': ai_result.get('duplicate_detection_status'),
            'missing_fields': ai_result.get('missing_fields'),
            'normalized_values': ai_result.get('normalized_values'),
            'extraction_confidence_score': ai_result.get('extraction_confidence_score'),
        }
    except HTTPException:
        raise
    except Exception as e:
        # Provide the last step and error message to help debugging
        # Log full traceback/server diagnostics before returning error to client
        print(f"Unhandled exception at step '{last_step}': {e}")
        traceback.print_exc()
        detail_msg = f"Step '{last_step}' failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail_msg)


@router.get("/")
def get_quotes(vendor_id: str = None, procurement_id: str = None):
    client = supabase_service if supabase_service else supabase
    if procurement_id:
        # Fetch vendors for this procurement first
        vendors_resp = client.table("vendors").select("id").eq("procurement_id", procurement_id).execute()
        vendor_ids = [v["id"] for v in (vendors_resp.data or [])]
        if not vendor_ids:
            return []
        result = client.table("vendor_quotes").select("*").in_("vendor_id", vendor_ids).execute()
        return result.data
    elif vendor_id:
        result = client.table("vendor_quotes")\
            .select("*")\
            .eq("vendor_id", vendor_id)\
            .execute()
        return result.data
    return []
