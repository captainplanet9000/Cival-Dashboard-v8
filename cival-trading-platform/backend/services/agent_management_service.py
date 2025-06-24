from typing import Dict, List, Optional, Any, Callable, Literal # Added Literal
from datetime import datetime, timezone
import uuid
import json
from sqlalchemy.orm import Session

from ..models.agent_models import (
    AgentConfigInput,
    AgentConfigOutput,
    AgentUpdateRequest,
    AgentStatus,
    AgentStrategyConfig,
    AgentRiskConfig
)
from ..models.db_models import AgentConfigDB
from loguru import logger

class AgentManagementService:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory
        self._agent_statuses: Dict[str, AgentStatus] = {}
        logger.info("AgentManagementService initialized with DB session factory.")
        # _load_existing_statuses_from_db should be called from an async context, e.g., app startup.

    async def _load_existing_statuses_from_db(self):
        logger.info("Loading existing agent statuses from database...")
        db: Session = self.session_factory()
        try:
            db_agents_query = db.query(AgentConfigDB.agent_id, AgentConfigDB.updated_at, AgentConfigDB.is_active)
            db_agents = db_agents_query.all()
            for agent_id_val, updated_at_val, is_active_val in db_agents:
                if agent_id_val not in self._agent_statuses:
                    self._agent_statuses[agent_id_val] = AgentStatus(
                        agent_id=agent_id_val,
                        status="stopped",
                        last_heartbeat=updated_at_val
                    )
            logger.info(f"Initialized/checked statuses for {len(db_agents)} agents from DB (all set to 'stopped' initially).")
        except Exception as e:
            logger.error(f"Error loading existing agent statuses from DB: {e}", exc_info=True)
        finally:
            db.close()

    async def load_all_agent_statuses_from_db(self) -> None:
        """Public wrapper to initialize in-memory agent statuses from the database."""
        await self._load_existing_statuses_from_db()
        logger.info(
            f"Loaded agent runtime statuses for {len(self._agent_statuses)} agents from DB."
        )

    def _db_to_pydantic(self, db_agent: AgentConfigDB) -> AgentConfigOutput:
        try:
            strategy_data = json.loads(db_agent.strategy_config_json or "{}")
            if 'darvas_params' in strategy_data and strategy_data['darvas_params'] and isinstance(strategy_data['darvas_params'], dict):
                strategy_data['darvas_params'] = AgentStrategyConfig.DarvasStrategyParams(**strategy_data['darvas_params'])
            if 'williams_alligator_params' in strategy_data and strategy_data['williams_alligator_params'] and isinstance(strategy_data['williams_alligator_params'], dict):
                strategy_data['williams_alligator_params'] = AgentStrategyConfig.WilliamsAlligatorParams(**strategy_data['williams_alligator_params'])
            # Added for MarketConditionClassifierParams
            if 'market_condition_classifier_params' in strategy_data and strategy_data['market_condition_classifier_params'] and isinstance(strategy_data['market_condition_classifier_params'], dict):
                strategy_data['market_condition_classifier_params'] = AgentStrategyConfig.MarketConditionClassifierParams(**strategy_data['market_condition_classifier_params'])
            # Added for PortfolioOptimizerParams
            if 'portfolio_optimizer_params' in strategy_data and strategy_data['portfolio_optimizer_params'] and isinstance(strategy_data['portfolio_optimizer_params'], dict):
                 # PortfolioOptimizerParams contains a list of PortfolioOptimizerRule
                rules_data = strategy_data['portfolio_optimizer_params'].get('rules', [])
                parsed_rules = [AgentStrategyConfig.PortfolioOptimizerRule(**rule) for rule in rules_data]
                strategy_data['portfolio_optimizer_params'] = AgentStrategyConfig.PortfolioOptimizerParams(rules=parsed_rules)

            strategy_config = AgentStrategyConfig(**strategy_data)
        except (json.JSONDecodeError, TypeError) as e_strat:
            logger.error(f"Error deserializing strategy_config_json for agent {db_agent.agent_id}: {e_strat}. Data: '{db_agent.strategy_config_json}'")
            strategy_config = AgentStrategyConfig(strategy_name="ERROR_DESERIALIZING", parameters={}, watched_symbols=[])

        try:
            risk_conf_dict = json.loads(db_agent.risk_config_json or "{}")
            risk_config = AgentRiskConfig(**risk_conf_dict)
        except (json.JSONDecodeError, TypeError) as e_risk:
            logger.error(f"Error deserializing risk_config_json for agent {db_agent.agent_id}: {e_risk}. Data: '{db_agent.risk_config_json}'")
            risk_config = AgentRiskConfig(max_capital_allocation_usd=0, risk_per_trade_percentage=0.01)

        try:
            hyperliquid_conf = json.loads(db_agent.hyperliquid_config_json) if db_agent.hyperliquid_config_json else None
        except json.JSONDecodeError as e_hl:
            logger.error(f"Error deserializing hyperliquid_config_json for agent {db_agent.agent_id}: {e_hl}. Data: '{db_agent.hyperliquid_config_json}'")
            hyperliquid_conf = None

        try:
            op_params = json.loads(db_agent.operational_parameters_json or "{}")
        except json.JSONDecodeError as e_op:
            logger.error(f"Error deserializing operational_parameters_json for agent {db_agent.agent_id}: {e_op}. Data: '{db_agent.operational_parameters_json}'")
            op_params = {}

        return AgentConfigOutput(
            agent_id=db_agent.agent_id, name=db_agent.name, description=db_agent.description,
            agent_type=db_agent.agent_type, parent_agent_id=db_agent.parent_agent_id,
            is_active=db_agent.is_active, strategy=strategy_config, risk_config=risk_config,
            hyperliquid_config=hyperliquid_conf, operational_parameters=op_params,
            created_at=db_agent.created_at, updated_at=db_agent.updated_at
        )

    async def create_agent(self, agent_input: AgentConfigInput) -> AgentConfigOutput:
        logger.info(f"Attempting to create agent with name: {agent_input.name} in DB.")
        agent_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        pydantic_agent = AgentConfigOutput(
            agent_id=agent_id, created_at=now, updated_at=now, is_active=False,
            **agent_input.model_dump()
        )

        db_agent = AgentConfigDB(
            agent_id=pydantic_agent.agent_id, name=pydantic_agent.name, description=pydantic_agent.description,
            agent_type=pydantic_agent.agent_type, parent_agent_id=pydantic_agent.parent_agent_id,
            is_active=pydantic_agent.is_active,
            strategy_config_json=pydantic_agent.strategy.model_dump_json(),
            risk_config_json=pydantic_agent.risk_config.model_dump_json(),
            hyperliquid_config_json=json.dumps(pydantic_agent.hyperliquid_config) if pydantic_agent.hyperliquid_config else None,
            operational_parameters_json=json.dumps(pydantic_agent.operational_parameters or {}),
            created_at=pydantic_agent.created_at, updated_at=pydantic_agent.updated_at
        )

        db: Session = self.session_factory()
        try:
            db.add(db_agent)
            db.commit()
            db.refresh(db_agent)
            logger.info(f"Agent created successfully in DB with ID: {agent_id}")
            self._agent_statuses[agent_id] = AgentStatus(agent_id=agent_id, status="stopped", last_heartbeat=now)
            return self._db_to_pydantic(db_agent)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating agent {agent_id} in DB: {e}", exc_info=True)
            raise
        finally:
            db.close()

    async def get_agents(self) -> List[AgentConfigOutput]:
        logger.debug("Retrieving all agents from DB.")
        db: Session = self.session_factory()
        try:
            db_agents = db.query(AgentConfigDB).all()
            return [self._db_to_pydantic(db_agent) for db_agent in db_agents]
        finally:
            db.close()

    async def get_agent(self, agent_id: str) -> Optional[AgentConfigOutput]:
        logger.debug(f"Attempting to retrieve agent with ID: {agent_id} from DB.")
        db: Session = self.session_factory()
        try:
            db_agent = db.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
            return self._db_to_pydantic(db_agent) if db_agent else None
        finally:
            db.close()

    async def update_agent(self, agent_id: str, update_data: AgentUpdateRequest) -> Optional[AgentConfigOutput]:
        logger.info(f"Attempting to update agent with ID: {agent_id} in DB.")
        db: Session = self.session_factory()
        try:
            db_agent = db.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
            if not db_agent:
                logger.warning(f"Agent with ID {agent_id} not found in DB for update.")
                return None

            pydantic_agent_current = self._db_to_pydantic(db_agent) # Current state as Pydantic model
            update_payload_dict = update_data.model_dump(exclude_unset=True) # Changes from request

            # Create a dictionary from the current Pydantic model to apply updates
            current_agent_dict = pydantic_agent_current.model_dump()

            # Merge strategy (includes merging nested Darvas/Alligator/MCC/Optimizer params if provided)
            if 'strategy' in update_payload_dict and update_payload_dict['strategy'] is not None:
                current_strategy_dict = current_agent_dict.get('strategy', {})
                new_strategy_data = update_payload_dict['strategy'] # This is a dict

                # Parameters within strategy
                if 'parameters' in new_strategy_data and isinstance(current_strategy_dict.get('parameters'), dict):
                    current_strategy_dict['parameters'].update(new_strategy_data['parameters'])

                # Specific typed strategy params (darvas_params, etc.)
                for param_key in ['darvas_params', 'williams_alligator_params', 'market_condition_classifier_params', 'portfolio_optimizer_params']:
                    if param_key in new_strategy_data and new_strategy_data[param_key] is not None:
                        if isinstance(current_strategy_dict.get(param_key), dict) and isinstance(new_strategy_data[param_key], dict):
                            current_strategy_dict[param_key].update(new_strategy_data[param_key])
                        else: # Overwrite if not dict or not existing
                             current_strategy_dict[param_key] = new_strategy_data[param_key]

                # Update other top-level fields within strategy
                for key, value in new_strategy_data.items():
                    if key not in ['parameters', 'darvas_params', 'williams_alligator_params', 'market_condition_classifier_params', 'portfolio_optimizer_params']:
                        current_strategy_dict[key] = value
                current_agent_dict['strategy'] = current_strategy_dict

            if 'risk_config' in update_payload_dict and update_payload_dict['risk_config'] is not None:
                 current_risk_config_dict = current_agent_dict.get('risk_config', {})
                 current_risk_config_dict.update(update_payload_dict['risk_config'])
                 current_agent_dict['risk_config'] = current_risk_config_dict

            if 'operational_parameters' in update_payload_dict and update_payload_dict['operational_parameters'] is not None:
                current_op_params = current_agent_dict.get('operational_parameters', {})
                current_op_params.update(update_payload_dict['operational_parameters'])
                current_agent_dict['operational_parameters'] = current_op_params

            # Update other top-level fields from AgentUpdateRequest (like name, description, is_active, etc.)
            for key, value in update_payload_dict.items():
                if key not in ['strategy', 'operational_parameters', 'risk_config']: # Already handled
                    current_agent_dict[key] = value

            current_agent_dict['updated_at'] = datetime.now(timezone.utc)
            updated_pydantic_agent = AgentConfigOutput(**current_agent_dict) # Validate and get full model

            # Update DB record from the validated Pydantic model
            db_agent.name = updated_pydantic_agent.name
            db_agent.description = updated_pydantic_agent.description
            db_agent.agent_type = updated_pydantic_agent.agent_type
            db_agent.parent_agent_id = updated_pydantic_agent.parent_agent_id
            db_agent.is_active = updated_pydantic_agent.is_active # Persist is_active
            db_agent.strategy_config_json = updated_pydantic_agent.strategy.model_dump_json()
            db_agent.risk_config_json = updated_pydantic_agent.risk_config.model_dump_json()
            db_agent.hyperliquid_config_json = json.dumps(updated_pydantic_agent.hyperliquid_config) if updated_pydantic_agent.hyperliquid_config else None
            db_agent.operational_parameters_json = json.dumps(updated_pydantic_agent.operational_parameters or {})
            db_agent.updated_at = updated_pydantic_agent.updated_at

            # If 'is_active' was part of the update and changed the state:
            if 'is_active' in update_payload_dict and pydantic_agent_current.is_active != updated_pydantic_agent.is_active:
                new_is_active_state = updated_pydantic_agent.is_active
                logger.info(f"Agent {agent_id} 'is_active' state changed from {pydantic_agent_current.is_active} to {new_is_active_state} by update_agent.")
                new_runtime_status_str: Literal["running", "stopped"] = "running" if new_is_active_state else "stopped"
                current_mem_status = self._agent_statuses.get(agent_id)
                if not current_mem_status or current_mem_status.status != new_runtime_status_str:
                    self._agent_statuses[agent_id] = AgentStatus(
                        agent_id=agent_id, status=new_runtime_status_str,
                        message=f"Set to {new_runtime_status_str} by update_agent.",
                        last_heartbeat=datetime.now(timezone.utc)
                    )
                    logger.info(f"In-memory status for agent {agent_id} updated to '{new_runtime_status_str}'.")
                elif current_mem_status and current_mem_status.status == new_runtime_status_str:
                     current_mem_status.last_heartbeat = datetime.now(timezone.utc)
                     self._agent_statuses[agent_id] = current_mem_status
                     logger.debug(f"In-memory status for agent {agent_id} already '{new_runtime_status_str}', heartbeat updated.")

            db.commit()
            db.refresh(db_agent)
            logger.info(f"Agent {agent_id} updated successfully in DB.")
            return self._db_to_pydantic(db_agent)
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating agent {agent_id} in DB: {e}", exc_info=True)
            return None
        finally:
            db.close()

    async def delete_agent(self, agent_id: str) -> bool:
        logger.info(f"Attempting to delete agent with ID: {agent_id} from DB.")
        db: Session = self.session_factory()
        try:
            db_agent = db.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
            if db_agent:
                db.delete(db_agent)
                db.commit()
                if agent_id in self._agent_statuses: del self._agent_statuses[agent_id]
                logger.info(f"Agent {agent_id} deleted successfully from DB.")
                return True
            logger.warning(f"Agent {agent_id} not found in DB for deletion.")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting agent {agent_id} from DB: {e}", exc_info=True)
            return False
        finally:
            db.close()

    async def start_agent(self, agent_id: str) -> AgentStatus:
        logger.info(f"Attempting to start agent with ID: {agent_id}")
        db: Session = self.session_factory()
        try:
            db_agent = db.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
            if not db_agent:
                raise ValueError(f"Agent with ID {agent_id} not found.")
            db_agent.is_active = True
            db_agent.updated_at = datetime.now(timezone.utc)
            db.commit()
            status = AgentStatus(agent_id=agent_id, status="running", message="Agent is now running.", last_heartbeat=datetime.now(timezone.utc))
            self._agent_statuses[agent_id] = status
            logger.info(f"Agent {agent_id} started. DB updated: is_active=True.")
            return status
        except Exception as e:
            db.rollback()
            logger.error(f"Error starting agent {agent_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to start agent {agent_id}: {e}")
        finally:
            db.close()

    async def stop_agent(self, agent_id: str) -> AgentStatus:
        logger.info(f"Attempting to stop agent with ID: {agent_id}")
        db: Session = self.session_factory()
        try:
            db_agent = db.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
            if not db_agent:
                raise ValueError(f"Agent with ID {agent_id} not found.")
            db_agent.is_active = False
            db_agent.updated_at = datetime.now(timezone.utc)
            db.commit()
            status = AgentStatus(agent_id=agent_id, status="stopped", message="Agent has been stopped.", last_heartbeat=datetime.now(timezone.utc))
            self._agent_statuses[agent_id] = status
            logger.info(f"Agent {agent_id} stopped. DB updated: is_active=False.")
            return status
        except Exception as e:
            db.rollback()
            logger.error(f"Error stopping agent {agent_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to stop agent {agent_id}: {e}")
        finally:
            db.close()

    async def get_child_agents(self, parent_agent_id: str) -> List[AgentConfigOutput]:
        logger.debug(f"Retrieving child agents for parent_agent_id: {parent_agent_id} from DB.")
        db: Session = self.session_factory()
        try:
            db_child_agents = db.query(AgentConfigDB).filter(AgentConfigDB.parent_agent_id == parent_agent_id).all()
            return [self._db_to_pydantic(db_agent) for db_agent in db_child_agents]
        finally:
            db.close()

    async def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        logger.debug(f"Retrieving status for agent ID: {agent_id}")
        status = self._agent_statuses.get(agent_id)
        if not status:
            db_agent_pydantic = await self.get_agent(agent_id)
            if db_agent_pydantic:
                logger.warning(f"Status not found in memory for existing agent {agent_id}, re-initializing from DB.")
                current_status_val: Literal["running", "stopped"] = "running" if db_agent_pydantic.is_active else "stopped"
                default_status = AgentStatus(agent_id=agent_id, status=current_status_val, message="Status initialized from DB is_active field.", last_heartbeat=db_agent_pydantic.updated_at)
                self._agent_statuses[agent_id] = default_status
                return default_status
            else:
                logger.warning(f"Status not found for agent ID {agent_id} (agent also not in DB).")
                return None
        return status

    async def update_agent_heartbeat(self, agent_id: str) -> bool:
        logger.debug(f"Received heartbeat for agent ID: {agent_id}")
        db: Session = self.session_factory()
        try:
            db_agent_data = db.query(AgentConfigDB.agent_id, AgentConfigDB.is_active).filter(AgentConfigDB.agent_id == agent_id).first()
            if not db_agent_data:
                logger.error(f"Cannot update heartbeat: Agent config for ID {agent_id} not found in DB.")
                if agent_id in self._agent_statuses: del self._agent_statuses[agent_id]
                return False

            agent_is_active_in_db = db_agent_data.is_active
            status = self._agent_statuses.get(agent_id)
            now = datetime.now(timezone.utc)

            if not status:
                current_status_val: Literal["running", "stopped"] = "running" if agent_is_active_in_db else "stopped"
                logger.warning(f"Heartbeat for agent {agent_id}: No in-memory status. Initializing based on DB is_active ({agent_is_active_in_db}) as '{current_status_val}'.")
                status = AgentStatus(agent_id=agent_id, status=current_status_val, message="Heartbeat received, status initialized from DB.", last_heartbeat=now)

            if agent_is_active_in_db and status.status != "running":
                 logger.warning(f"Heartbeat for agent {agent_id}: Agent is active in DB, but status was '{status.status}'. Setting to 'running'.")
                 status.status = "running"
                 status.message = f"Status set to running by heartbeat (was {status.status}, DB is_active=True)."
            elif not agent_is_active_in_db and status.status == "running":
                 logger.warning(f"Heartbeat for agent {agent_id}: Agent is NOT active in DB, but status was 'running'. Setting to 'stopped'.")
                 status.status = "stopped"
                 status.message = f"Status set to stopped by heartbeat (was {status.status}, DB is_active=False)."

            status.last_heartbeat = now
            self._agent_statuses[agent_id] = status
            logger.debug(f"Heartbeat updated for agent {agent_id}. Status: {status.status}.")
            return True
        except Exception as e:
            logger.error(f"Error during heartbeat update for agent {agent_id}: {e}", exc_info=True)
            # Do not rollback here as it's mostly a read operation with in-memory update.
            return False
        finally:
            db.close()

