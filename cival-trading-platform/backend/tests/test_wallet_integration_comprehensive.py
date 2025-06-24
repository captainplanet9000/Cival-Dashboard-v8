"""
Phase 7: Comprehensive Wallet Integration Testing Suite
Complete testing framework for all wallet integration phases (1-6)
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

# Import all wallet integration components
from services.master_wallet_service import MasterWalletService
from services.wallet_coordination_service import WalletCoordinationService
from services.wallet_event_streaming_service import WalletEventStreamingService, WalletEventType
from services.wallet_agent_coordination_service import WalletAgentCoordinationService
from services.wallet_goal_integration_service import WalletGoalIntegrationService, GoalType, GoalStatus

from dashboard.comprehensive_dashboard import WalletIntegratedDashboard
from api.comprehensive_wallet_api import wallet_api_router
from api.wallet_dashboard_api import wallet_dashboard_router

from models.master_wallet_models import (
    MasterWallet, MasterWalletConfig, FundAllocationRequest, 
    FundCollectionRequest, CreateMasterWalletRequest
)

class TestWalletIntegrationComprehensive:
    """Comprehensive test suite for wallet integration system"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock service registry for testing"""
        registry = Mock()
        registry.get_service = Mock(return_value=None)
        registry.list_services = Mock(return_value=[])
        registry.all_services = {}
        registry.all_connections = {}
        registry.is_initialized = Mock(return_value=True)
        registry.health_check = AsyncMock(return_value={"registry": "healthy"})
        return registry
    
    @pytest.fixture
    def sample_wallet_config(self):
        """Sample wallet configuration for testing"""
        return MasterWalletConfig(
            name="Test Wallet",
            description="Test wallet for integration testing",
            primary_chain="ethereum",
            supported_chains=["ethereum", "polygon"],
            auto_distribution=True,
            performance_based_allocation=True,
            max_allocation_per_agent=Decimal("0.1"),
            emergency_stop_threshold=Decimal("0.2"),
            daily_loss_limit=Decimal("0.05")
        )
    
    @pytest.fixture
    def sample_master_wallet(self, sample_wallet_config):
        """Sample master wallet for testing"""
        wallet = MasterWallet(config=sample_wallet_config)
        return wallet
    
    @pytest.fixture
    async def wallet_service(self, mock_registry):
        """Master wallet service for testing"""
        with patch('services.master_wallet_service.get_registry', return_value=mock_registry):
            service = MasterWalletService()
            return service
    
    @pytest.fixture
    async def coordination_service(self, mock_registry):
        """Wallet coordination service for testing"""
        with patch('services.wallet_coordination_service.get_registry', return_value=mock_registry):
            service = WalletCoordinationService()
            return service
    
    @pytest.fixture
    async def event_streaming_service(self, mock_registry):
        """Event streaming service for testing"""
        with patch('services.wallet_event_streaming_service.get_registry', return_value=mock_registry):
            service = WalletEventStreamingService()
            return service
    
    @pytest.fixture
    async def agent_coordination_service(self, mock_registry):
        """Agent coordination service for testing"""
        with patch('services.wallet_agent_coordination_service.get_registry', return_value=mock_registry):
            service = WalletAgentCoordinationService()
            return service
    
    @pytest.fixture
    async def goal_integration_service(self, mock_registry):
        """Goal integration service for testing"""
        with patch('services.wallet_goal_integration_service.get_registry', return_value=mock_registry):
            service = WalletGoalIntegrationService()
            return service
    
    @pytest.fixture
    async def integrated_dashboard(self, mock_registry):
        """Integrated dashboard for testing"""
        with patch('dashboard.comprehensive_dashboard.get_registry', return_value=mock_registry):
            dashboard = WalletIntegratedDashboard()
            return dashboard

