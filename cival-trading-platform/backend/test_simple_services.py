#!/usr/bin/env python3
"""
Test script for simple services without external dependencies
"""

import sys
import logging
import asyncio
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_simple_services():
    """Test our simple services"""
    logger.info("🧪 Testing simple services...")
    
    try:
        # Test simple historical data service
        from services.simple_historical_data_service import create_simple_historical_data_service
        
        historical_service = create_simple_historical_data_service()
        logger.info("✅ Simple historical data service created")
        
        # Test service methods
        status = await historical_service.get_service_status()
        logger.info(f"✅ Service status: {status['status']}")
        
        # Test getting historical data
        historical_data = await historical_service.get_historical_data('BTC-USD', '1mo')
        if historical_data:
            logger.info(f"✅ Historical data retrieved: {len(historical_data['data'])} data points")
        else:
            logger.warning("⚠️  No historical data returned")
        
        # Test current price
        current_price = await historical_service.get_current_price('BTC-USD')
        if current_price:
            logger.info(f"✅ Current price: ${current_price['price']}")
        else:
            logger.warning("⚠️  No current price returned")
        
        # Test volatility
        volatility = await historical_service.get_volatility('BTC-USD')
        logger.info(f"✅ Volatility: {volatility:.1%}")
        
        # Test supported symbols
        symbols = await historical_service.get_supported_symbols()
        logger.info(f"✅ Supported symbols: {len(symbols)}")
        
        logger.info("🎉 All simple service tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Simple service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting simple service tests...")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"⏰ Test time: {datetime.now(timezone.utc).isoformat()}")
    
    success = await test_simple_services()
    
    if success:
        logger.info("✅ All tests completed successfully!")
        return True
    else:
        logger.error("❌ Tests failed!")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"💥 Test crashed: {e}")
        sys.exit(1)