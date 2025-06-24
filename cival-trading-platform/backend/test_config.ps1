# Sample configuration for testing Trading Farm AI Services API
# Copy this file and update with your actual credentials before running

# API Configuration
$env:HOST = "0.0.0.0"
$env:PORT = "8000"
$env:DEBUG = "True"

# Supabase configuration - REQUIRED
$env:SUPABASE_URL = "https://nmzuamwzbjlfhbqbvvpf.supabase.co"  # Must be a valid HTTPS URL
$env:SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tenVhbXd6YmpsZmhicWJ2dnBmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzI1NDMxMCwiZXhwIjoyMDYyODMwMzEwfQ.ZXVBYZv1k81-SvtVZwEwpWhbtBRAhELCtqhedD487yg"  # Your project's anon/service key

# Market Data API Keys - Optional but recommended for full functionality
$env:COIN_MARKET_CAP_API_KEY = "82006933-7a77-44ad-a876-d96fbb4fcc92"
$env:ALPHA_VANTAGE_API_KEY = "NRT9T3Z2UTBR52VQ"

# CORS Configuration
$env:CORS_ORIGINS = "http://localhost:3000,http://localhost:8000"

# JWT Authentication
$env:JWT_SECRET = "+IAxvL7arT3N0aLX4jvF/MHd5QaLrjeV0xBiTICk9ezbhNz2qznPKNbCKJHaYk08AvQHawlxuLsDi3VugDJ0DQ=="  # Generate a secure random string
$env:JWT_ALGORITHM = "HS256"
$env:JWT_EXPIRES_MINUTES = "60"

# Logging Configuration
$env:LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

Write-Host "Test configuration loaded successfully!" -ForegroundColor Green
Write-Host "NOTE: Update this file with your actual credentials before using" -ForegroundColor Yellow

# Start the API (uncomment to run directly from this file)
# python run_api.py