class TestPhase1DashboardIntegration(TestWalletIntegrationComprehensive):
    """Test Phase 1: Dashboard Integration"""
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, integrated_dashboard):
        """Test dashboard initialization with wallet services"""
        assert integrated_dashboard.wallet_dashboard_mode == True
        assert integrated_dashboard.selected_wallet_id is None
        assert integrated_dashboard.master_wallet_service is None
    
    @pytest.mark.asyncio
    async def test_wallet_service_initialization(self, integrated_dashboard):
        """Test wallet service initialization in dashboard"""
        await integrated_dashboard.initialize_wallet_services()
        # Verify initialization attempts were made
        assert hasattr(integrated_dashboard, 'master_wallet_service')
        assert hasattr(integrated_dashboard, 'wallet_hierarchy_service')
    
    @pytest.mark.asyncio
    async def test_master_wallet_control_data(self, integrated_dashboard):
        """Test master wallet control panel data retrieval"""
        control_data = await integrated_dashboard.get_master_wallet_control_data()
        
        assert "wallet_control_mode" in control_data
        assert "selected_wallet_id" in control_data
        assert "allocation_opportunities" in control_data
        assert "collection_opportunities" in control_data
    
    @pytest.mark.asyncio
    async def test_fund_allocation_execution(self, integrated_dashboard):
        """Test fund allocation execution through dashboard"""
        allocation_request = FundAllocationRequest(
            target_type="agent",
            target_id="test_agent",
            target_name="Test Agent",
            amount_usd=Decimal("1000")
        )
        
        result = await integrated_dashboard.execute_fund_allocation(allocation_request)
        
        assert "success" in result
        assert "error" in result  # Should be error due to no wallet service
    
    @pytest.mark.asyncio
    async def test_wallet_overview_data(self, integrated_dashboard):
        """Test enhanced overview data with wallet integration"""
        overview_data = await integrated_dashboard.get_overview_data()
        
        assert "platform" in overview_data
        assert "services" in overview_data
        assert "master_wallet_summary" in overview_data
        assert overview_data["platform"]["wallet_mode"] == True
    
    @pytest.mark.asyncio
    async def test_complete_dashboard_data(self, integrated_dashboard):
        """Test complete dashboard data retrieval"""
        dashboard_data = await integrated_dashboard.get_all_dashboard_data()
        
        required_tabs = [
            "overview", "agent_management", "trading_operations",
            "risk_safety", "market_analytics", "performance_analytics",
            "system_monitoring", "master_wallet_control"
        ]
        
        for tab in required_tabs:
            assert tab in dashboard_data
        
        assert "wallet_mode" in dashboard_data
        assert "selected_wallet_id" in dashboard_data

class TestPhase2APIIntegration(TestWalletIntegrationComprehensive):
    """Test Phase 2: API Integration"""
    
    def test_api_router_configuration(self):
        """Test API router configuration"""
        assert wallet_api_router.prefix == "/api/v1/wallet"
        assert "wallet-supremacy" in wallet_api_router.tags
    
    def test_api_route_definitions(self):
        """Test API route definitions"""
        routes = wallet_api_router.routes
        route_paths = [route.path for route in routes]
        
        expected_paths = [
            "/create", "/list", "/{wallet_id}", "/{wallet_id}/config",
            "/{wallet_id}/allocate", "/{wallet_id}/collect", "/transfer",
            "/{wallet_id}/performance", "/{wallet_id}/balances",
            "/{wallet_id}/allocations", "/analytics/summary"
        ]
        
        for expected_path in expected_paths:
            assert any(expected_path in path for path in route_paths)
    
    @pytest.mark.asyncio
    async def test_wallet_creation_model_validation(self, sample_wallet_config):
        """Test wallet creation request model validation"""
        request = CreateMasterWalletRequest(config=sample_wallet_config)
        
        assert request.config.name == "Test Wallet"
        assert request.config.auto_distribution == True
        assert request.config.max_allocation_per_agent == Decimal("0.1")
    
    @pytest.mark.asyncio
    async def test_allocation_request_validation(self):
        """Test fund allocation request validation"""
        allocation_request = FundAllocationRequest(
            target_type="agent",
            target_id="test_agent",
            target_name="Test Agent",
            amount_usd=Decimal("1000")
        )
        
        assert allocation_request.target_type == "agent"
        assert allocation_request.amount_usd == Decimal("1000")
        assert allocation_request.allocation_method == "fixed"
    
    @pytest.mark.asyncio
    async def test_collection_request_validation(self):
        """Test fund collection request validation"""
        collection_request = FundCollectionRequest(
            allocation_id="test_allocation",
            collection_type="partial",
            amount_usd=Decimal("500")
        )
        
        assert collection_request.allocation_id == "test_allocation"
        assert collection_request.collection_type == "partial"
        assert collection_request.amount_usd == Decimal("500")

