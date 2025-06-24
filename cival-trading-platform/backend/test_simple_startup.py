#!/usr/bin/env python3
"""
Simple test script to verify our core services can be imported and instantiated
"""

import sys
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_service_imports():
    """Test importing our core services"""
    logger.info("🔍 Testing service imports...")
    
    try:
        # Test importing factory functions
        from services.historical_data_service import create_historical_data_service
        logger.info("✅ HistoricalDataService import successful")
        
        from services.trading_engine_service import create_trading_engine_service  
        logger.info("✅ TradingEngineService import successful")
        
        from services.order_management_service import create_order_management_service
        logger.info("✅ OrderManagementService import successful")
        
        from services.portfolio_tracker_service import create_portfolio_tracker_service
        logger.info("✅ PortfolioTrackerService import successful")
        
        from services.ai_prediction_service import create_ai_prediction_service
        logger.info("✅ AIPredictionService import successful")
        
        from services.technical_analysis_service import create_technical_analysis_service
        logger.info("✅ TechnicalAnalysisService import successful")
        
        from services.sentiment_analysis_service import create_sentiment_analysis_service
        logger.info("✅ SentimentAnalysisService import successful")
        
        from services.ml_portfolio_optimizer_service import create_ml_portfolio_optimizer_service
        logger.info("✅ MLPortfolioOptimizerService import successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Service import failed: {e}")
        return False

def test_service_creation():
    """Test creating service instances"""
    logger.info("🏗️  Testing service creation...")
    
    try:
        from services.historical_data_service import create_historical_data_service
        from services.trading_engine_service import create_trading_engine_service
        from services.order_management_service import create_order_management_service
        from services.portfolio_tracker_service import create_portfolio_tracker_service
        from services.ai_prediction_service import create_ai_prediction_service
        from services.technical_analysis_service import create_technical_analysis_service
        from services.sentiment_analysis_service import create_sentiment_analysis_service
        from services.ml_portfolio_optimizer_service import create_ml_portfolio_optimizer_service
        
        # Create service instances
        services = {}
        services['historical_data'] = create_historical_data_service()
        logger.info("✅ HistoricalDataService created")
        
        services['trading_engine'] = create_trading_engine_service()
        logger.info("✅ TradingEngineService created")
        
        services['order_management'] = create_order_management_service()
        logger.info("✅ OrderManagementService created")
        
        services['portfolio_tracker'] = create_portfolio_tracker_service()
        logger.info("✅ PortfolioTrackerService created")
        
        services['ai_prediction'] = create_ai_prediction_service()
        logger.info("✅ AIPredictionService created")
        
        services['technical_analysis'] = create_technical_analysis_service()
        logger.info("✅ TechnicalAnalysisService created")
        
        services['sentiment_analysis'] = create_sentiment_analysis_service()
        logger.info("✅ SentimentAnalysisService created")
        
        services['ml_portfolio_optimizer'] = create_ml_portfolio_optimizer_service()
        logger.info("✅ MLPortfolioOptimizerService created")
        
        logger.info(f"📊 Total services created: {len(services)}")
        return services
        
    except Exception as e:
        logger.error(f"❌ Service creation failed: {e}")
        return None

async def test_service_methods():
    """Test basic service methods"""
    logger.info("🧪 Testing service methods...")
    
    try:
        from services.historical_data_service import create_historical_data_service
        
        # Test historical data service
        historical_service = create_historical_data_service()
        status = await historical_service.get_service_status()
        logger.info(f"✅ Historical data service status: {status}")
        
        # Test AI prediction service
        from services.ai_prediction_service import create_ai_prediction_service
        ai_service = create_ai_prediction_service()
        prediction = await ai_service.get_price_prediction('BTC-USD')
        logger.info(f"✅ AI prediction test: {prediction.get('symbol', 'N/A')}")
        
        # Test portfolio tracker
        from services.portfolio_tracker_service import create_portfolio_tracker_service
        portfolio_service = create_portfolio_tracker_service()
        summary = await portfolio_service.get_portfolio_summary()
        logger.info(f"✅ Portfolio summary test: {summary.get('total_equity', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Service method test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting simple service test...")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"⏰ Test time: {datetime.now(timezone.utc).isoformat()}")
    
    # Test 1: Service imports
    import_success = test_service_imports()
    if not import_success:
        logger.error("❌ Import test failed, stopping...")
        return False
    
    # Test 2: Service creation
    services = test_service_creation()
    if not services:
        logger.error("❌ Service creation test failed, stopping...")
        return False
    
    # Test 3: Service methods
    method_success = await test_service_methods()
    if not method_success:
        logger.error("❌ Service method test failed, stopping...")
        return False
    
    logger.info("🎉 All tests passed! Core services are working.")
    return True

if __name__ == "__main__":
    import asyncio
    
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Test completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Test failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Test crashed: {e}")
        sys.exit(1)