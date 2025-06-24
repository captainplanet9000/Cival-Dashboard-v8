import os
import json
from copy import deepcopy
from typing import Any, Dict, Optional, List # Added List for logs_summary
from loguru import logger
from pydantic import BaseModel, Field as PydanticField, ValidationError as PydanticValidationError
from uuid import uuid4
from datetime import datetime

from crewai import Crew, Process

# Attempt to import definitions from the same package/sub-packages
try:
    from .trading_crew_definitions import (
        market_analyst_agent,
        strategy_agent,
        trade_advisor_agent,
        market_analysis_task,
        strategy_application_task,
        trade_decision_task
    )
    from ..types.trading_types import TradingDecision  # Expected final output
    from ..main import LLMConfig # Importing LLMConfig from main.py where it's defined
    from ..services.agent_persistence_service import AgentPersistenceService # Added
    from ..models.crew_models import TaskStatus # Added
except ImportError as e:
    logger.error(f"Error importing crew definitions or types: {e}. Ensure PYTHONPATH is set correctly or run as part of a package.")
    # Define fallback placeholders if imports fail, to allow basic structure testing
    class TradingDecision(BaseModel): pass
    class LLMConfig(BaseModel): model_name: str; api_key_env_var: Optional[str]; parameters: Dict = {}
    class AgentPersistenceService: pass # Basic placeholder
    class TaskStatus: PENDING="PENDING"; RUNNING="RUNNING"; COMPLETED="COMPLETED"; FAILED="FAILED" # Basic placeholder

# LLM Client Imports (attempted)
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    logger.warning("langchain_openai not found. OpenAI models will not be available.")
    ChatOpenAI = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    logger.warning("langchain_google_genai not found. Google Gemini models will not be available.")
    ChatGoogleGenerativeAI = None

# Request model for the service
class TradingCrewRequest(BaseModel):
    """
    Defines the request structure for initiating a trading crew analysis.
    The content of `strategy_config` should align with the Pydantic model
    corresponding to the `strategy_name` (e.g., DarvasBoxConfig for 'DarvasBox').
    """
    symbol: str = PydanticField(..., example="BTC/USD")
    timeframe: str = PydanticField(default="1h", example="1h")
    strategy_name: str = PydanticField(..., example="DarvasBoxStrategy") # Example updated
    llm_config_id: str = PydanticField(..., example="openai_gpt4_turbo")
    strategy_config: Dict[str, Any] = PydanticField(
        ...,
        description="A dictionary containing strategy-specific configuration parameters. The structure should match the Pydantic config model for the strategy specified in 'strategy_name'.",
        example={
            "lookback_period_highs": 50,
            "box_definition_period": 10,
            "volume_increase_factor": 1.2,
            "min_box_duration": 3
        }
    )
    # additional_context: Optional[Dict[str, Any]] = None

# Example of TradingCrewRequest instantiation:
# request_example = TradingCrewRequest(
#     symbol="AAPL",
#     timeframe="1d",
#     strategy_name="DarvasBoxStrategy", # Or "WilliamsAlligatorStrategy", etc.
#     llm_config_id="default_openai_gpt4",
#     strategy_config={
#         # For DarvasBoxStrategy:
#         "lookback_period_highs": 252,
#         "box_definition_period": 10,
#         "volume_increase_factor": 1.5,
#         "box_range_tolerance_percent": 1.0,
#         "min_box_duration": 3,
#         "stop_loss_percent_from_bottom": 2.0
#         # For WilliamsAlligatorStrategy:
#         # "jaw_period": 13, "teeth_period": 8, "lips_period": 5, ...
#     }
# )