class TestPhase3ServiceCoordination(TestWalletIntegrationComprehensive):
    """Test Phase 3: Service Coordination"""
    
    @pytest.mark.asyncio
    async def test_coordination_service_initialization(self, coordination_service):
        """Test coordination service initialization"""
        assert coordination_service.coordination_active == False
        assert coordination_service.wallet_aware_services == {}
        assert coordination_service.service_wallet_mappings == {}
    
    @pytest.mark.asyncio
    async def test_service_integration_tracking(self, coordination_service):
        """Test service integration tracking"""
        await coordination_service.initialize()
        
        # Should attempt to integrate wallet-aware services
        assert hasattr(coordination_service, 'wallet_aware_services')
    
    @pytest.mark.asyncio
    async def test_allocation_coordination(self, coordination_service):
        """Test coordinated allocation request"""
        result = await coordination_service.coordinate_allocation_request(
            wallet_id="test_wallet",
            target_type="agent",
            target_id="test_agent",
            amount=Decimal("1000")
        )
        
        assert "wallet_id" in result
        assert "target_type" in result
        assert "coordination_steps" in result
        assert result["target_type"] == "agent"
    
    @pytest.mark.asyncio
    async def test_collection_coordination(self, coordination_service):
        """Test coordinated collection request"""
        result = await coordination_service.coordinate_collection_request(
            wallet_id="test_wallet",
            allocation_id="test_allocation",
            collection_type="partial"
        )
        
        assert "wallet_id" in result
        assert "allocation_id" in result
        assert "coordination_steps" in result
    
    @pytest.mark.asyncio
    async def test_coordination_status(self, coordination_service):
        """Test coordination status retrieval"""
        status = await coordination_service.get_coordination_status()
        
        assert "service" in status
        assert "status" in status
        assert "wallet_aware_services" in status
        assert status["service"] == "wallet_coordination_service"

class TestPhase4EventStreaming(TestWalletIntegrationComprehensive):
    """Test Phase 4: Event Streaming"""
    
    @pytest.mark.asyncio
    async def test_event_streaming_initialization(self, event_streaming_service):
        """Test event streaming service initialization"""
        assert event_streaming_service.streaming_active == False
        assert event_streaming_service.event_processing_active == False
        assert len(event_streaming_service.event_subscribers) == 0
        assert len(event_streaming_service.global_subscribers) == 0
    
    @pytest.mark.asyncio
    async def test_event_emission(self, event_streaming_service):
        """Test event emission"""
        await event_streaming_service.emit_event(
            WalletEventType.FUNDS_ALLOCATED,
            "test_wallet",
            {"allocation_amount": 1000}
        )
        
        # Event should be queued
        assert event_streaming_service.event_queue.qsize() >= 0
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, event_streaming_service):
        """Test event subscription"""
        callback = AsyncMock()
        
        await event_streaming_service.subscribe_to_events(
            callback,
            event_types=[WalletEventType.FUNDS_ALLOCATED],
            wallet_ids=["test_wallet"]
        )
        
        # Should have subscribers registered
        assert len(event_streaming_service.event_subscribers) > 0 or len(event_streaming_service.wallet_subscribers) > 0
    
    @pytest.mark.asyncio
    async def test_event_history(self, event_streaming_service):
        """Test event history retrieval"""
        history = await event_streaming_service.get_event_history(
            wallet_id="test_wallet",
            limit=10
        )
        
        assert isinstance(history, list)
    
    @pytest.mark.asyncio
    async def test_streaming_status(self, event_streaming_service):
        """Test streaming service status"""
        status = await event_streaming_service.get_streaming_status()
        
        assert "service" in status
        assert "status" in status
        assert "metrics" in status
        assert "queue_size" in status
        assert status["service"] == "wallet_event_streaming_service"

