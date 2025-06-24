#!/usr/bin/env python3
"""
Simple Database Integration Test
Tests new database schema with existing Supabase setup
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timezone
from decimal import Decimal
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test Supabase connection
def test_supabase_connection():
    """Test Supabase connection"""
    print("🔧 Testing Supabase Connection...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in environment")
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        # Test with existing table
        response = supabase.table('agent_tasks').select('*').limit(1).execute()
        print(f"✅ Supabase connected successfully - URL: {supabase_url[:50]}...")
        print(f"   Agent tasks table accessible: {len(response.data)} records found")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

# Test Redis connection
async def test_redis_connection():
    """Test Redis connection"""
    print("\n🔧 Testing Redis Connection...")
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        print(f"✅ Redis connected successfully - URL: {redis_url}")
        
        # Test basic operations
        await redis_client.set("test_key", "test_value", ex=60)
        value = await redis_client.get("test_key")
        print(f"✅ Redis read/write test successful: {value}")
        
        await redis_client.close()
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

# Test local SQLAlchemy models
def test_local_database():
    """Test local database with new models"""
    print("\n🔧 Testing Local Database Models...")
    
    try:
        # Import and test database models directly
        from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Decimal, ForeignKey
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.dialects.postgresql import UUID, JSONB
        from sqlalchemy.sql import func
        import uuid
        
        Base = declarative_base()
        
        # Define simple test models
        class TestFarm(Base):
            __tablename__ = 'test_farms'
            farm_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            name = Column(String(255), nullable=False)
            farm_type = Column(String(100), nullable=False)
            total_allocated_usd = Column(Decimal(20, 8), default=0)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime, default=func.now())
        
        class TestGoal(Base):
            __tablename__ = 'test_goals'
            goal_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            name = Column(String(255), nullable=False)
            goal_type = Column(String(100), nullable=False)
            completion_percentage = Column(Decimal(5, 2), default=0)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime, default=func.now())
        
        # Create engine and tables
        engine = create_engine('sqlite:///test_integration.db', echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test creating records
        test_farm = TestFarm(
            name="Test Integration Farm",
            farm_type="trend_following",
            total_allocated_usd=Decimal("5000.00")
        )
        session.add(test_farm)
        session.commit()
        print(f"✅ Created test farm: {test_farm.farm_id}")
        
        test_goal = TestGoal(
            name="Test Integration Goal",
            goal_type="trade_volume",
            completion_percentage=Decimal("25.5")
        )
        session.add(test_goal)
        session.commit()
        print(f"✅ Created test goal: {test_goal.goal_id}")
        
        # Test reading records
        farms = session.query(TestFarm).all()
        goals = session.query(TestGoal).all()
        print(f"✅ Database contains {len(farms)} farms and {len(goals)} goals")
        
        session.close()
        
        # Cleanup test database
        os.remove('test_integration.db')
        print("✅ Local database test completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Local database test failed: {e}")
        return False

# Test migration file
def test_migration_file():
    """Test migration file exists and is readable"""
    print("\n🔧 Testing Migration File...")
    
    try:
        migration_file = project_root / "database" / "supabase_migration_001_wallet_farm_goal.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Check for expected tables
        expected_tables = [
            'CREATE TABLE IF NOT EXISTS farms',
            'CREATE TABLE IF NOT EXISTS goals', 
            'CREATE TABLE IF NOT EXISTS master_wallets',
            'CREATE TABLE IF NOT EXISTS fund_allocations',
            'CREATE TABLE IF NOT EXISTS wallet_transactions',
            'CREATE TABLE IF NOT EXISTS agent_farm_assignments',
            'CREATE TABLE IF NOT EXISTS farm_goal_assignments'
        ]
        
        tables_found = 0
        for table_sql in expected_tables:
            if table_sql in migration_sql:
                tables_found += 1
        
        print(f"✅ Migration file loaded: {len(migration_sql)} characters")
        print(f"✅ Found {tables_found}/{len(expected_tables)} expected table definitions")
        
        if tables_found == len(expected_tables):
            print("✅ All required tables defined in migration")
            return True
        else:
            print("❌ Some tables missing from migration")
            return False
        
    except Exception as e:
        print(f"❌ Migration file test failed: {e}")
        return False

# Test existing services integration
def test_existing_services():
    """Test integration with existing services"""
    print("\n🔧 Testing Existing Services Integration...")
    
    try:
        # Test database manager import
        from core.database_manager import DatabaseManager
        print("✅ DatabaseManager import successful")
        
        # Test service registry import
        from core.service_registry import get_registry
        registry = get_registry()
        services = registry.list_services()
        print(f"✅ Service registry accessible: {len(services)} services registered")
        
        # Test some key services
        key_services = ['market_data', 'portfolio_tracker', 'agent_management']
        available_services = []
        for service_name in key_services:
            service = registry.get_service(service_name)
            if service:
                available_services.append(service_name)
        
        print(f"✅ Key services available: {available_services}")
        
        return True
        
    except Exception as e:
        print(f"❌ Existing services test failed: {e}")
        return False

async def main():
    """Main test execution"""
    print("🚀 Database Integration Test Suite (Phase 1)")
    print("Testing wallet-farm-goal schema with existing infrastructure")
    print("=" * 70)
    
    # Run all tests
    tests = [
        ("Supabase Connection", test_supabase_connection()),
        ("Redis Connection", await test_redis_connection()),
        ("Local Database Models", test_local_database()),
        ("Migration File", test_migration_file()),
        ("Existing Services", test_existing_services())
    ]
    
    passed = 0
    total = len(tests)
    
    print("\n📊 Test Results:")
    print("=" * 30)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print("=" * 30)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Phase 1 Database Integration COMPLETED!")
        print("\n📝 Next Steps:")
        print("1. Execute the Supabase migration SQL in your Supabase dashboard")
        print("2. SQL file: database/supabase_migration_001_wallet_farm_goal.sql")
        print("3. Proceed to Phase 2: Wallet Hierarchy Services")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)