# This file will contain the definitions for CrewAI agents, tasks, and eventually the trading_crew itself.

# Note on LLM Configuration:
# The `llm` parameter for the agents defined below will be dynamically configured
# by a service layer (e.g., TradingCrewService or CrewExecutionService).
# This service will use LLMConfig data (allowing selection of OpenAI, Gemini, Claude models
# and their specific parameters like temperature, max_tokens, etc.) to instantiate
# the appropriate LLM for each agent before the crew is kicked off.
# The LLM instances here are placeholders for structure and default behavior.

from crewai import Agent, Task, Crew, Process
from typing import Any, Type, List as TypingList # Renamed List to TypingList to avoid conflict
from loguru import logger # Added logger for fallback import warnings

# Attempt to import a specific LLM for placeholder usage.
# In a real environment, this would be managed by the service layer.
try:
    from langchain_openai import ChatOpenAI
    # Default placeholder LLM - this would be replaced by dynamic configuration
    # Ensure OPENAI_API_KEY is set in the environment if you run this directly for testing
    default_llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.7)
except ImportError:
    print("Warning: langchain_openai not found. Using a generic placeholder for LLM.")
    default_llm: Any = None

# Pydantic Model Imports for Task Outputs
# Assuming 'crews' is a sub-package of 'python_ai_services',
# and 'types' and 'models' are sibling sub-packages.
try:
    from ..types.trading_types import MarketAnalysis, TradingDecision
    from ..models.crew_models import StrategyApplicationResult
except ImportError:
    # Fallback for environments where relative imports might be tricky during subtask execution
    # This is primarily for the subtask execution context.
    # In a real setup, these imports should work if the package structure is correct.
    print("Warning: Could not perform relative imports for Pydantic models. Using placeholders if defined, or expect errors.")
    # Define very basic placeholders if needed for type hinting, actual models are more complex
    class MarketAnalysis(dict): pass
    class TradingDecision(dict): pass
    class StrategyApplicationResult(dict): pass

# Tool Imports (with fallbacks for subtask environment)
try:
    from ..tools.market_data_tools import fetch_market_data_tool
except ImportError:
    logger.warning("Failed to import 'fetch_market_data_tool'. It will be None.")
    fetch_market_data_tool = None

try:
    from ..tools.technical_analysis_tools import run_technical_analysis_tool
except ImportError:
    logger.warning("Failed to import 'run_technical_analysis_tool'. It will be None.")
    run_technical_analysis_tool = None

try:
    from ..tools.strategy_application_tools import apply_darvas_box_tool
except ImportError:
    logger.warning("Failed to import 'apply_darvas_box_tool'. It will be None.")
    apply_darvas_box_tool = None

# Imports for other strategy application tools
try:
    from ..tools.strategy_application_tools import apply_williams_alligator_tool
except ImportError:
    logger.warning("Failed to import 'apply_williams_alligator_tool'. It will be None.")
    apply_williams_alligator_tool = None

try:
    from ..tools.strategy_application_tools import apply_renko_tool
except ImportError:
    logger.warning("Failed to import 'apply_renko_tool'. It will be None.")
    apply_renko_tool = None

try:
    from ..tools.strategy_application_tools import apply_heikin_ashi_tool
except ImportError:
    logger.warning("Failed to import 'apply_heikin_ashi_tool'. It will be None.")
    apply_heikin_ashi_tool = None

try:
    from ..tools.strategy_application_tools import apply_elliott_wave_tool
except ImportError:
    logger.warning("Failed to import 'apply_elliott_wave_tool'. It will be None.")
    apply_elliott_wave_tool = None

try:
    from ..tools.risk_assessment_tools import assess_trade_risk_tool
except ImportError:
    logger.warning("Failed to import 'assess_trade_risk_tool'. It will be None.")
    assess_trade_risk_tool = None

# Memory Tool Imports
try:
    from ..tools.memory_tools import store_memory_tool, recall_memories_tool
except ImportError:
    logger.warning("Failed to import memory tools ('store_memory_tool', 'recall_memories_tool'). They will be None.")
    store_memory_tool = None
    recall_memories_tool = None


# --- Agent Definitions ---

# Prepare tool lists, filtering out None values if imports failed
_market_analyst_tools_base: TypingList[Any] = [t for t in [fetch_market_data_tool, run_technical_analysis_tool] if t is not None]

