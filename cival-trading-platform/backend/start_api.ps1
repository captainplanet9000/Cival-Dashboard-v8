# PowerShell script to start the Trading Farm AI Services API
Write-Host "Starting Trading Farm AI Services API..."

# Set environment variables for the API
$env:HOST = "0.0.0.0"
$env:PORT = "8000"
$env:DEBUG = "True"

# These should be set to your actual values     
# Supabase configuration
$env:SUPABASE_URL = "https://nmzuamwzbjlfhbqbvvpf.supabase.co"  # Must be a valid HTTPS URL
$env:SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tenVhbXd6YmpsZmhicWJ2dnBmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzI1NDMxMCwiZXhwIjoyMDYyODMwMzEwfQ.ZXVBYZv1k81-SvtVZwEwpWhbtBRAhELCtqhedD487yg"  # Your project's anon/service key

# Market Data API Keys
$env:COINMARKETCAP_API_KEY = "82006933-7a77-44ad-a876-d96fbb4fcc92"  # No underscores in variable name
$env:ALPHA_VANTAGE_API_KEY = "NRT9T3Z2UTBR52VQ"

# CORS Configuration
$env:CORS_ORIGINS = "http://localhost:3000,http://localhost:8000"  # Adjust based on your frontend URLs

# JWT Authentication
$env:JWT_SECRET = "+IAxvL7arT3N0aLX4jvF/MHd5QaLrjeV0xBiTICk9ezbhNz2qznPKNbCKJHaYk08AvQHawlxuLsDi3VugDJ0DQ=="     # Replace with a secure random string
$env:JWT_ALGORITHM = "HS256"              # JWT algorithm
$env:JWT_EXPIRES_MINUTES = "60"           # Token expiry in minutes

# Logging Configuration
$env:LOG_LEVEL = "INFO"                   # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Write a message to show environment is set up
Write-Host "Environment variables set successfully!" -ForegroundColor Green
Write-Host "Starting Trading Farm AI API server..." -ForegroundColor Cyan

# Start the API
python run_api.py
