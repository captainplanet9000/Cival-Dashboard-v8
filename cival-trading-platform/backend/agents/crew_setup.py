from crewai import Agent, Task, Crew, Process
from .crew_llm_config import get_llm, ERROR_MSG as LLM_ERROR_MSG
from loguru import logger

# Imports for event emission
from ..models.event_models import AgentLogEvent
# from ..services.event_service import EventService # Using placeholder for now
import uuid
from pydantic import BaseModel # For placeholder service type hint
from typing import Optional, Any # For placeholder service type hint and callback
import asyncio

# Import the newly created tools
from ..tools.agent_analysis_tools import (
    historical_stock_prices,
    current_stock_quote,
    search_stock_symbols,
    sma_calculation_tool,
    ema_calculation_tool,
    rsi_calculation_tool,
    macd_calculation_tool
)
from typing import Optional, Any # For placeholder service type hint and callback
import asyncio


class PlaceholderEventService:
    async def publish_event(self, event: BaseModel, channel: Optional[str] = None):
        event_type_str = getattr(event, 'event_type', 'UnknownType')
        event_id_str = getattr(event, 'event_id', 'NoID')
        logger.info(f"[PlaceholderEventService] Would publish event: Type='{event_type_str}', ID='{event_id_str}' to channel '{channel or 'agent_events'}'")
        logger.debug(f"[PlaceholderEventService] Event details: {event.model_dump_json(indent=2)}")

placeholder_event_service = PlaceholderEventService()
current_crew_run_id = uuid.uuid4()

def agent_step_callback(step_output: Any, agent_name_for_event: str):
    logger.debug(f"Agent Step Callback triggered for Agent: {agent_name_for_event}, Output: {str(step_output)[:200]}")
    try:
        log_message = f"Agent {agent_name_for_event} step executed."
        payload_data = {}
        if isinstance(step_output, str): # Basic handling for string output
            log_message = f"Agent {agent_name_for_event} step output: {step_output}"
        elif isinstance(step_output, dict): # If output is a dict, try to get a 'log' or use the whole dict
            log_message = step_output.get("log", log_message)
            payload_data = step_output
        # Add more sophisticated parsing of step_output if needed based on CrewAI's AgentOutput/ToolOutput structure

        event = AgentLogEvent(
            source_id=agent_name_for_event, # Using agent_name as source_id for this log
            agent_id=agent_name_for_event,
            message=log_message,
            log_level="INFO",
            data=payload_data if payload_data else None, # Store structured output if available
            crew_run_id=current_crew_run_id # Associate with the current (mock) crew run
        )

        # CrewAI callbacks are synchronous, but publish_event is async.
        # This is a common challenge. For a placeholder, we can try asyncio.run,
        # but in a real FastAPI/async app, this needs careful handling
        # (e.g., passing to an async queue, or using a sync adapter for the event service if available).
        original_publish_method = placeholder_event_service.publish_event
        async def temp_sync_publish(event_to_publish, channel=None): # Wrapper to call async method
            await original_publish_method(event_to_publish, channel)

        try:
            # Attempt to run the async publish method. This is a simplified approach.
            # In environments with an existing event loop (like FastAPI), creating a new one with asyncio.run()
            # can cause issues. A more robust solution would involve `asyncio.create_task` if the callback
            # itself can be async, or using a thread to run the async code if the callback must remain sync.
            # For now, this placeholder illustrates the intent.
            asyncio.run(temp_sync_publish(event))
        except RuntimeError as e:
            # This might happen if asyncio.run() is called from an already running event loop.
            logger.warning(f"Could not run async placeholder publish via asyncio.run for {agent_name_for_event} (RuntimeError: {e}). Logging event locally.")
            # Fallback to just logging if async call fails in this context
            logger.info(f"[PlaceholderEventService] Would publish event (direct log): Type='{event.event_type}', ID='{str(event.event_id)}', Agent: '{event.agent_id}'")

    except Exception as e:
        logger.error(f"Error in agent_step_callback for agent {agent_name_for_event}: {e}", exc_info=True)


# Attempt to get the configured LLM
# If get_llm() raises an error (e.g., API key missing), agents can't be created with it.
try:
    llm_instance = get_llm()
    logger.info("Successfully fetched LLM instance for crew_setup.")
except EnvironmentError as e:
    logger.error(f"Failed to get LLM for agent creation in crew_setup: {e}")
    logger.warning("Agents in crew_setup.py will not be functional without a configured LLM.")
    llm_instance = None # Explicitly set to None so agent creation might proceed if allow_delegation=False and no tools requiring LLM
    # Or, re-raise the error if agents absolutely cannot be defined without an LLM:
    # raise EnvironmentError(f"Cannot define agents in crew_setup.py: LLM not available. Error: {e}") from e