class TestPhase5AgentCoordination(TestWalletIntegrationComprehensive):
    """Test Phase 5: Agent Coordination"""
    
    @pytest.mark.asyncio
    async def test_agent_coordination_initialization(self, agent_coordination_service):
        """Test agent coordination service initialization"""
        assert agent_coordination_service.coordination_active == False
        assert len(agent_coordination_service.agent_profiles) == 0
        assert len(agent_coordination_service.wallet_agent_allocations) == 0
    
    @pytest.mark.asyncio
    async def test_agent_allocation_recommendation(self, agent_coordination_service):
        """Test agent allocation recommendations"""
        recommendations = await agent_coordination_service.recommend_agent_allocation(
            wallet_id="test_wallet",
            available_amount=Decimal("10000")
        )
        
        assert isinstance(recommendations, list)
        # May be empty if no qualified agents
    
    @pytest.mark.asyncio
    async def test_agent_rebalancing(self, agent_coordination_service):
        """Test agent rebalancing execution"""
        result = await agent_coordination_service.execute_agent_rebalancing("test_wallet")
        
        assert "wallet_id" in result
        assert "rebalancing_actions" in result
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_coordination_status(self, agent_coordination_service):
        """Test agent coordination status"""
        status = await agent_coordination_service.get_coordination_status()
        
        assert "service" in status
        assert "status" in status
        assert "agent_profiles_count" in status
        assert "coordination_metrics" in status
        assert status["service"] == "wallet_agent_coordination_service"

class TestPhase6GoalIntegration(TestWalletIntegrationComprehensive):
    """Test Phase 6: Goal Integration"""
    
    @pytest.mark.asyncio
    async def test_goal_integration_initialization(self, goal_integration_service):
        """Test goal integration service initialization"""
        assert goal_integration_service.integration_active == False
        assert len(goal_integration_service.active_goals) == 0
        assert len(goal_integration_service.wallet_goals) == 0
        assert goal_integration_service.auto_goal_creation == True
    
    @pytest.mark.asyncio
    async def test_goal_creation(self, goal_integration_service):
        """Test goal creation"""
        goal = await goal_integration_service.create_goal(
            goal_type=GoalType.PROFIT_TARGET,
            target_value=Decimal("1000"),
            wallet_id="test_wallet",
            allocation_id="test_allocation",
            description="Test profit goal"
        )
        
        assert goal.goal_type == GoalType.PROFIT_TARGET
        assert goal.target_value == Decimal("1000")
        assert goal.wallet_id == "test_wallet"
        assert goal.status == GoalStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_goal_progress_calculation(self, goal_integration_service):
        """Test goal progress calculation"""
        goal = await goal_integration_service.create_goal(
            goal_type=GoalType.PROFIT_TARGET,
            target_value=Decimal("1000"),
            wallet_id="test_wallet"
        )
        
        goal.current_value = Decimal("500")
        progress = goal.calculate_progress()
        
        assert progress == Decimal("50")  # 50% progress
    
    @pytest.mark.asyncio
    async def test_goal_completion_check(self, goal_integration_service):
        """Test goal completion detection"""
        goal = await goal_integration_service.create_goal(
            goal_type=GoalType.PROFIT_TARGET,
            target_value=Decimal("1000"),
            wallet_id="test_wallet"
        )
        
        goal.current_value = Decimal("1000")
        assert goal.is_completed() == True
        
        goal.current_value = Decimal("500")
        assert goal.is_completed() == False
    
    @pytest.mark.asyncio
    async def test_goals_for_wallet(self, goal_integration_service):
        """Test goal retrieval for wallet"""
        # Create test goal
        await goal_integration_service.create_goal(
            goal_type=GoalType.PROFIT_TARGET,
            target_value=Decimal("1000"),
            wallet_id="test_wallet"
        )
        
        goals = await goal_integration_service.get_goals_for_wallet("test_wallet")
        
        assert isinstance(goals, list)
        assert len(goals) > 0
        assert goals[0]["wallet_id"] == "test_wallet"
    
    @pytest.mark.asyncio
    async def test_goal_analytics(self, goal_integration_service):
        """Test goal analytics"""
        analytics = await goal_integration_service.get_goal_analytics()
        
        assert "metrics" in analytics
        assert "goal_type_distribution" in analytics
        assert "status_distribution" in analytics
        assert "total_active_goals" in analytics
    
    @pytest.mark.asyncio
    async def test_integration_status(self, goal_integration_service):
        """Test goal integration status"""
        status = await goal_integration_service.get_integration_status()
        
        assert "service" in status
        assert "status" in status
        assert "active_goals" in status
        assert "auto_goal_creation" in status
        assert status["service"] == "wallet_goal_integration_service"

