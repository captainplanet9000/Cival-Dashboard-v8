from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED, STATE_RUNNING, STATE_PAUSED # For state checking
from typing import TYPE_CHECKING
from loguru import logger
import asyncio # For the test main

if TYPE_CHECKING: # To avoid circular imports for type hints
    from ..services.agent_orchestrator_service import AgentOrchestratorService
    from ..services.alert_monitoring_service import AlertMonitoringService
    from ..services.agent_management_service import AgentManagementService

scheduler = AsyncIOScheduler() # Global scheduler instance

async def _run_alert_monitoring_for_active_agents(
    alert_monitoring_service: 'AlertMonitoringService',
    agent_management_service: 'AgentManagementService'
):
    logger.info("Scheduler: Starting alert monitoring cycle for active agents.")
    try:
        # Assuming get_agents() returns all agents, then we filter for active ones.
        all_agents = await agent_management_service.get_agents()
        active_agents = [agent for agent in all_agents if agent.is_active]

        if not active_agents:
            logger.info("Scheduler: No active agents found for alert monitoring.")
            return

        logger.info(f"Scheduler: Found {len(active_agents)} active agents for alert monitoring.")
        for agent in active_agents:
            try:
                logger.info(f"Scheduler: Running alert checks for agent {agent.agent_id} ({agent.name}).")
                await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent.agent_id)
            except Exception as e_agent_alert:
                logger.error(f"Scheduler: Error during alert check for agent {agent.agent_id}: {e_agent_alert}", exc_info=True)
        logger.info("Scheduler: Finished alert monitoring cycle for active agents.")
    except Exception as e_outer:
        logger.error(f"Scheduler: Error in outer alert monitoring loop: {e_outer}", exc_info=True)


def schedule_agent_orchestration(
    orchestrator_service: 'AgentOrchestratorService',
    interval_seconds: int = 60
):
    # Check scheduler state more reliably
    if scheduler.state == STATE_STOPPED or not scheduler.running: # Check both state and running attribute
        logger.info(f"Scheduling agent orchestration every {interval_seconds} seconds.")
        scheduler.add_job(
            orchestrator_service.run_all_active_agents_once,
            'interval',
            seconds=interval_seconds,
            id='agent_orchestration_job',
            replace_existing=True
        )
    else:
        logger.warning(f"Scheduler already running (state: {scheduler.state}). Orchestration job not added to avoid duplicates.")


def schedule_alert_monitoring(
    alert_monitoring_service: 'AlertMonitoringService',
    agent_management_service: 'AgentManagementService',
    interval_seconds: int = 300
):
    if scheduler.state == STATE_STOPPED or not scheduler.running:
        logger.info(f"Scheduling alert monitoring every {interval_seconds} seconds.")
        scheduler.add_job(
            _run_alert_monitoring_for_active_agents,
            'interval',
            seconds=interval_seconds,
            args=[alert_monitoring_service, agent_management_service],
            id='alert_monitoring_job',
            replace_existing=True
        )
    else:
        logger.warning(f"Scheduler already running (state: {scheduler.state}). Alert monitoring job not added.")

def start_scheduler():
    if scheduler.state == STATE_STOPPED: # Check specific state before starting
        logger.info("Starting APScheduler...")
        try:
            scheduler.start()
            logger.info("APScheduler started successfully.")
        except Exception as e:
            logger.error(f"Failed to start APScheduler: {e}", exc_info=True)
    elif scheduler.state == STATE_RUNNING:
        logger.info("APScheduler is already running.")
    elif scheduler.state == STATE_PAUSED:
        logger.info("APScheduler is paused. Resuming...")
        try:
            scheduler.resume()
            logger.info("APScheduler resumed successfully.")
        except Exception as e:
            logger.error(f"Failed to resume APScheduler: {e}", exc_info=True)


def shutdown_scheduler(wait: bool = True):
    if scheduler.running and scheduler.state != STATE_STOPPED : # Check if it's actually running
        logger.info("Shutting down APScheduler...")
        try:
            scheduler.shutdown(wait=wait)
            logger.info("APScheduler shut down successfully.")
        except Exception as e:
            logger.error(f"Error during APScheduler shutdown: {e}", exc_info=True)
    else:
        logger.info(f"APScheduler is not running (state: {scheduler.state}). No action taken for shutdown.")

# Example of how to use it (for testing or if this module is run directly)
# async def main_test():
#     from unittest.mock import MagicMock, AsyncMock # Need AsyncMock for async methods
#     # Ensure service mocks have async methods if they are called with await
#     mock_orch_service = MagicMock()
#     mock_orch_service.run_all_active_agents_once = AsyncMock()

#     mock_alert_service = MagicMock()
#     mock_alert_service.check_and_trigger_alerts_for_agent = AsyncMock()

#     mock_agent_config = MagicMock()
#     mock_agent_config.agent_id = "test_agent_1"
#     mock_agent_config.name = "Test Agent 1"
#     mock_agent_config.is_active = True

#     mock_agent_service = MagicMock()
#     mock_agent_service.get_agents = AsyncMock(return_value=[mock_agent_config])

#     schedule_agent_orchestration(mock_orch_service, 5)
#     schedule_alert_monitoring(mock_alert_service, mock_agent_service, 10)
#     start_scheduler()
#     try:
#         while True:
#             await asyncio.sleep(1)
#     except KeyboardInterrupt:
#         pass # Allow clean exit
#     finally:
#         shutdown_scheduler()
#         logger.info("Test main finished.")

# if __name__ == "__main__":
#    asyncio.run(main_test())
