from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Procurement AI API",
    description="Backend for AI-driven Procurement Agent",
    version="1.0.0"
)

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .supabase_client import supabase

@app.get("/")
async def root():
    """Health check endpoint to verify the backend is running."""
    return {
        "message": "Procurement AI Backend Running",
        "status": "healthy"
    }

@app.get("/test-supabase")
async def test_supabase():
    """Test endpoint to verify Supabase connectivity and query vendors."""
    try:
        # Querying the 'vendors' table
        response = supabase.table("vendors").select("*").execute()
        
        return {
            "status": "success",
            "data": response.data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Include routers
from .routes import vendors
app.include_router(vendors.router)
from .routes import quote_routes
app.include_router(quote_routes.router)
from .routes import optimization_routes
app.include_router(optimization_routes.router)
from .routes import negotiation_routes
app.include_router(negotiation_routes.router)
from .routes import risk_routes
app.include_router(risk_routes.router)
from .routes import recommendation_routes
app.include_router(recommendation_routes.router)
from .routes import audit_routes
app.include_router(audit_routes.router)
from .routes import procurement_routes
app.include_router(procurement_routes.router)
from .routes import agent_routes
app.include_router(agent_routes.router)

import logging
logger = logging.getLogger("uvicorn.error")

async def run_shadow_market_scout_loop():
    import asyncio
    from .services.risk_service import analyze_vendor_risk
    from .supabase_client import supabase_service, supabase
    client = supabase_service or supabase
    
    while True:
        try:
            logger.info("Shadow Market Scout Background Agent: Initiating 24-hour audit scan...")
            # Fetch all vendors
            vendors_response = client.table("vendors").select("id, vendor_name").execute()
            vendors = vendors_response.data or []
            
            for vendor in vendors:
                vendor_id = vendor.get("id")
                vendor_name = vendor.get("vendor_name")
                if vendor_id:
                    try:
                        logger.info(f"Auditing risks for vendor: {vendor_name} ({vendor_id})...")
                        # Perform risk analysis and persist
                        risk_result = await analyze_vendor_risk(vendor_id, client=client, persist=True)
                        
                        # Write observation to shared memory service
                        from .services.memory_service import write_observation
                        write_observation(
                            key=f"risk_audit_{vendor_id}",
                            value=risk_result,
                            agent="Shadow Market Scout"
                        )
                    except Exception as ve:
                        logger.error(f"Error auditing vendor {vendor_name}: {ve}")
                        
        except Exception as e:
            logger.error(f"Error in Shadow Market Scout loop: {e}")
            
        # Run every 24 hours
        await asyncio.sleep(86400)

@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(run_shadow_market_scout_loop())




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)