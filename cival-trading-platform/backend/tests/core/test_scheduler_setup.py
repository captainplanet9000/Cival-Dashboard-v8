import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED, STATE_RUNNING, STATE_PAUSED


# Functions and objects to test/mock are in scheduler_setup
from python_ai_services.core import scheduler_setup
# To mock the global scheduler object within scheduler_setup module:
# patch('python_ai_services.core.scheduler_setup.scheduler')

# Mock service types for type hinting
from python_ai_services.services.agent_orchestrator_service import AgentOrchestratorService
from python_ai_services.services.alert_monitoring_service import AlertMonitoringService
from python_ai_services.services.agent_management_service import AgentManagementService
from python_ai_services.models.agent_models import AgentConfigOutput # For mock agent data


@pytest_asyncio.fixture
def mock_scheduler():
    """Fixture to mock the global scheduler instance in scheduler_setup module."""
    with patch('python_ai_services.core.scheduler_setup.scheduler', spec=AsyncIOScheduler) as mock_sched:
        # Set initial state for the mock scheduler
        mock_sched.state = STATE_STOPPED
        # Mock 'running' attribute for older check style, though 'state' is better
        type(mock_sched).running = property(fget=lambda self_mock: self_mock.state == STATE_RUNNING)
        yield mock_sched

@pytest_asyncio.fixture
def mock_orchestrator_service():
    service = AsyncMock(spec=AgentOrchestratorService)
    service.run_all_active_agents_once = AsyncMock()
    return service

@pytest_asyncio.fixture
def mock_alert_monitoring_service():
    service = AsyncMock(spec=AlertMonitoringService)
    service.check_and_trigger_alerts_for_agent = AsyncMock()
    return service

@pytest_asyncio.fixture
def mock_agent_management_service():
    service = AsyncMock(spec=AgentManagementService)
    service.get_agents = AsyncMock()
    return service

# --- Tests for scheduling functions ---

def test_schedule_agent_orchestration(mock_scheduler: MagicMock, mock_orchestrator_service: MagicMock):
    mock_scheduler.state = STATE_STOPPED # Ensure scheduler is stopped for job to be added
    scheduler_setup.schedule_agent_orchestration(mock_orchestrator_service, interval_seconds=30)
    mock_scheduler.add_job.assert_called_once_with(
        mock_orchestrator_service.run_all_active_agents_once,
        'interval',
        seconds=30,
        id='agent_orchestration_job',
        replace_existing=True
    )

def test_schedule_agent_orchestration_scheduler_running(mock_scheduler: MagicMock, mock_orchestrator_service: MagicMock):
    mock_scheduler.state = STATE_RUNNING # Simulate scheduler already running
    scheduler_setup.schedule_agent_orchestration(mock_orchestrator_service, interval_seconds=30)
    mock_scheduler.add_job.assert_not_called()


def test_schedule_alert_monitoring(
    mock_scheduler: MagicMock,
    mock_alert_monitoring_service: MagicMock,
    mock_agent_management_service: MagicMock
):
    mock_scheduler.state = STATE_STOPPED
    scheduler_setup.schedule_alert_monitoring(
        mock_alert_monitoring_service,
        mock_agent_management_service,
        interval_seconds=120
    )
    mock_scheduler.add_job.assert_called_once_with(
        scheduler_setup._run_alert_monitoring_for_active_agents,
        'interval',
        seconds=120,
        args=[mock_alert_monitoring_service, mock_agent_management_service],
        id='alert_monitoring_job',
        replace_existing=True
    )

# --- Tests for _run_alert_monitoring_for_active_agents ---

@pytest.mark.asyncio
async def test_run_alert_monitoring_no_active_agents(
    mock_alert_monitoring_service: MagicMock,
    mock_agent_management_service: MagicMock
):
    mock_agent_management_service.get_agents = AsyncMock(return_value=[
        MagicMock(spec=AgentConfigOutput, agent_id="agent1", is_active=False),
        MagicMock(spec=AgentConfigOutput, agent_id="agent2", is_active=False)
    ])

    await scheduler_setup._run_alert_monitoring_for_active_agents(
        mock_alert_monitoring_service, mock_agent_management_service
    )
    mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.assert_not_called()

