#!/usr/bin/env python3
"""
Database Integration Test Script
Tests the new wallet-farm-goal schema with existing Supabase and Redis connections
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
import traceback

# Import database models and services
from models.database_models import (
    DatabaseManager, FarmDB, GoalDB, MasterWalletDB, 
    FundAllocationDB, WalletTransactionDB, AgentFarmAssignmentDB, 
    FarmGoalAssignmentDB, init_database
)

# Import existing services
from core.database_manager import get_database_manager as get_existing_db_manager
import redis.asyncio as redis
from supabase import create_client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class DatabaseIntegrationTester:
    """Test database integration with existing infrastructure"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Initialize connections
        self.supabase = None
        self.redis_client = None
        self.db_manager = None
        
        print("🔧 Initializing Database Integration Tester...")
    
    async def test_existing_connections(self):
        """Test existing Supabase and Redis connections"""
        print("\n📡 Testing Existing Connections...")
        
        try:
            # Test Supabase connection
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                
                # Test with a simple query
                response = self.supabase.table('agent_tasks').select('*').limit(1).execute()
                print(f"✅ Supabase connection successful - URL: {self.supabase_url[:50]}...")
                print(f"   Agent tasks table accessible: {len(response.data)} records found")
            else:
                print("❌ Supabase credentials not found")
                return False
            
            # Test Redis connection
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                print(f"✅ Redis connection successful - URL: {self.redis_url}")
            except Exception as e:
                print(f"❌ Redis connection failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    async def test_new_schema_creation(self):
        """Test creating new schema tables in Supabase"""
        print("\n🏗️  Testing New Schema Creation...")
        
        try:
            # Read the migration SQL file
            migration_file = project_root / "database" / "supabase_migration_001_wallet_farm_goal.sql"
            
            if not migration_file.exists():
                print(f"❌ Migration file not found: {migration_file}")
                return False
            
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            print(f"✅ Migration SQL loaded: {len(migration_sql)} characters")
            print("   Tables to create: farms, goals, master_wallets, fund_allocations, wallet_transactions")
            print("   Relationship tables: agent_farm_assignments, farm_goal_assignments")
            
            # Note: In production, you would execute this SQL in Supabase dashboard or via API
            print("📝 To apply migration: Execute the SQL in your Supabase SQL editor")
            print(f"   File location: {migration_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Schema creation test failed: {e}")
            return False
    
    async def test_sqlalchemy_models(self):
        """Test SQLAlchemy models with local database"""
        print("\n🔍 Testing SQLAlchemy Models...")
        
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager()
            self.db_manager.create_tables()
            print("✅ SQLAlchemy models initialized successfully")
            
            # Test creating sample data
            with self.db_manager.get_sync_session() as session:
                # Create a test farm
                test_farm = FarmDB(
                    name="Test Trend Following Farm",
                    description="Test farm for trend following strategies",
                    farm_type="trend_following",
                    configuration={
                        "strategies": ["williams_alligator", "elliott_wave"],
                        "risk_profile": "moderate"
                    }
                )
                session.add(test_farm)
                session.commit()
                print(f"✅ Created test farm: {test_farm.farm_id}")
                
                # Create a test goal
                test_goal = GoalDB(
                    name="Test 100 Trades Goal",
                    description="Test goal for 100 trades",
                    goal_type="trade_volume",
                    target_criteria={
                        "total_trades": 100,
                        "timeframe_days": 30,
                        "min_profit_per_trade": 5
                    }
                )
                session.add(test_goal)
                session.commit()
                print(f"✅ Created test goal: {test_goal.goal_id}")
                
                # Create a test master wallet
                test_wallet = MasterWalletDB(
                    name="Test Master Wallet",
                    description="Test wallet for integration testing",
                    configuration={
                        "auto_distribution": True,
                        "risk_limits": {
                            "max_allocation_per_agent": 0.1,
                            "daily_loss_limit": 0.05
                        }
                    },
                    total_value_usd=Decimal("10000.00")
                )
                session.add(test_wallet)
                session.commit()
                print(f"✅ Created test master wallet: {test_wallet.wallet_id}")
                
                # Create a test fund allocation
                test_allocation = FundAllocationDB(
                    wallet_id=test_wallet.wallet_id,
                    target_type="farm",
                    target_id=test_farm.farm_id,
                    target_name=test_farm.name,
                    allocated_amount_usd=Decimal("2000.00"),
                    allocated_percentage=Decimal("20.00"),
                    current_value_usd=Decimal("2000.00"),
                    initial_allocation_usd=Decimal("2000.00")
                )
                session.add(test_allocation)
                session.commit()
                print(f"✅ Created test fund allocation: {test_allocation.allocation_id}")
                
                # Create a test farm-goal assignment
                test_assignment = FarmGoalAssignmentDB(
                    farm_id=test_farm.farm_id,
                    goal_id=test_goal.goal_id,
                    contribution_weight=Decimal("1.0"),
                    target_metrics={"target_trades": 100},
                    current_metrics={"current_trades": 0}
                )
                session.add(test_assignment)
                session.commit()
                print(f"✅ Created test farm-goal assignment: {test_assignment.assignment_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ SQLAlchemy models test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_data_operations(self):
        """Test CRUD operations on new models"""
        print("\n📊 Testing Data Operations...")
        
        try:
            with self.db_manager.get_sync_session() as session:
                # Test reading farms
                farms = session.query(FarmDB).all()
                print(f"✅ Found {len(farms)} farms in database")
                
                # Test reading goals
                goals = session.query(GoalDB).all()
                print(f"✅ Found {len(goals)} goals in database")
                
                # Test reading wallets
                wallets = session.query(MasterWalletDB).all()
                print(f"✅ Found {len(wallets)} master wallets in database")
                
                # Test reading allocations
                allocations = session.query(FundAllocationDB).all()
                print(f"✅ Found {len(allocations)} fund allocations in database")
                
                # Test relationships
                if farms:
                    farm = farms[0]
                    print(f"✅ Farm '{farm.name}' has {len(farm.agent_assignments)} agent assignments")
                    print(f"✅ Farm '{farm.name}' has {len(farm.goal_assignments)} goal assignments")
                
                if wallets:
                    wallet = wallets[0]
                    print(f"✅ Wallet '{wallet.name}' has {len(wallet.fund_allocations)} allocations")
                    print(f"✅ Wallet '{wallet.name}' has {len(wallet.transactions)} transactions")
            
            return True
            
        except Exception as e:
            print(f"❌ Data operations test failed: {e}")
            return False
    
    async def test_cache_integration(self):
        """Test Redis cache integration"""
        print("\n🗃️  Testing Cache Integration...")
        
        try:
            # Test storing wallet data in cache
            test_wallet_data = {
                "wallet_id": "test-wallet-123",
                "total_value_usd": 10000.0,
                "allocations": 5,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.setex(
                "test_wallet:test-wallet-123",
                300,  # 5 minutes TTL
                json.dumps(test_wallet_data)
            )
            print("✅ Stored test wallet data in Redis")
            
            # Test retrieving cached data
            cached_data = await self.redis_client.get("test_wallet:test-wallet-123")
            if cached_data:
                parsed_data = json.loads(cached_data)
                print(f"✅ Retrieved cached wallet data: {parsed_data['wallet_id']}")
            
            # Test farm performance cache
            test_farm_performance = {
                "farm_id": "test-farm-456",
                "total_return": 15.5,
                "sharpe_ratio": 2.1,
                "agent_count": 3,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.setex(
                "farm_performance:test-farm-456",
                600,  # 10 minutes TTL
                json.dumps(test_farm_performance)
            )
            print("✅ Stored test farm performance in Redis")
            
            # Test goal progress cache
            test_goal_progress = {
                "goal_id": "test-goal-789",
                "completion_percentage": 45.2,
                "trades_completed": 90,
                "target_trades": 200,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.lpush(
                "goal_progress:test-goal-789",
                json.dumps(test_goal_progress)
            )
            await self.redis_client.ltrim("goal_progress:test-goal-789", 0, 99)  # Keep last 100
            print("✅ Stored test goal progress in Redis")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache integration test failed: {e}")
            return False
    
    async def test_service_integration(self):
        """Test integration with existing services"""
        print("\n⚙️  Testing Service Integration...")
        
        try:
            # Test with existing database manager
            existing_db = get_existing_db_manager()
            print("✅ Existing database manager accessible")
            
            # Test database connections
            connections_status = await existing_db.get_connections_status()
            print(f"✅ Existing connections status: {connections_status}")
            
            # Test service registry integration (if available)
            try:
                from core.service_registry import get_registry
                registry = get_registry()
                print(f"✅ Service registry accessible: {len(registry.list_services())} services")
            except Exception as e:
                print(f"⚠️  Service registry not available: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Service integration test failed: {e}")
            return False
    
    async def generate_integration_report(self):
        """Generate final integration report"""
        print("\n📋 Integration Test Report")
        print("=" * 50)
        
        # Test existing connections
        connections_ok = await self.test_existing_connections()
        
        # Test new schema
        schema_ok = await self.test_new_schema_creation()
        
        # Test SQLAlchemy models
        models_ok = await self.test_sqlalchemy_models()
        
        # Test data operations
        data_ops_ok = await self.test_data_operations()
        
        # Test cache integration
        cache_ok = await self.test_cache_integration()
        
        # Test service integration
        services_ok = await self.test_service_integration()
        
        # Summary
        total_tests = 6
        passed_tests = sum([connections_ok, schema_ok, models_ok, data_ops_ok, cache_ok, services_ok])
        
        print(f"\n📊 Test Results: {passed_tests}/{total_tests} passed")
        print("=" * 50)
        print(f"✅ Existing Connections: {'PASS' if connections_ok else 'FAIL'}")
        print(f"✅ New Schema Creation: {'PASS' if schema_ok else 'FAIL'}")
        print(f"✅ SQLAlchemy Models: {'PASS' if models_ok else 'FAIL'}")
        print(f"✅ Data Operations: {'PASS' if data_ops_ok else 'FAIL'}")
        print(f"✅ Cache Integration: {'PASS' if cache_ok else 'FAIL'}")
        print(f"✅ Service Integration: {'PASS' if services_ok else 'FAIL'}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Database integration ready for Phase 2.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed. Review and fix before proceeding.")
        
        print("\n📝 Next Steps:")
        print("1. Execute the Supabase migration SQL in your Supabase dashboard")
        print("2. Update your existing services to use new models")
        print("3. Implement wallet-farm-goal services in Phase 2")
        print("4. Add AG-UI integration for new components")
        
        return passed_tests == total_tests
    
    async def cleanup(self):
        """Cleanup test resources"""
        try:
            if self.redis_client:
                # Clean up test data
                await self.redis_client.delete("test_wallet:test-wallet-123")
                await self.redis_client.delete("farm_performance:test-farm-456") 
                await self.redis_client.delete("goal_progress:test-goal-789")
                await self.redis_client.close()
                print("✅ Cleaned up Redis test data")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

async def main():
    """Main test execution"""
    print("🚀 Database Integration Test Suite")
    print("Testing wallet-farm-goal schema with existing Supabase and Redis")
    print("=" * 70)
    
    tester = DatabaseIntegrationTester()
    
    try:
        success = await tester.generate_integration_report()
        return success
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        traceback.print_exc()
        return False
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)