all_strategy_tools_imports = [
    apply_darvas_box_tool,
    apply_williams_alligator_tool,
    apply_renko_tool,
    apply_heikin_ashi_tool,
    apply_elliott_wave_tool,
]
_strategy_agent_tools_base = [tool for tool in all_strategy_tools_imports if tool is not None]
if not _strategy_agent_tools_base: # Log if all strategy tools failed to import
    logger.warning("CRITICAL: No strategy application tools were successfully imported for StrategyAgent!")

_trade_advisor_tools_base: TypingList[Any] = [t for t in [assess_trade_risk_tool] if t is not None]

# Prepare memory tools list
memory_tools_list: TypingList[Any] = [t for t in [store_memory_tool, recall_memories_tool] if t is not None]
if not memory_tools_list:
    logger.warning("Memory tools (store_memory_tool, recall_memories_tool) failed to import. Agents will lack memory capabilities via these tools.")

# Extend base tool lists with memory tools, ensuring no duplicates
market_analyst_tools_list = list(dict.fromkeys(_market_analyst_tools_base + memory_tools_list))
strategy_agent_tools_list = list(dict.fromkeys(_strategy_agent_tools_base + memory_tools_list))
trade_advisor_tools_list = list(dict.fromkeys(_trade_advisor_tools_base + memory_tools_list))


market_analyst_agent = Agent(
    role="Expert Market Analyst",
    goal="Analyze market conditions for {symbol} over {timeframe}, using available tools to fetch data and perform technical analysis. Synthesize findings into a structured `MarketAnalysis` object, and store key observations using memory tools for future reference and cross-task context.",
    backstory=(
        "A seasoned financial analyst with over 15 years of experience in equity and crypto markets. "
        "Possesses deep expertise in technical analysis, chart patterns, indicator interpretation, and "
        "correlating market sentiment with price movements. Known for clear, concise, and actionable insights, "
        "adept at summarizing complex data, and leveraging memory tools to maintain context over time."
    ),
    llm=default_llm,
    tools=market_analyst_tools_list,
    allow_delegation=False,
    verbose=True,
    memory=True
)

strategy_agent = Agent(
    role="Quantitative Trading Strategist",
    goal="Apply the '{strategy_name}' trading strategy to the provided market analysis for {symbol}. Utilize strategy-specific tools and logic to determine a trading action, confidence, and key trade parameters. Can recall prior analyses or store strategy rationale using memory tools. Format your output as a `StrategyApplicationResult` object.",
    backstory=(
        "A specialist in quantitative modeling and algorithmic trading strategy development and execution. "
        "Expert in translating market analysis and predefined strategy rules into concrete, actionable trading advice "
        "with strict adherence to the specified strategy's logic. Uses memory tools to enhance context and record decisions. Ensures all outputs are structured and precise."
    ),
    llm=default_llm,
    tools=strategy_agent_tools_list,
    allow_delegation=False,
    verbose=True,
    memory=True
)

trade_advisor_agent = Agent(
    role="Prudent Chief Trading Advisor",
    goal="Synthesize the market analysis and strategy advice for {symbol}. Perform a final risk assessment using available tools, and recall relevant historical context or decisions using memory tools. Formulate a comprehensive and actionable trading decision, ensuring it's presented as a `TradingDecision` object and key aspects are stored in memory.",
    backstory=(
        "An experienced trading advisor and risk manager with a fiduciary mindset. Responsible for making final, sound, "
        "risk-managed trading recommendations. Ensures all available information, strategy outputs, risk factors, and historical context (via memory tools) are meticulously "
        "evaluated to ensure the highest quality and reliability of the final trading decision."
    ),
    llm=default_llm,
    tools=trade_advisor_tools_list,
    allow_delegation=False,
    verbose=True,
    memory=True
)

# --- Task Definitions ---
# Note: Placeholders like {symbol}, {timeframe}, and {strategy_name} in task descriptions
# will be dynamically filled by the TradingCrewService or CrewExecutionService when
# the crew is initiated, using inputs provided to that service.