@pytest.mark.asyncio
async def test_run_alert_monitoring_with_active_agents(
    mock_alert_monitoring_service: MagicMock,
    mock_agent_management_service: MagicMock
):
    active_agent1 = MagicMock(spec=AgentConfigOutput, agent_id="active1", name="Active Agent 1", is_active=True)
    inactive_agent = MagicMock(spec=AgentConfigOutput, agent_id="inactive1", name="Inactive Agent", is_active=False)
    active_agent2 = MagicMock(spec=AgentConfigOutput, agent_id="active2", name="Active Agent 2", is_active=True)
    mock_agent_management_service.get_agents = AsyncMock(return_value=[active_agent1, inactive_agent, active_agent2])

    await scheduler_setup._run_alert_monitoring_for_active_agents(
        mock_alert_monitoring_service, mock_agent_management_service
    )

    assert mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.call_count == 2
    mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.assert_any_call("active1")
    mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.assert_any_call("active2")

@pytest.mark.asyncio
async def test_run_alert_monitoring_agent_check_fails(
    mock_alert_monitoring_service: MagicMock,
    mock_agent_management_service: MagicMock
):
    active_agent1 = MagicMock(spec=AgentConfigOutput, agent_id="ok_agent", name="OK Agent", is_active=True)
    failing_agent = MagicMock(spec=AgentConfigOutput, agent_id="fail_agent", name="Failing Agent", is_active=True)
    mock_agent_management_service.get_agents = AsyncMock(return_value=[active_agent1, failing_agent])

    # Simulate error for one agent's alert check
    async def alert_check_side_effect(agent_id_param):
        if agent_id_param == "fail_agent":
            raise ValueError("Simulated alert check error")
    mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.side_effect = alert_check_side_effect

    # The function should handle the error and continue for other agents
    await scheduler_setup._run_alert_monitoring_for_active_agents(
        mock_alert_monitoring_service, mock_agent_management_service
    )
    assert mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.call_count == 2


@pytest.mark.asyncio
async def test_run_alert_monitoring_get_agents_fails(
    mock_alert_monitoring_service: MagicMock,
    mock_agent_management_service: MagicMock
):
    mock_agent_management_service.get_agents = AsyncMock(side_effect=Exception("Failed to fetch agents"))

    await scheduler_setup._run_alert_monitoring_for_active_agents(
        mock_alert_monitoring_service, mock_agent_management_service
    )
    mock_alert_monitoring_service.check_and_trigger_alerts_for_agent.assert_not_called()


# --- Tests for start_scheduler and shutdown_scheduler ---

def test_start_scheduler_when_stopped(mock_scheduler: MagicMock):
    mock_scheduler.state = STATE_STOPPED
    scheduler_setup.start_scheduler()
    mock_scheduler.start.assert_called_once()

def test_start_scheduler_when_running(mock_scheduler: MagicMock):
    mock_scheduler.state = STATE_RUNNING
    scheduler_setup.start_scheduler()
    mock_scheduler.start.assert_not_called() # Should not call start if already running

def test_start_scheduler_when_paused(mock_scheduler: MagicMock):
    mock_scheduler.state = STATE_PAUSED
    scheduler_setup.start_scheduler() # Should call resume
    mock_scheduler.resume.assert_called_once()
    mock_scheduler.start.assert_not_called()


def test_shutdown_scheduler_when_running(mock_scheduler: MagicMock):
    mock_scheduler.state = STATE_RUNNING
    # Ensure 'running' attribute reflects state for this test of the older check style
    type(mock_scheduler).running = property(fget=lambda self_mock: self_mock.state == STATE_RUNNING)

    scheduler_setup.shutdown_scheduler(wait=False)
    mock_scheduler.shutdown.assert_called_once_with(wait=False)

def test_shutdown_scheduler_when_stopped(mock_scheduler: MagicMock):
    mock_scheduler.state = STATE_STOPPED
    type(mock_scheduler).running = property(fget=lambda self_mock: self_mock.state == STATE_RUNNING)

    scheduler_setup.shutdown_scheduler()
    mock_scheduler.shutdown.assert_not_called() # Should not call shutdown if not running
