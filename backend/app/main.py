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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)