market_analysis_task = Task(
    description=(
        "Analyze the market conditions for symbol '{symbol}' over the '{timeframe}'. Utilize available tools to fetch "
        "necessary market data and perform technical analysis. Focus on identifying the current trend, volatility, "
        "key support and resistance levels, and summarizing relevant technical indicator values. "
        "Consider recent news or sentiment if data is available through your tools. Your final output must be a detailed analysis. "
        "Upon completing your analysis, you MUST use the `store_memory_tool`. For the `app_agent_id` parameter, construct a unique ID using the provided '{{crew_run_id}}' (if available, otherwise use 'general_analysis'), the symbol '{{symbol}}', and timeframe '{{timeframe}}', formatted like: "
        "'{crew_run_id}_market_analysis_{symbol}_{timeframe}' or 'general_analysis_market_analysis_{symbol}_{timeframe}'. "
        "The `observation` parameter for the tool should be a concise JSON string summarizing your `MarketAnalysis` output's key findings. Example: "
        "'observation=''{{\"condition\": \"bullish\", \"trend\": \"uptrend\", \"key_support\": 150.0, \"key_resistance\": 180.0}}'''. "
        "This will help build historical context for subsequent tasks or runs. The placeholders {{symbol}}, {{timeframe}}, and {{crew_run_id}} will be interpolated from task inputs if provided."
    ),
    expected_output=(
        "A JSON object that strictly conforms to the `MarketAnalysis` Pydantic model. This includes fields like "
        "`symbol`, `timeframe`, `market_condition`, `trend_direction`, `trend_strength`, `volatility_score`, `support_levels`, "
        "`resistance_levels`, `indicators`, `sentiment_score`, `news_impact_summary`, and `short_term_forecast`. "
        "The agent should also have stored a summary of this analysis using the memory tool as per the description."
    ),
    agent=market_analyst_agent,
    output_pydantic=MarketAnalysis,
    async_execution=False
)

strategy_application_task = Task(
    description=(
        "You are tasked with applying a specific trading strategy to the provided market analysis for the symbol: '{symbol}'. "
        "The strategy to apply is explicitly named: '{strategy_name}'. "
        "Before applying the strategy, you MAY use the `recall_memories_tool` to check for recent market analyses for '{symbol}' over '{timeframe}'. "
        "For the `app_agent_id` parameter of the recall tool, use a format like '{crew_run_id}_market_analysis_{symbol}_{timeframe}' or 'general_analysis_market_analysis_{symbol}_{timeframe}' (if {crew_run_id} is not available). The query should be specific, e.g., 'What was the market condition and trend for {symbol} recently?'. "
        "You have a set of tools, each designed to apply a different trading strategy (e.g., apply_darvas_box_tool, apply_williams_alligator_tool, etc.). "
        "You MUST select and use the ONE tool that corresponds EXACTLY to the provided '{strategy_name}'. "
        "The specific configuration parameters for this strategy are provided in the '{strategy_config}' dictionary. "
        "You MUST pass the market analysis data (from the context of the 'market_analysis_task') as the first argument (e.g., 'processed_market_data_json') to the chosen tool, "
        "and the '{strategy_config}' dictionary as the second argument (e.g., 'darvas_config' for apply_darvas_box_tool, 'alligator_config' for apply_williams_alligator_tool, etc. - ensure the config dictionary key matches the tool's expected parameter name for its specific configuration). "
        "Your goal is to execute the selected strategy tool with the correct inputs and output its findings. "
        "Determine a trading action (BUY, SELL, or HOLD), a confidence score, and other relevant parameters as dictated by the strategy's output. "
        "Provide a clear rationale. Your final output must be a detailed strategy application result. "
        "After determining your advice, you MUST use the `store_memory_tool`. For `app_agent_id`, use a format like '{crew_run_id}_strategy_application_{symbol}_{strategy_name}' or 'general_strategy_application_{symbol}_{strategy_name}'. "
        "The `observation` should be a concise JSON string summary of your `StrategyApplicationResult` (e.g., advice, confidence, key rationale points). Example: "
        "'observation=''{{\"advice\": \"BUY\", \"confidence\": 0.75, \"rationale_summary\": \"Breakout confirmed on high volume.\"}}'''. The placeholders {{symbol}}, {{strategy_name}}, and {{crew_run_id}} will be interpolated from task inputs if provided."
    ),
    expected_output=(
        "A JSON object strictly conforming to the `StrategyApplicationResult` Pydantic model. "
        "This JSON object must accurately reflect the outcome of applying the strategy '{strategy_name}' using its specific configuration '{strategy_config}'. "
        "Key fields to populate include: `symbol`, `strategy_name` (must match the input '{strategy_name}'), `advice` (BUY, SELL, or HOLD), "
        "`confidence_score`, `target_price` (if applicable), `stop_loss` (if applicable), `take_profit` (if applicable), `rationale`, "
        "and `additional_data` containing any specific outputs from the executed strategy tool (like box coordinates, Renko bricks, or HA candle previews). "
        "The agent should also have stored its advice summary using the memory tool as per the description."
    ),
    agent=strategy_agent,
    context=[market_analysis_task],
    output_pydantic=StrategyApplicationResult,
    async_execution=False
)

