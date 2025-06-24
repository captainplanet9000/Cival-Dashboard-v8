#!/usr/bin/env python3
"""
Minimal test to isolate the loguru dependency issue
"""

# Test 1: Import logging
print("Testing standard logging...")
import logging
print("✅ Standard logging works")

# Test 2: Try to import one of our services directly
print("Testing direct service import...")
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Try the most basic import
    print("Importing module...")
    from services.historical_data_service import HistoricalDataService
    print("✅ HistoricalDataService class imported")
    
    # Try factory function
    from services.historical_data_service import create_historical_data_service
    print("✅ Factory function imported")
    
    # Try creating instance
    service = create_historical_data_service()
    print("✅ Service instance created")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()