from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
from loguru import logger

from ..models.alert_models import (
    AlertConfigInput,
    AlertConfigOutput,
    # AlertUpdateRequest is not explicitly defined in the prompt,
    # but update_alert_config takes Dict[str, Any].
    # For typed partial updates, a separate AlertConfigUpdate model would be good.
)

class AlertConfigurationService:
    def __init__(self):
        self._alerts_configs: Dict[str, AlertConfigOutput] = {} # Key is alert_id
        logger.info("AlertConfigurationService initialized with in-memory storage.")

    async def create_alert_config(self, agent_id: str, config_input: AlertConfigInput) -> AlertConfigOutput:
        alert_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        alert_config = AlertConfigOutput(
            alert_id=alert_id,
            agent_id=agent_id, # Set based on path parameter from route
            created_at=now,
            updated_at=now,
            **config_input.model_dump()
        )
        self._alerts_configs[alert_id] = alert_config
        logger.info(f"Alert config created for agent {agent_id} with ID: {alert_id}, Name: {alert_config.name}")
        return alert_config

    async def get_alert_configs_for_agent(self, agent_id: str, only_enabled: bool = False) -> List[AlertConfigOutput]:
        agent_alerts = [
            config for config in self._alerts_configs.values() if config.agent_id == agent_id
        ]
        if only_enabled:
            agent_alerts = [config for config in agent_alerts if config.is_enabled]

        logger.debug(f"Retrieved {len(agent_alerts)} alert configs for agent {agent_id} (enabled_only={only_enabled}).")
        return agent_alerts

    async def get_alert_config(self, alert_id: str) -> Optional[AlertConfigOutput]:
        config = self._alerts_configs.get(alert_id)
        if config:
            logger.debug(f"Retrieved alert config with ID: {alert_id}")
        else:
            logger.warning(f"Alert config with ID {alert_id} not found.")
        return config

    async def update_alert_config(self, alert_id: str, update_data: Dict[str, Any]) -> Optional[AlertConfigOutput]:
        """
        Updates an existing alert configuration.
        `update_data` is a dictionary of fields to update.
        This method uses Pydantic's update capabilities by creating a new model from existing + updates.
        """
        existing_config = self._alerts_configs.get(alert_id)
        if not existing_config:
            logger.warning(f"Alert config with ID {alert_id} not found for update.")
            return None

        # Create a copy of the existing data dictionary
        updated_config_data = existing_config.model_dump()

        # Selectively update fields from update_data
        # This basic loop is for top-level fields. Nested models like 'conditions' might need more specific handling
        # if individual conditions or their parameters are to be updated patch-style.
        # For now, if 'conditions' is in update_data, it replaces the whole list.
        for key, value in update_data.items():
            if value is not None: # Ensure not to wipe fields with None unless explicitly intended
                 if key in updated_config_data: # Check if key is a valid field of AlertConfigOutput
                    updated_config_data[key] = value

        # Ensure `updated_at` is set
        updated_config_data["updated_at"] = datetime.now(timezone.utc)

        try:
            # Re-validate the updated data by creating a new AlertConfigOutput instance
            # This also handles any validation logic within the Pydantic models
            updated_config = AlertConfigOutput(**updated_config_data)
            self._alerts_configs[alert_id] = updated_config
            logger.info(f"Alert config {alert_id} updated successfully.")
            return updated_config
        except Exception as e: # Catch Pydantic validation errors or other issues
            logger.error(f"Error updating alert config {alert_id}: {e}", exc_info=True)
            # Optionally, revert to existing_config or handle error state
            return None # Indicate update failure


    async def delete_alert_config(self, alert_id: str) -> bool:
        if alert_id in self._alerts_configs:
            del self._alerts_configs[alert_id]
            logger.info(f"Alert config {alert_id} deleted successfully.")
            return True
        logger.warning(f"Alert config {alert_id} not found for deletion.")
        return False

