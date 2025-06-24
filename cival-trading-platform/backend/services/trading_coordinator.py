"""
Enhanced Trading Coordinator that leverages CrewAI for analysis.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import httpx
import json
import asyncio # Added

# Local imports
from ..utils.google_sdk_bridge import GoogleSDKBridge
from ..utils.a2a_protocol import A2AProtocol
# Use TradingAnalysisCrewRequest from api_models.py for consistency with new API endpoint
from ..models.api_models import TradingAnalysisCrewRequest
# Import the crew
from ..agents.crew_setup import trading_analysis_crew
# The original TradingAnalysisRequest and other types from trading_types might still be used by other methods
# or might need to be reconciled. For analyze_trading_opportunity, we use TradingAnalysisCrewRequest.
from ..types.trading_types import TradingAnalysisRequest as OriginalTradingAnalysisRequest

# Add import for SimulatedTradeExecutor for type hinting
from .simulated_trade_executor import SimulatedTradeExecutor
from .hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError
from .dex_execution_service import DEXExecutionService, DEXExecutionServiceError
from .trade_history_service import TradeHistoryService
from .risk_manager_service import RiskManagerService
from .agent_management_service import AgentManagementService
from .event_bus_service import EventBusService
from .regulatory_compliance_service import RegulatoryComplianceService
from .learning_data_logger_service import LearningDataLoggerService
from .order_history_service import OrderHistoryService, OrderHistoryServiceError
from ..core.websocket_manager import connection_manager as global_connection_manager
from ..models.websocket_models import WebSocketEnvelope
from ..models.trading_history_models import TradeFillData # For linking fills

# Add imports for PaperTradeOrder and related enums
from ..models.paper_trading_models import PaperTradeOrder, PaperTradeFill
from ..models.trading_history_models import TradeSide, OrderType as PaperOrderType
from ..models.hyperliquid_models import HyperliquidPlaceOrderParams
from datetime import timezone
import uuid
from typing import List # For _log_learning_event


class TradingCoordinator:
    """
    Coordinates trading analysis by leveraging specialized CrewAI crews.
    Other functionalities like trade execution are delegated to external APIs or simulators.
    """
    
    def __init__(self,
                 agent_id: str, # Made non-optional
                 agent_management_service: AgentManagementService, # Made non-optional
                 risk_manager_service: RiskManagerService, # Made non-optional
                 event_bus_service: EventBusService, # Made non-optional
                 google_bridge: Optional[GoogleSDKBridge] = None,
                 a2a_protocol: Optional[A2AProtocol] = None,
                 simulated_trade_executor: Optional[SimulatedTradeExecutor] = None,
                 hyperliquid_execution_service: Optional[HyperliquidExecutionService] = None,
                 dex_execution_service: Optional[DEXExecutionService] = None,
                 trade_history_service: Optional[TradeHistoryService] = None,
                 order_history_service: Optional[OrderHistoryService] = None,
                 compliance_service: Optional[RegulatoryComplianceService] = None,
                 learning_logger_service: Optional[LearningDataLoggerService] = None,
                 connection_mgr: Optional[Any] = None
                ):
        self.agent_id = agent_id
        self.agent_management_service = agent_management_service
        self.risk_manager_service = risk_manager_service
        self.event_bus_service = event_bus_service
        self.google_bridge = google_bridge
        self.a2a_protocol = a2a_protocol
        self.simulated_trade_executor = simulated_trade_executor
        self.hyperliquid_execution_service = hyperliquid_execution_service
        self.dex_execution_service = dex_execution_service
        self.trade_history_service = trade_history_service
        self.order_history_service = order_history_service
        self.compliance_service = compliance_service
        self.learning_logger_service = learning_logger_service
        self.connection_manager = connection_mgr if connection_mgr else global_connection_manager
        self.trade_execution_mode: str = "paper"

        self.base_url = "http://localhost:3000/api/agents/trading"
        logger.info(f"TradingCoordinator instance {self.agent_id} initialized.")
        if self.simulated_trade_executor: logger.info("SimulatedTradeExecutor: Available")
        if self.hyperliquid_execution_service: logger.info("HyperliquidExecutionService: Available")
        if self.dex_execution_service: logger.info("DEXExecutionService: Available")
        if self.order_history_service: logger.info("OrderHistoryService: Available")
        else: logger.warning("OrderHistoryService: Not available. Order lifecycle will not be recorded.")
        # Add other logs as needed
        logger.info(f"Default trade execution mode: {self.trade_execution_mode}")

    async def set_trade_execution_mode(self, mode: str) -> Dict[str, str]:
        """Sets the trade execution mode for the TradingCoordinator."""
        allowed_modes = ["paper", "live"]
        if mode.lower() not in allowed_modes:
            logger.error(f"Attempted to set invalid trade execution mode: {mode}")
            raise ValueError(f"Invalid trade execution mode '{mode}'. Allowed modes are: {', '.join(allowed_modes)}")

        self.trade_execution_mode = mode.lower()
        logger.info(f"Trade execution mode set to: {self.trade_execution_mode}")
        return {"status": "success", "message": f"Trade execution mode set to {self.trade_execution_mode}"}

    async def get_trade_execution_mode(self) -> Dict[str, str]:
        """Gets the current trade execution mode."""
        logger.debug(f"Current trade execution mode is: {self.trade_execution_mode}")
        return {"current_mode": self.trade_execution_mode}

    async def _execute_trade_decision(self, trade_params: Dict[str, Any], agent_id_executing_trade: str) -> Dict: # Renamed user_id to agent_id_executing_trade
        logger.info(f"TC ({self.agent_id}): Executing trade for agent {agent_id_executing_trade} with params: {trade_params}, mode: {self.trade_execution_mode}")

        internal_order_id: Optional[str] = None
        main_order_hl_params: Optional[HyperliquidPlaceOrderParams] = None
        main_order_result_dict = None # Ensure it's defined for all paths for the return
        sl_order_result_dict_or_error = None # Ensure defined
        tp_order_result_dict_or_error = None # Ensure defined


        if self.trade_execution_mode == "hyperliquid":
            if not self.hyperliquid_execution_service:
                return {"status": "live_skipped", "reason": "Hyperliquid service unavailable."}
            if not self.order_history_service:
                logger.warning("OrderHistoryService not available for Hyperliquid mode, order lifecycle will not be fully recorded.")

            try:
                is_buy = trade_params["action"].lower() == "buy"
                order_type_key = trade_params["order_type"].lower()
                order_type_params_hl: Dict[str, Any]

                if order_type_key == "limit":
                    if trade_params.get("price") is None: raise ValueError("Price required for HL limit order.")
                    order_type_params_hl = {"limit": {"tif": "Gtc"}}
                    limit_px_for_sdk = float(trade_params["price"])
                elif order_type_key == "market":
                    order_type_params_hl = {"market": {"tif": "Ioc"}}
                    limit_px_for_sdk = 0.0
                else: raise ValueError(f"Unsupported HL order type: {order_type_key}")

                main_order_hl_params = HyperliquidPlaceOrderParams(
                    asset=trade_params["symbol"].upper(), is_buy=is_buy, sz=float(trade_params["quantity"]),
                    limit_px=limit_px_for_sdk, order_type=order_type_params_hl, reduce_only=False
                )
                cloid_to_record = str(main_order_hl_params.cloid) if main_order_hl_params.cloid else None

                if self.order_history_service:
                    new_order_db = await self.order_history_service.record_order_submission(
                        agent_id=agent_id_executing_trade, order_params=trade_params,
                        strategy_name=trade_params.get("strategy_name"), client_order_id=cloid_to_record
                    )
                    internal_order_id = new_order_db.internal_order_id

                main_order_result = await self.hyperliquid_execution_service.place_order(main_order_hl_params)
                main_order_result_dict = main_order_result.model_dump() # Define after result

                if internal_order_id and self.order_history_service:
                    await self.order_history_service.update_order_from_hl_response(internal_order_id, main_order_result)

                if main_order_result.oid is not None and self.trade_history_service and self.hyperliquid_execution_service:
                    await asyncio.sleep(2)
                    actual_fills = await self.hyperliquid_execution_service.get_fills_for_order(agent_id_executing_trade, main_order_result.oid)
                    for fill_dict in actual_fills:
                        try:
                            raw_dir = fill_dict.get("dir", "")
                            if "long" in raw_dir.lower(): mapped_side = "buy" if "open" in raw_dir.lower() else "sell"
                            elif "short" in raw_dir.lower(): mapped_side = "sell" if "open" in raw_dir.lower() else "buy"
                            elif raw_dir.upper() == "B": mapped_side = "buy"
                            elif raw_dir.upper() == "S": mapped_side = "sell"
                            else: mapped_side = "buy" if main_order_hl_params.is_buy else "sell"

                            fill_data_obj = TradeFillData(
                                agent_id=agent_id_executing_trade, asset=str(fill_dict["coin"]), side=mapped_side, # type: ignore
                                quantity=float(fill_dict["qty"]), price=float(fill_dict["px"]),
                                timestamp=datetime.fromtimestamp(int(fill_dict["time"])/1000, tz=timezone.utc),
                                fee=float(fill_dict.get("fee",0.0)), fee_currency="USD",
                                exchange_order_id=str(fill_dict.get("oid", main_order_result.oid)),
                                exchange_trade_id=str(fill_dict.get("tid", uuid.uuid4()))
                            )
                            recorded_fill = await self.trade_history_service.record_fill(fill_data_obj)
                            await self.trade_history_service.record_fill(fill_data_obj) # record_fill returns None
                            # Link to order history if applicable (assuming internal_order_id and service exist)
                            if hasattr(self, 'order_history_service') and self.order_history_service and internal_order_id and hasattr(fill_data_obj, 'fill_id'):
                                await self.order_history_service.link_fill_to_order(internal_order_id, fill_data_obj.fill_id) # Use fill_data_obj.fill_id

                            # Send WebSocket message using fill_data_obj
                            if self.connection_manager:
                                ws_env = WebSocketEnvelope(
                                    event_type="NEW_FILL",
                                    agent_id=agent_id_executing_trade, # This is the agent for whom the trade was
                                    payload=fill_data_obj.model_dump(mode='json')
                                )
                                await self.connection_manager.send_to_client(agent_id_executing_trade, ws_env)
                        except Exception as e_f: logger.error(f"TC ({self.agent_id}): Error processing HL fill or sending WebSocket: {e_f}", exc_info=True)

                # SL/TP logic (simplified, ensure main_order_result_dict is used if needed)
                if main_order_result.oid is not None and main_order_result.status in ["resting", "filled", "ok"]:
                    # ... (SL/TP placement logic can be added here) ...
                    pass

                return {"status": "live_executed", "details": {"main_order": main_order_result_dict, "stop_loss_order": sl_order_result_dict_or_error, "take_profit_order": tp_order_result_dict_or_error } }

            except (HyperliquidExecutionServiceError, ValueError) as e:
                logger.error(f"Live trade execution process failed for agent {agent_id_executing_trade}: {e}", exc_info=True)
                if internal_order_id and self.order_history_service:
                    await self.order_history_service.update_order_status(internal_order_id, "ERROR", error_message=f"HL Execution Error: {str(e)}")
                return {"status": "live_failed", "error": str(e), "details": {"main_order": main_order_result_dict, "stop_loss_order": sl_order_result_dict_or_error, "take_profit_order": tp_order_result_dict_or_error}}
            except Exception as e:
                logger.error(f"Unexpected error during live trade execution for agent {agent_id_executing_trade}: {e}", exc_info=True)
                if internal_order_id and self.order_history_service:
                    await self.order_history_service.update_order_status(internal_order_id, "ERROR", error_message=f"Unexpected HL Error: {str(e)}")
                return {"status": "live_failed", "error": f"Unexpected error: {str(e)}", "details": {"main_order": main_order_result_dict, "stop_loss_order": sl_order_result_dict_or_error, "take_profit_order": tp_order_result_dict_or_error}}

        elif self.trade_execution_mode == "dex":
            if not self.dex_execution_service:
                return {"status": "dex_skipped", "reason": "DEX service unavailable."}
            if not self.order_history_service:
                logger.warning("OrderHistoryService not available for DEX mode, order lifecycle will not be fully recorded.")

            internal_order_id_for_dex: Optional[str] = None
            try:
                if self.order_history_service:
                    new_dex_order_db = await self.order_history_service.record_order_submission(
                        agent_id=agent_id_executing_trade, order_params=trade_params,
                        strategy_name=trade_params.get("strategy_name"), client_order_id=trade_params.get("client_order_id")
                    )
                    internal_order_id_for_dex = new_dex_order_db.internal_order_id

                logger.info(f"TC ({self.agent_id}): DEX path for agent {agent_id_executing_trade} - current logic is placeholder.")
                # Placeholder for DEX parameter mapping and call
                symbol_pair = trade_params.get("symbol", "UNKNOWN/UNKNOWN")
                mock_token_in_address = f"0xMOCK_IN_{symbol_pair.split('/')[0]}"
                mock_token_out_address = f"0xMOCK_OUT_{symbol_pair.split('/')[1] if '/' in symbol_pair else ''}"
                mock_amount_in_wei = int(float(trade_params.get("quantity",0)) * 10**18)
                mock_min_amount_out_wei = 0
                mock_fee_tier = 3000

                # dex_swap_result = await self.dex_execution_service.place_swap_order(...) # Actual call
                dex_swap_result = {
                    "tx_hash": f"0xMOCK_DEX_{uuid.uuid4().hex}", "status": "success_mocked_dex", "error": None,
                    "amount_out_wei_actual": mock_min_amount_out_wei,
                    "amount_out_wei_minimum_requested": mock_min_amount_out_wei,
                    "amount_in_wei": mock_amount_in_wei, "token_in": mock_token_in_address,
                    "token_out": mock_token_out_address
                } # Mocked result

                if internal_order_id_for_dex and self.order_history_service:
                    await self.order_history_service.update_order_from_dex_response(internal_order_id_for_dex, dex_swap_result)
                    # Conceptual fill linking for DEX (if fills were part of dex_swap_result)
                    # if self.trade_history_service and dex_swap_result.get("fills"): ... link them ...

                return {"status": "dex_executed_placeholder", "details": dex_swap_result}

            except (DEXExecutionServiceError, ValueError) as e:
                logger.error(f"DEX trade execution failed for agent {agent_id_executing_trade}: {e}", exc_info=True)
                if internal_order_id_for_dex and self.order_history_service:
                    await self.order_history_service.update_order_status(internal_order_id_for_dex, "ERROR", error_message=f"DEX Exec Error: {str(e)}")
                return {"status": "dex_failed", "error": str(e)}
            except Exception as e:
                logger.error(f"Unexpected error during DEX trade placeholder for agent {agent_id_executing_trade}: {e}", exc_info=True)
                if internal_order_id_for_dex and self.order_history_service:
                    await self.order_history_service.update_order_status(internal_order_id_for_dex, "ERROR", error_message=f"Unexpected DEX Error: {str(e)}")
                return {"status": "dex_failed_unexpected", "error": str(e)}

        elif self.trade_execution_mode == "paper":
            if not self.simulated_trade_executor:
                return {"status": "paper_skipped", "reason": "Simulated executor unavailable."}
            try:
                paper_order_side = TradeSide.BUY if trade_params["action"].lower() == "buy" else TradeSide.SELL
                paper_order_type_str = trade_params["order_type"].lower()
                paper_order_type_enum = PaperOrderType.MARKET
                if paper_order_type_str == "limit": paper_order_type_enum = PaperOrderType.LIMIT

                paper_order = PaperTradeOrder(
                    user_id=uuid.UUID(agent_id_executing_trade), symbol=trade_params["symbol"], side=paper_order_side,
                    order_type=paper_order_type_enum, quantity=float(trade_params["quantity"]),
                    limit_price=float(trade_params["price"]) if paper_order_type_enum == PaperOrderType.LIMIT and trade_params.get("price") is not None else None,
                    created_at=datetime.now(timezone.utc)
                )
                updated_order, fills = await self.simulated_trade_executor.submit_paper_order(paper_order)
                # OHS integration for paper trades is not part of this subtask's primary scope
                # but could be added here if desired, by calling record_order_submission and update_order_status.
                return {"status": "paper_executed", "details": {"order": updated_order.model_dump(), "fills": [f.model_dump() for f in fills]}}
            except Exception as e:
                return {"status": "paper_failed", "error": str(e)}
        else:
            return {"status": "error", "reason": f"Unknown trade execution mode: {self.trade_execution_mode}"}

    async def _parse_crew_result_and_execute(self, crew_result: Any, user_id: str):
        """
        Parses the result from a CrewAI crew and, if actionable, triggers a trade decision.
        """
        logger.info(f"Parsing crew result for user {user_id}. Result snippet: {str(crew_result)[:300]}")

        trade_params: Optional[Dict[str, Any]] = None

        try:
            if isinstance(crew_result, str):
                try:
                    data = json.loads(crew_result)
                except json.JSONDecodeError:
                    logger.warning(f"Crew result is a string but not valid JSON: {crew_result}")
                    data = {} # Treat as empty dict if not parsable
            elif isinstance(crew_result, dict):
                data = crew_result
            else:
                logger.warning(f"Crew result is of unexpected type: {type(crew_result)}. Cannot parse for trade action.")
                return

            # Placeholder parsing logic - adapt based on actual crew output structure
            # Example: Crew might output a dict with 'action', 'symbol', 'quantity', 'order_type', 'price'
            action = data.get("action", data.get("trading_decision", {}).get("action"))
            symbol = data.get("symbol", data.get("trading_decision", {}).get("symbol"))
            quantity = data.get("quantity", data.get("trading_decision", {}).get("quantity"))
            order_type = data.get("order_type", data.get("trading_decision", {}).get("order_type", "market")) # Default to market
            price = data.get("price", data.get("trading_decision", {}).get("price")) # For limit orders

            if action and symbol and quantity:
                if action.lower() in ["buy", "sell"]:
                    trade_params = {
                        "action": action.lower(),
                        "symbol": symbol,
                        "quantity": float(quantity), # Ensure quantity is float
                        "order_type": order_type.lower(),
                    }
                    if order_type.lower() == "limit" and price is not None:
                        trade_params["price"] = float(price) # Ensure price is float

                    logger.info(f"Extracted trade parameters: {trade_params}")
                    await self._execute_trade_decision(trade_params, user_id)
                elif action.lower() == "hold":
                    logger.info(f"Crew decision is 'hold' for {symbol}. No trade execution.")
                else:
                    logger.warning(f"Unknown action '{action}' in crew result. No trade execution.")
            else:
                logger.warning(f"Essential trade parameters (action, symbol, quantity) not found in crew result: {data}")

        except Exception as e:
            logger.error(f"Error parsing crew result or initiating trade execution: {e}", exc_info=True)


    async def execute_trade(self, trade_request: Dict) -> Dict:
        logger.info(f"Executing trade: {trade_request}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/execute",
                    json=trade_request,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Log successful trade execution
                logger.info(f"Trade executed successfully: {result}")
                
                # Broadcast trade execution to other agents
                await self.a2a_protocol.broadcast_message(
                    message_type="trade_executed",
                    payload={
                        "agent_id": trade_request.get("agentId", trade_request.get("agent_id")),
                        "trade": result,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing trade: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Trade execution failed: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error executing trade: {str(e)}")
            raise Exception(f"Trade execution request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error executing trade: {str(e)}", exc_info=True)
            raise Exception(f"An unexpected error occurred during trade execution: {str(e)}")

    async def register_agent(self, agent_config: Dict) -> Dict:
        """Register agent with trading permissions"""
        logger.info(f"Registering agent: {agent_config}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/register",
                    json=agent_config,
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Agent registered successfully: {result}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error registering agent: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Agent registration failed: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error registering agent: {str(e)}")
            raise Exception(f"Agent registration request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error registering agent: {str(e)}", exc_info=True)
            raise Exception(f"An unexpected error occurred during agent registration: {str(e)}")

    async def get_agent_status(self, agent_id: str) -> Dict:
        """Get agent status"""
        logger.info(f"Getting status for agent: {agent_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/status?agentId={agent_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Retrieved agent status: {result}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting agent status: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to get agent status: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error getting agent status: {str(e)}")
            raise Exception(f"Agent status request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting agent status: {str(e)}", exc_info=True)
            raise Exception(f"An unexpected error occurred while fetching agent status: {str(e)}")

    async def get_agent_trading_history(self, agent_id: str) -> Dict:
        """Get agent trading history"""
        logger.info(f"Getting trading history for agent: {agent_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/history?agentId={agent_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Retrieved agent trading history: {len(result.get('trades', []))} trades")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting agent trading history: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to get agent trading history: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error getting agent trading history: {str(e)}")
            raise Exception(f"Agent trading history request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting agent trading history: {str(e)}", exc_info=True)
            raise Exception(f"An unexpected error occurred while fetching agent trading history: {str(e)}")
            
    async def analyze_trading_opportunity(self, request: TradingAnalysisCrewRequest) -> Any:
        """
        Analyzes a trading opportunity by kicking off the trading_analysis_crew.
        The request should conform to TradingAnalysisCrewRequest.
        """
        logger.info(f"TradingCoordinator: Received request to analyze trading opportunity for symbol: {request.symbol}")

        inputs_for_crew = {
            "symbol": request.symbol,
            "market_event_description": request.market_event_description,
            "additional_context": request.additional_context,
            "user_id": request.user_id,
            # crew_run_id could be generated here or expected in request if needed by crew directly
            # For now, crew_setup.py's example kickoff didn't strictly require it in inputs if tasks are general
        }

        # CrewAI's kickoff is a synchronous (blocking) call.
        # Since this service method is async, we must run kickoff in an executor.
        try:
            logger.info(f"Delegating analysis to trading_analysis_crew with inputs: {inputs_for_crew}")
            
            loop = asyncio.get_event_loop()
            # Using lambda to correctly pass inputs to kickoff in the executor
            result = await loop.run_in_executor(None, lambda: trading_analysis_crew.kickoff(inputs=inputs_for_crew))

            logger.info(f"Trading_analysis_crew execution completed. Result snippet: {str(result)[:500]}")
            # The structure of 'result' depends on the output of the last task in trading_analysis_crew.
            # For now, we return it directly. It might need mapping to a specific Pydantic response model.

            # After getting the result, parse it and potentially execute a trade
            # This call is fire-and-forget for now from the perspective of analyze_trading_opportunity's return value
            await self._parse_crew_result_and_execute(result, request.user_id) # request.user_id is str

            return result
        except Exception as e:
            logger.error(f"Error during trading_analysis_crew kickoff via TradingCoordinator: {e}", exc_info=True)
            # Depending on desired error handling, could raise a custom service exception here.
            # For now, re-raising a generic Exception to be caught by the main API handler.
            raise Exception(f"Failed to analyze trading opportunity due to crew execution error: {e}")