# Define MarketAnalystAgent
market_analyst_agent = Agent(
    role="Market Analyst",
    goal="Analyze market conditions, identify trends, and pinpoint trading opportunities based on comprehensive technical and fundamental analysis, utilizing provided tools for data retrieval and indicator calculation.", # Refined goal
    backstory=(
        "As a seasoned Market Analyst with years of experience in financial markets, you possess a deep understanding of market dynamics, "
        "economic indicators, and chart patterns. You excel at synthesizing vast amounts of data into actionable insights, "
        "providing a clear outlook on potential market movements and opportunities for various assets. You are proficient in using a suite of "
        "data fetching and technical analysis tools to support your analysis."
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm_instance,
    tools=[
        historical_stock_prices,
        current_stock_quote,
        search_stock_symbols,
        sma_calculation_tool,
        ema_calculation_tool,
        rsi_calculation_tool,
        macd_calculation_tool
    ], # Assign the new tools
    step_callback=lambda step_output_arg: agent_step_callback(step_output=step_output_arg, agent_name_for_event="market_analyst_agent") # Existing callback
)

# Define RiskManagerAgent
risk_manager_agent = Agent(
    role="Risk Manager",
    goal="Assess and mitigate trading risks by evaluating proposed trades, portfolio exposure, and market volatility.",
    backstory=(
        "With a sharp eye for detail and a quantitative mindset, you are a Risk Manager dedicated to safeguarding trading capital. "
        "You meticulously evaluate the risk parameters of every proposed trade, monitor overall portfolio exposure, "
        "and advise on appropriate position sizing and stop-loss levels to ensure adherence to risk tolerance."
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm_instance,
    step_callback=lambda step_output_arg: agent_step_callback(step_output=step_output_arg, agent_name_for_event="risk_manager_agent")
)

# Define TradeExecutorAgent
trade_executor_agent = Agent(
    role="Trade Executor",
    goal="Execute approved trades efficiently, minimizing slippage and achieving the best possible execution prices.",
    backstory=(
        "You are a precise and disciplined Trade Executor, skilled in navigating exchange order books and various order types. "
        "Your primary objective is to carry out trading decisions with speed and accuracy, ensuring that trades are filled "
        "at or near the desired levels while minimizing market impact and transaction costs."
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm_instance,
    step_callback=lambda step_output_arg: agent_step_callback(step_output=step_output_arg, agent_name_for_event="trade_executor_agent")
)

if llm_instance is None:
    logger.warning("LLM instance is None. Agents in crew_setup.py have been defined without a functional LLM. "
                   "They will have limited capabilities, especially if they rely on LLM for task execution or tool use.")

# Example of how to potentially export or use them (optional, could be done by importing the file)
# available_agents = {
# "market_analyst": market_analyst_agent,
# "risk_manager": risk_manager_agent,
# "trade_executor": trade_executor_agent,
# }

logger.info("CrewAI agents (MarketAnalyst, RiskManager, TradeExecutor) defined in crew_setup.py.")

# --- Task Definitions ---
# Define tasks for each agent. These are general tasks for now.
# Specific inputs/outputs and tool usage will be refined later.

# Task for Market Analyst Agent
market_analysis_task = Task(
    description=(
        "Conduct a comprehensive market analysis for the financial symbol: {symbol}. "
        "Consider any provided {market_event_description} and {additional_context}. "
        "Your analysis should cover today's date: {current_date}. " # Agent will need a tool for current date or it's passed in inputs
        "1. Fetch historical price data for the past year (e.g., using '2023-01-01' to '2023-12-31' if current year is 2024, adjust accordingly). "
        "2. Calculate and consider key technical indicators: SMA (20-period, 50-period), EMA (20-period), RSI (14-period), and MACD (standard parameters). "
        "3. Fetch the current quote for the symbol. "
        "4. Synthesize this information to determine current market sentiment, identify key support and resistance levels, "
        "and pinpoint any potential trading opportunities (e.g., bullish breakout, bearish reversal, ranging conditions). "
        "If a specific opportunity is identified, clearly state it."
        "You must use the provided tools for fetching data and calculating indicators."
    ),
    expected_output=(
        "A structured JSON report containing: "
        "  - 'symbol': The analyzed symbol. "
        "  - 'current_date_analyzed': Date of analysis. "
        "  - 'market_sentiment': Overall sentiment (e.g., 'Bullish', 'Bearish', 'Neutral', 'Ranging'). "
        "  - 'key_levels': {{ 'support': [level1, level2, ...], 'resistance': [level1, level2, ...] }}. "
        "  - 'technical_summary': Brief summary of indicator states (e.g., 'SMA20 above SMA50', 'RSI oversold'). "
        "  - 'identified_opportunity': Description of the primary trading opportunity identified (e.g., 'Potential bullish breakout above resistance X if volume confirms.') or 'None identified'. "
        "  - 'opportunity_details': {{ 'type': 'buy/sell/hold_watch', 'confidence': 0.0-1.0, 'entry_conditions': 'e.g., price closes above X', 'stop_loss_suggestion': 'e.g., price Y', 'take_profit_suggestion': 'e.g., price Z' }} if an opportunity is identified, else null. "
        "  - 'raw_indicator_values': {{ 'sma_20': last_sma20_value, 'sma_50': last_sma50_value, 'ema_20': last_ema20_value, 'rsi_14': last_rsi_value, 'macd': {{'macd': last_macd, 'signal': last_signal, 'histogram': last_hist}} }} (latest values of calculated indicators)."
    ),
    agent=market_analyst_agent
)

# Task for Risk Manager Agent
# This task will depend on the output of the market_analysis_task.
# CrewAI handles passing context between tasks.
risk_assessment_task = Task(
    description=(
        "Based on the provided market analysis and a proposed trading opportunity (e.g., buy, sell, hold signal from market analyst), "
        "assess the potential risks involved. Consider factors like market volatility, "
        "the confidence of the analysis, and general risk parameters. "
        "Provide a risk assessment score and recommendations for managing the risk (e.g., position size, stop-loss levels)."
    ),
    expected_output=(
        "A risk assessment report including: "
        "1. Overall risk level (e.g., low, medium, high). "
        "2. Key risks identified. "
        "3. Recommended risk mitigation strategies (e.g., stop-loss suggestion, position sizing advice). "
        "4. Confirmation whether the proposed opportunity aligns with predefined risk tolerance (conceptual for now)."
    ),
    agent=risk_manager_agent,
    context=[market_analysis_task], # Depends on the market analyst's output
)

# Task for Trade Executor Agent
# This task depends on the market analysis and risk assessment.
trade_execution_preparation_task = Task(
    description=(
        "Given a market analysis, a risk assessment, and an approved trading signal, "
        "prepare the preliminary details for trade execution. This does NOT involve actual execution. "
        "Identify the symbol, action (buy/sell), potential quantity (conceptual, e.g., 'standard unit'), "
        "and note any specific conditions from the risk assessment (e.g., 'execute only if price is above X')."
    ),
    expected_output=(
        "A trade preparation summary including: "
        "1. Symbol for trade. "
        "2. Action (Buy/Sell). "
        "3. Conceptual quantity or trade size. "
        "4. Any critical execution notes or conditions from the risk assessment. "
        "5. Confirmation that the trade is ready for (hypothetical) execution."
    ),
    agent=trade_executor_agent,
    context=[risk_assessment_task], # Depends on the risk manager's output
)

# --- Crew Definition ---
# Assemble the agents and tasks into a crew
trading_analysis_crew = Crew(
    agents=[market_analyst_agent, risk_manager_agent, trade_executor_agent],
    tasks=[market_analysis_task, risk_assessment_task, trade_execution_preparation_task],
    process=Process.sequential,  # Start with a sequential process
    verbose=2,  # Or 1 for less output, 2 for detailed execution steps
    # memory=True, # Optional: enable memory for the crew (requires further setup if using persistent memory)
    # cache=True, # Optional: enable caching for tool usage
    # manager_llm=llm_instance # Optional: if a specific LLM should manage the crew's execution flow
)

logger.info("CrewAI Tasks and Trading Analysis Crew defined in crew_setup.py.")

# Example of how to run the crew (for testing purposes, not for production in this file)
# if __name__ == '__main__':
#     if llm_instance:
#         logger.info("Attempting to run the trading_analysis_crew with sample input...")
#         # To run the crew, it needs input. Tasks are defined with descriptions that imply
#         # they expect some initial context (e.g., a financial symbol).
#         # This input is typically passed to the crew's kickoff method.
#         # The tasks' descriptions will need to be written to guide the LLM effectively
#         # based on the inputs provided to crew.kickoff().
#         inputs = {"symbol": "AAPL", "market_event_description": "Apple announced new iPhone."}
#         try:
#             # result = trading_analysis_crew.kickoff(inputs=inputs)
#             # For newer versions of CrewAI, inputs might be passed directly to tasks if not using a Process manager with specific input reqs.
#             # The tasks are defined to take general context.
#             # A simple kickoff without inputs might work if agents are designed to seek info or use defaults.
#             # However, the first task "Analyze the current market conditions for a specified financial symbol" implies an input is needed.
#
#             # CrewAI's kickoff can take inputs that are then available in the task context.
#             # Let's assume the `description` of the first task is general enough or agents are
#             # prompted/tooled to ask for specifics if needed.
#             # For a structured input, you might define it on the Process or ensure tasks can receive it.
#
#             # A more robust way for tasks to get inputs is by defining them in the task's `description`
#             # using placeholders like {symbol} and then passing them in `crew.kickoff(inputs={'symbol': 'BTCUSD'})`.
#             # The current task descriptions are general.
#
#             logger.info(f"Kicking off trading_analysis_crew with inputs: {inputs}")
#             # The inputs dict should contain keys that are referenced in your tasks' descriptions (e.g., {symbol})
#             # For now, the tasks are general. The input will be available in the shared context.
#             result = trading_analysis_crew.kickoff(inputs=inputs)
#             logger.info("Crew execution finished.")
#             logger.info("Result:\n%s", result)
#         except Exception as e:
#             logger.error(f"Error running trading_analysis_crew: {e}", exc_info=True)
#     else:
#         logger.warning("Cannot run crew kickoff example as LLM is not available.")