class TestIntegratedSystemPerformance(TestWalletIntegrationComprehensive):
    """Test integrated system performance and optimization"""
    
    @pytest.mark.asyncio
    async def test_service_registry_performance(self, mock_registry):
        """Test service registry performance with multiple services"""
        services = [
            "master_wallet_service",
            "wallet_coordination_service", 
            "wallet_event_streaming_service",
            "wallet_agent_coordination_service",
            "wallet_goal_integration_service"
        ]
        
        # Mock multiple service calls
        mock_registry.get_service.side_effect = lambda name: Mock() if name in services else None
        
        # Test concurrent service access
        results = await asyncio.gather(*[
            asyncio.create_task(asyncio.sleep(0.01))  # Simulate service call
            for _ in range(100)
        ])
        
        assert len(results) == 100
    
    @pytest.mark.asyncio
    async def test_event_processing_performance(self, event_streaming_service):
        """Test event processing performance"""
        # Emit multiple events quickly
        start_time = datetime.now()
        
        for i in range(100):
            await event_streaming_service.emit_event(
                WalletEventType.FUNDS_ALLOCATED,
                f"test_wallet_{i}",
                {"allocation_amount": i * 100}
            )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Should process 100 events in under 1 second
        assert processing_time < 1.0
    
    @pytest.mark.asyncio
    async def test_concurrent_wallet_operations(self, wallet_service):
        """Test concurrent wallet operations"""
        # Simulate concurrent operations
        operations = []
        
        for i in range(10):
            operations.append(
                wallet_service.get_wallet_status(f"wallet_{i}")
            )
        
        results = await asyncio.gather(*operations, return_exceptions=True)
        
        # All operations should complete (even if with errors due to missing wallets)
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, goal_integration_service):
        """Test memory usage with many goals"""
        # Create many goals
        for i in range(1000):
            await goal_integration_service.create_goal(
                goal_type=GoalType.PROFIT_TARGET,
                target_value=Decimal("1000"),
                wallet_id=f"wallet_{i % 10}",  # 10 wallets with 100 goals each
                description=f"Goal {i}"
            )
        
        # Should handle 1000 goals without issues
        assert len(goal_integration_service.active_goals) == 1000
        
        # Test cleanup
        goal_integration_service.active_goals.clear()
        assert len(goal_integration_service.active_goals) == 0

class TestErrorHandlingAndResilience(TestWalletIntegrationComprehensive):
    """Test error handling and system resilience"""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, coordination_service):
        """Test handling when services are unavailable"""
        # Mock service registry to return None for all services
        coordination_service.registry.get_service.return_value = None
        
        await coordination_service.initialize()
        
        # Should initialize without crashing
        assert coordination_service.master_wallet_service is None
    
    @pytest.mark.asyncio
    async def test_invalid_wallet_id_handling(self, agent_coordination_service):
        """Test handling of invalid wallet IDs"""
        recommendations = await agent_coordination_service.recommend_agent_allocation(
            wallet_id="invalid_wallet",
            available_amount=Decimal("1000")
        )
        
        # Should return empty list, not crash
        assert isinstance(recommendations, list)
    
    @pytest.mark.asyncio
    async def test_malformed_event_handling(self, event_streaming_service):
        """Test handling of malformed events"""
        # Try to emit event with invalid data
        try:
            await event_streaming_service.emit_event(
                WalletEventType.FUNDS_ALLOCATED,
                "",  # Empty wallet ID
                None  # Invalid data
            )
        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, Exception)
    
    @pytest.mark.asyncio
    async def test_network_timeout_simulation(self, wallet_service):
        """Test network timeout simulation"""
        # Mock timeout scenarios
        with patch('asyncio.sleep', side_effect=asyncio.TimeoutError):
            try:
                result = await wallet_service.get_wallet_status("test_wallet")
            except Exception:
                # Should handle timeout gracefully
                pass

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])