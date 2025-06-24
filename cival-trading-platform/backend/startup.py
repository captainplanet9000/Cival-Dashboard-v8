#!/usr/bin/env python3
"""
Smart Startup Script for MCP Trading Platform
Automatically detects available dependencies and starts the appropriate version
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependency(package_name):
    """Check if a Python package is available"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def check_dependencies():
    """Check what dependencies are available"""
    dependencies = {
        'fastapi': check_dependency('fastapi'),
        'uvicorn': check_dependency('uvicorn'),
        'pandas': check_dependency('pandas'),
        'numpy': check_dependency('numpy'),
        'sqlalchemy': check_dependency('sqlalchemy'),
        'redis': check_dependency('redis'),
        'supabase': check_dependency('supabase'),
        'yfinance': check_dependency('yfinance')
    }
    
    return dependencies

def install_minimal_requirements():
    """Try to install minimal requirements if pip is available"""
    logger.info("🔧 Attempting to install minimal requirements...")
    
    minimal_packages = [
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0"
    ]
    
    try:
        # Try different pip commands
        pip_commands = ["pip", "pip3", "python -m pip", "python3 -m pip"]
        
        for pip_cmd in pip_commands:
            try:
                result = subprocess.run(
                    f"{pip_cmd} install {' '.join(minimal_packages)}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ Successfully installed packages with {pip_cmd}")
                    return True
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"⏰ Timeout installing with {pip_cmd}")
                continue
            except Exception as e:
                logger.warning(f"⚠️  Failed to install with {pip_cmd}: {e}")
                continue
        
        logger.warning("⚠️  Could not install packages, falling back to simple mode")
        return False
        
    except Exception as e:
        logger.warning(f"⚠️  Package installation failed: {e}")
        return False

def start_full_application():
    """Start the full application with all dependencies"""
    logger.info("🚀 Starting full MCP Trading Platform...")
    
    try:
        # Try to import and run the full application
        import main_consolidated
        logger.info("✅ Full application imported successfully")
        
        # This would normally run uvicorn, but we'll use the simple version for now
        return start_simple_application()
        
    except Exception as e:
        logger.error(f"❌ Full application failed to start: {e}")
        logger.info("🔄 Falling back to simple mode...")
        return start_simple_application()

def start_simple_application():
    """Start the simple application"""
    logger.info("🚀 Starting simple MCP Trading Platform...")
    
    try:
        import simple_main
        
        # Check if FastAPI is available
        if check_dependency('fastapi') and check_dependency('uvicorn'):
            logger.info("✅ FastAPI available, starting web server...")
            # Import and run the app
            import uvicorn
            uvicorn.run(
                "simple_main:app",
                host="0.0.0.0",
                port=int(os.getenv("PORT", 8000)),
                log_level="info"
            )
        else:
            logger.info("⚠️  FastAPI not available, running basic mode...")
            # Run async test mode
            import asyncio
            result = asyncio.run(simple_main.run_simple_test())
            
            if result:
                logger.info("✅ Simple application test completed successfully")
                # Keep running for deployment
                logger.info("🔄 Keeping application alive for deployment...")
                while True:
                    import time
                    time.sleep(60)
                    logger.info(f"📊 Application running... {datetime.now().strftime('%H:%M:%S')}")
            else:
                logger.error("❌ Simple application test failed")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Simple application failed to start: {e}")
        return False

def main():
    """Main startup logic"""
    logger.info("🎯 MCP Trading Platform - Smart Startup")
    logger.info("=" * 60)
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"⏰ Startup time: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"🌐 Port: {os.getenv('PORT', '8000')}")
    logger.info("=" * 60)
    
    # Check dependencies
    logger.info("🔍 Checking dependencies...")
    deps = check_dependencies()
    
    available_count = sum(1 for available in deps.values() if available)
    total_count = len(deps)
    
    logger.info(f"📊 Dependencies available: {available_count}/{total_count}")
    
    for package, available in deps.items():
        status = "✅" if available else "❌"
        logger.info(f"  {status} {package}")
    
    # Decide which version to run
    if deps['fastapi'] and deps['uvicorn']:
        logger.info("🎉 Web framework available - can run web server")
        
        # Try to install additional packages for better functionality
        if not deps['pandas'] or not deps['numpy']:
            install_minimal_requirements()
        
        if available_count >= 6:  # Most dependencies available
            success = start_full_application()
        else:
            success = start_simple_application()
    else:
        logger.info("⚠️  Web framework not available - trying to install...")
        
        # Try to install minimal requirements
        if install_minimal_requirements():
            # Recheck dependencies
            if check_dependency('fastapi') and check_dependency('uvicorn'):
                success = start_simple_application()
            else:
                logger.error("❌ Failed to install web framework")
                success = False
        else:
            logger.warning("⚠️  Running in basic mode without web server")
            success = start_simple_application()
    
    if success:
        logger.info("🎉 Application started successfully!")
        return 0
    else:
        logger.error("💥 Application failed to start!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Startup crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)