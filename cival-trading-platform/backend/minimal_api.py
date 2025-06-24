"""
Minimal FastAPI server for diagnosing issues with the Trading Farm API.
This file creates a standalone API server with only the essential components.
"""

import os
from fastapi import FastAPI
import uvicorn

# Create a simple FastAPI app
app = FastAPI(
    title="Trading Farm Minimal API",
    description="Minimal API server for debugging",
    version="1.0.0"
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "message": "Minimal API server is running"
    }

# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Log startup event"""
    print("Starting Minimal Trading Farm API")

# Shutdown event handler
@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown event"""
    print("Shutting down Minimal Trading Farm API")

# Run the server if executed directly
if __name__ == "__main__":
    # Set environment variables that might be needed
    os.environ["SUPABASE_URL"] = "https://nmzuamwzbjlfhbqbvvpf.supabase.co"
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tenVhbXd6YmpsZmhicWJ2dnBmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzI1NDMxMCwiZXhwIjoyMDYyODMwMzEwfQ.ZXVBYZv1k81-SvtVZwEwpWhbtBRAhELCtqhedD487yg"
    
    print("Starting minimal API server on port 8050...")
    
    # Run the API with debug settings and a different port
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8050,
        log_level="debug"
    )
