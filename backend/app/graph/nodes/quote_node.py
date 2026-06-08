from typing import Dict, Any, List
from ...supabase_client import supabase, supabase_service

def quote_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Graph node to fetch vendors and their associated quotes for a given procurement.
    """
    procurement_id = state.get("procurement_id")
    if not procurement_id:
        return {"vendors": []}

    # Use service role client to bypass RLS
    client = supabase_service if supabase_service else supabase
    
    # 1. Fetch all vendors for procurement_id
    vendor_res = client.table("vendors")\
        .select("*")\
        .eq("procurement_id", procurement_id)\
        .execute()
    
    vendors = vendor_res.data if vendor_res.data else []
    
    # 2. For each vendor, fetch their quotes
    for vendor in vendors:
        vendor_id = vendor.get("id")
        quote_res = client.table("vendor_quotes")\
            .select("*")\
            .eq("vendor_id", vendor_id)\
            .execute()
        
        # 3. Attach quotes to the vendor object
        vendor["quotes"] = quote_res.data if quote_res.data else []

    return {
        "vendors": vendors
    }