class TradingCrewService:
    def __init__(self, persistence_service: AgentPersistenceService): # Injected
        self.persistence_service: AgentPersistenceService = persistence_service
        # Mock LLM configs kept for now, assuming they are loaded here or this service
        # is a simplified version. In a full app, these might come from DB via persistence_service.
        self.available_llm_configs: Dict[str, LLMConfig] = {
            "openai_gpt4_turbo": LLMConfig(
                id="llm_cfg_openai", model_name="gpt-4-turbo", api_key_env_var="OPENAI_API_KEY",
                parameters={"temperature": 0.7, "max_tokens": 1500} # type: ignore
            ),
            "gemini_1_5_pro": LLMConfig(
                id="llm_cfg_gemini", model_name="gemini-1.5-pro", api_key_env_var="GEMINI_API_KEY",
                parameters={"temperature": 0.8, "top_k": 40} # type: ignore
            ),
            "default_llm": LLMConfig(
                id="llm_cfg_default", model_name="gpt-4-turbo", api_key_env_var="OPENAI_API_KEY",
                parameters={"temperature": 0.5} # type: ignore
            )
        }
        logger.info(f"TradingCrewService initialized with persistence_service: {type(persistence_service).__name__}")

    def _get_llm_instance(self, llm_config: LLMConfig) -> Any:
        logger.info(f"Attempting to instantiate LLM for model: {llm_config.model_name}")
        api_key = None
        if llm_config.api_key_env_var:
            api_key = os.getenv(llm_config.api_key_env_var)
            if not api_key:
                logger.error(f"API key environment variable '{llm_config.api_key_env_var}' not found.")
                raise ValueError(f"API key for {llm_config.model_name} not configured.")

        model_name_lower = llm_config.model_name.lower()
        # Ensure parameters is a dict, even if None from Pydantic model
        params = llm_config.parameters.model_dump() if hasattr(llm_config.parameters, 'model_dump') else (llm_config.parameters or {})


        if "gpt" in model_name_lower:
            if ChatOpenAI:
                logger.info(f"Instantiating ChatOpenAI with model: {llm_config.model_name} and params: {params}")
                return ChatOpenAI(model=llm_config.model_name, api_key=api_key, **params)
            else:
                logger.error("ChatOpenAI (langchain_openai) is not available, but an OpenAI model was requested.")
                raise NotImplementedError("OpenAI LLM client (langchain_openai) not installed/available.")

        elif "gemini" in model_name_lower:
            if ChatGoogleGenerativeAI:
                logger.info(f"Instantiating ChatGoogleGenerativeAI with model: {llm_config.model_name} and params: {params}")
                return ChatGoogleGenerativeAI(model=llm_config.model_name, google_api_key=api_key, **params) # Corrected: model not model_name
            else:
                logger.error("ChatGoogleGenerativeAI (langchain_google_genai) is not available, but a Gemini model was requested.")
                raise NotImplementedError("Google Gemini LLM client (langchain_google_genai) not installed/available.")

        else:
            logger.warning(f"LLM for model name '{llm_config.model_name}' is not implemented.")
            raise NotImplementedError(f"LLM support for '{llm_config.model_name}' is not implemented.")

    async def run_analysis(self, request: TradingCrewRequest) -> Optional[TradingDecision]:
        logger.info(f"Received request to run trading analysis for: {request.symbol}")
        task_id = str(uuid4())
        initial_inputs = request.model_dump()
        parsed_result: Optional[TradingDecision] = None

        # 1. Initial Task Creation
        try:
            created_task = await self.persistence_service.create_agent_task(
                task_id_str=task_id,
                crew_id="trading_analysis_crew",
                inputs=initial_inputs,
                status=TaskStatus.PENDING.value
            )
            if not created_task:
                logger.error(f"Failed to create agent task record for task_id {task_id}. Aborting crew run.")
                return None
            logger.info(f"AgentTask record created with ID: {task_id}, status: PENDING.")
        except Exception as e:
            logger.exception(f"Critical error creating initial AgentTask for {request.symbol}: {e}")
            return None # Cannot proceed without task record

        try:
            # 2. Load LLMConfig
            llm_config_data = self.available_llm_configs.get(request.llm_config_id)
            if not llm_config_data:
                logger.warning(f"LLMConfig ID '{request.llm_config_id}' not found. Using default LLM.")
                llm_config_data = self.available_llm_configs.get("default_llm")

            if not llm_config_data: # Should not happen if default_llm is defined
                 error_msg = "Default LLM configuration is missing."
                 logger.error(error_msg)
                 await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.FAILED.value, error_message=error_msg)
                 return None

            # 3. Instantiate LLM
            llm_instance = self._get_llm_instance(llm_config_data) # This can raise ValueError or NotImplementedError

            # 4. Update Task to RUNNING
            await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.RUNNING.value)
            logger.info(f"AgentTask {task_id} status updated to RUNNING.")

            # 5. Deep Copy Crew Components and Assign LLM
            cloned_market_analyst = deepcopy(market_analyst_agent)
            cloned_strategy_agent = deepcopy(strategy_agent)
            cloned_trade_advisor = deepcopy(trade_advisor_agent)

            cloned_market_analyst.llm = llm_instance
            cloned_strategy_agent.llm = llm_instance
            cloned_trade_advisor.llm = llm_instance

            current_market_analysis_task = deepcopy(market_analysis_task)
            current_market_analysis_task.agent = cloned_market_analyst

            current_strategy_application_task = deepcopy(strategy_application_task)
            current_strategy_application_task.agent = cloned_strategy_agent
            current_strategy_application_task.context = [current_market_analysis_task]

            current_trade_decision_task = deepcopy(trade_decision_task)
            current_trade_decision_task.agent = cloned_trade_advisor
            current_trade_decision_task.context = [current_market_analysis_task, current_strategy_application_task]

            # 6. Instantiate Crew
            current_crew = Crew(
                agents=[cloned_market_analyst, cloned_strategy_agent, cloned_trade_advisor],
                tasks=[current_market_analysis_task, current_strategy_application_task, current_trade_decision_task],
                process=Process.sequential, verbose=2, output_log_file=True
            )
            logger.info(f"Trading analysis crew instantiated for {request.symbol} using LLM: {llm_config_data.model_name}")

            # 7. Prepare Inputs & Kickoff Crew
            inputs_for_crew = {
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "strategy_name": request.strategy_name,
                "strategy_config": request.strategy_config,
                "crew_run_id": task_id # New addition, using the AgentTask's task_id
            }
            # Sensitive config values (like API keys if they were ever part of strategy_config) should be redacted if logged.
            # For now, assume strategy_config contains only non-sensitive parameters.
            logger.info(
                f"Kicking off trading analysis crew (Task ID/Crew Run ID: {task_id}) for symbol {request.symbol}, "
                f"strategy '{request.strategy_name}' with LLM '{llm_config_data.model_name}'. "
                f"Strategy Config: {request.strategy_config}. Full inputs: {inputs_for_crew}" # Log full inputs for clarity
            )
            raw_result: Any = None
            if hasattr(current_crew, 'kickoff_async'):
                 raw_result = await current_crew.kickoff_async(inputs=inputs_for_crew)
            else:
                 import asyncio
                 loop = asyncio.get_event_loop()
                 raw_result = await loop.run_in_executor(None, current_crew.kickoff, inputs_for_crew)
            logger.info(f"Crew execution for task_id {task_id} finished. Raw result: {str(raw_result)[:500]}...") # Log preview

            # 8. Process Result
            if raw_result is None:
                error_msg = f"Crew for {request.symbol} (task_id: {task_id}) returned no result."
                logger.error(error_msg)
                await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.FAILED.value, error_message=error_msg)
                return None

            try:
                if isinstance(raw_result, TradingDecision):
                    parsed_result = raw_result
                elif isinstance(raw_result, dict):
                    parsed_result = TradingDecision(**raw_result)
                elif isinstance(raw_result, str):
                    parsed_result = TradingDecision(**json.loads(raw_result))
                else:
                    error_msg = f"Crew for {request.symbol} (task_id: {task_id}) returned an unexpected result type: {type(raw_result)}."
                    logger.warning(error_msg + f" Result: {str(raw_result)[:500]}")
                    # Attempt to force into a TradingDecision with a 'reasoning' field if it's just a string
                    if isinstance(raw_result, str):
                        parsed_result = TradingDecision(symbol=request.symbol, action="INFO", confidence_score=0.0, reasoning=raw_result, decision_id=str(uuid4())) # type: ignore
                    else:
                        await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.FAILED.value, error_message=error_msg)
                        return None

                logger.info(f"Successfully parsed crew result for task_id {task_id}.")
                await self.persistence_service.update_agent_task_result(
                    task_id=task_id,
                    output=parsed_result.model_dump(),
                    status=TaskStatus.COMPLETED.value,
                    logs_summary=[{"timestamp": datetime.utcnow().isoformat(), "event": "Crew completed successfully."}] # Conceptual
                )
                return parsed_result

            except (PydanticValidationError, json.JSONDecodeError) as e_parse:
                error_msg = f"Error parsing crew result for {request.symbol} (task_id: {task_id}): {e_parse}. Raw result: {str(raw_result)[:500]}"
                logger.error(error_msg)
                await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.FAILED.value, error_message=error_msg)
                return None

        except (ValueError, NotImplementedError) as e_llm: # Catch specific errors from _get_llm_instance
            error_msg = f"LLM configuration/instantiation error for task_id {task_id}: {e_llm}"
            logger.error(error_msg)
            await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.FAILED.value, error_message=error_msg)
            return None
        except Exception as e_crew: # Catch errors from agent/task cloning, crew instantiation, or kickoff
            error_msg = f"Exception during crew processing for {request.symbol} (task_id: {task_id}): {e_crew}"
            logger.exception(error_msg) # Log full traceback
            await self.persistence_service.update_agent_task_status(task_id=task_id, status=TaskStatus.FAILED.value, error_message=error_msg)
            return None

pass