trade_decision_task = Task(
    description=(
        "Review the provided market analysis and the '{strategy_name}' strategy application result for '{symbol}'. "
        "To build comprehensive context, you SHOULD use the `recall_memories_tool` to retrieve relevant information. For example: "
        "1. The latest `MarketAnalysis` for '{symbol}' (e.g., `app_agent_id='{crew_run_id}_market_analysis_{symbol}_{timeframe}'` or 'general_analysis_market_analysis_{symbol}_{timeframe}'). "
        "2. The latest `StrategyApplicationResult` for '{symbol}' and '{strategy_name}' (e.g., `app_agent_id='{crew_run_id}_strategy_application_{symbol}_{strategy_name}'` or 'general_strategy_application_{symbol}_{strategy_name}'). "
        "Your query should be specific to what you need from these memories. "
        "Conduct a final risk assessment using the `assess_trade_risk_tool` based on the proposed action from the strategy, "
        "market context from the analysis, and any available portfolio information (conceptually, portfolio context might be limited for this tool directly). "
        "Synthesize all information to formulate a comprehensive trading decision. Your final output must be a complete trading signal, "
        "ensuring all fields of the `TradingDecision` Pydantic model are appropriately populated. "
        "After formulating the final `TradingDecision`, you MUST use the `store_memory_tool`. For `app_agent_id`, use a format like '{crew_run_id}_trade_decision_{symbol}' or 'general_trade_decision_{symbol}'. "
        "The `observation` should be a concise JSON string summary of the key elements of your `TradingDecision` (e.g., action, symbol, confidence, primary reason, risk level). Example: "
        "'observation=''{{\"action\": \"BUY\", \"symbol\": \"{symbol}\", \"confidence\": 0.8, \"reason_summary\": \"Strong bullish indicators and positive RRR.\", \"risk_level\": \"LOW\"}}'''. The placeholders {{symbol}}, {{strategy_name}}, {{timeframe}} and {{crew_run_id}} will be interpolated from task inputs if provided."
    ),
    expected_output=(
        "A JSON object strictly conforming to the `TradingDecision` Pydantic model. This must include `action` (enum: BUY, SELL, or HOLD), "
        "`decision_id` (generate a unique ID), `symbol`, `confidence` (float 0-1), `timestamp` (ISO format), `reasoning` (comprehensive summary), "
        "`risk_assessment` (embedding the output from `assess_trade_risk_tool` or its key fields like `risk_level` and `warnings`), "
        "and where applicable, `quantity` (use a default like 1.0 if not calculable yet or not provided by strategy), "
        "`entry_price` (Optional[float]), `stop_loss` (Optional[float]), and `take_profit` (Optional[float]). "
        "The agent should also have stored its final decision summary using the memory tool as per the description."
    ),
    agent=trade_advisor_agent,
    context=[market_analysis_task, strategy_application_task],
    output_pydantic=TradingDecision,
    async_execution=False
)

# --- Crew Definition ---
# This defines the blueprint of the trading analysis crew.
# The actual instantiation, including dynamic LLM configuration for agents,
# will be handled by a service layer (e.g., TradingCrewService or CrewExecutionService).

trading_analysis_crew = Crew(
    agents=[market_analyst_agent, strategy_agent, trade_advisor_agent],
    tasks=[market_analysis_task, strategy_application_task, trade_decision_task],
    process=Process.sequential,  # Tasks will be executed one after another
    verbose=2,  # 0 for no output, 1 for basic, 2 for detailed output
    memory=False, # Crew-level memory; individual agents have their own memory enabled.
                  # Set to True if a shared short-term scratchpad for the whole crew run is needed.
    manager_llm=None, # No manager LLM for sequential processes.
                      # Would be configured if using Process.hierarchical.
    output_log_file=True # Creates a log file for the crew run, e.g., "trading_analysis_crew_YYYY-MM-DD_HH-MM-SS.log"
                         # Can also be a specific file path string.
)

# --- Placeholder for Tools (to be defined in ../tools/) ---
# (Comments about tools from previous step remain relevant)
pass
