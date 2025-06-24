# Trading Farm AI Services API - Robust Startup Script
# This script sets environment variables and starts the API with additional error handling

# Set environment variables
Write-Host "Setting environment variables..." -ForegroundColor Cyan

# Supabase credentials
$env:SUPABASE_URL = "https://nmzuamwzbjlfhbqbvvpf.supabase.co"
$env:SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tenVhbXd6YmpsZmhicWJ2dnBmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzI1NDMxMCwiZXhwIjoyMDYyODMwMzEwfQ.ZXVBYZv1k81-SvtVZwEwpWhbtBRAhELCtqhedD487yg"

# Market data API keys
$env:COINMARKETCAP_API_KEY = "82006933-7a77-44ad-a876-d96fbb4fcc92"
$env:ALPHA_VANTAGE_API_KEY = "NRT9T3Z2UTBR52VQ"

# JWT authentication
$env:JWT_SECRET = "+IAxvL7arT3N0aLX4jvF/MHd5QaLrjeV0xBiTICk9ezbhNz2qznPKNbCKJHaYk08AvQHawlxuLsDi3VugDJ0DQ=="

# CORS and API configuration
$env:ALLOWED_ORIGINS = "http://localhost:3000,http://localhost:3001,http://localhost:8000"
$env:API_PREFIX = "/api"

# Logging configuration
$env:LOG_LEVEL = "INFO"

Write-Host "Environment variables set successfully!" -ForegroundColor Green

# Verify required Python packages
Write-Host "Verifying required Python packages..." -ForegroundColor Cyan
$requiredPackages = @("fastapi", "uvicorn", "pydantic", "pydantic-settings", "loguru", "supabase", "httpx")

foreach ($package in $requiredPackages) {
    try {
        python -c "import $package"
        Write-Host "  ✓ $package is installed" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ $package is missing. Installing..." -ForegroundColor Yellow
        pip install $package
    }
}

Write-Host "Starting Trading Farm AI API server with stability enhancements..." -ForegroundColor Cyan

# Start the API with enhanced options for stability
python -m uvicorn python_ai_services.api.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120 --limit-concurrency 10 --no-access-log
