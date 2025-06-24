# Conceptual Trading Crew Run with Memory Tool Integration

This document outlines a conceptual walkthrough of the `trading_analysis_crew` execution, highlighting how each agent is expected to interact with its tools, including the newly integrated memory tools (`store_memory_tool`, `recall_memories_tool`).

## Scenario Overview

The crew is tasked with performing a trading analysis for a specific financial symbol, applying a designated strategy, and producing a final trading decision. This run will demonstrate how memory tools are used to persist and recall information throughout the workflow.

## 1. Sample API Request

The process is initiated by a POST request to the `/api/v1/crews/trading/analyze` endpoint.

**Request Body Example:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "4h",
  "strategy_name": "DarvasBoxStrategy",
  "llm_config_id": "openai_gpt4_turbo",
  "strategy_config": {
    "lookback_period_highs": 90,
    "box_definition_period": 7,
    "volume_increase_factor": 1.5,
    "min_box_duration": 3,
    "stop_loss_percent_from_bottom": 1.5,
    "box_range_tolerance_percent": 0.5
  }
}
```

## 2. Inputs to `crew.kickoff_async` by `TradingCrewService`

The `TradingCrewService` receives the request, generates a unique `task_id` (which also serves as `crew_run_id`), and then starts the crew with the following inputs:

```python
inputs_for_crew = {
    "symbol": "BTC-USD",
    "timeframe": "4h",
    "strategy_name": "DarvasBoxStrategy", # From request
    "strategy_config": { ... }, # From request
    "crew_run_id": "mock_task_123_xyz" # Example task_id
}
```
*(Note: Placeholders like `{symbol}`, `{timeframe}`, `{strategy_name}`, `{strategy_config}`, and `{crew_run_id}` in agent/task descriptions will be interpolated from these inputs by CrewAI.)*

---

## 3. Task Execution Flow

### Task 1: `market_analysis_task` (Executed by `MarketAnalystAgent`)

*   **Agent's Goal (Refined):** Analyze market conditions for `{symbol}` over `{timeframe}`, using available tools to fetch data and perform technical analysis. Synthesize findings into a structured `MarketAnalysis` object, and diligently records key findings in memory for future reference and learning.
*   **Inputs from Crew Context:** `symbol="BTC-USD"`, `timeframe="4h"`, `strategy_name="DarvasBoxStrategy"`, `strategy_config={...}`, `crew_run_id="mock_task_123_xyz"`
*   **Expected Primary Tool Usage:**
    1.  `fetch_market_data_tool(symbol="BTC-USD", timeframe="4h", historical_days=...)`
        *   Output: `market_data_json_output_1` (JSON string containing OHLCV data, e.g., `{"symbol": "BTC-USD", "data": [...], "data_source_status": "service_success", ...}`)
    2.  `run_technical_analysis_tool(market_data_json=market_data_json_output_1, volume_sma_period=20)`
        *   Output: `technical_analysis_json_output_1` (JSON string containing OHLCV data augmented with TA features like `volume_sma`, e.g., `{"symbol": "BTC-USD", "ohlcv_with_ta": [...], ...}`)
*   **LLM Interaction (Conceptual):**
    *   The agent receives the task description (which instructs it to perform analysis and then store a summary).
    *   It processes the outputs from `fetch_market_data_tool` and `run_technical_analysis_tool`.
    *   Based on this data, it formulates the `MarketAnalysis` object.
    *   Expected LLM Output (for `MarketAnalysis`): `{"symbol": "BTC-USD", "timeframe": "4h", "market_condition": "NEUTRAL", "trend_direction": "SIDEWAYS", "trend_strength": 0.4, ...}` (let's call this `market_analysis_object_1`)
*   **Expected Memory Tool Usage:**
    *   The agent is instructed to use `store_memory_tool`.
    *   Call: `store_memory_tool(app_agent_id="mock_task_123_xyz_market_analysis_BTC-USD_4h", observation=json.dumps({"condition": "NEUTRAL", "trend": "SIDEWAYS", "key_support": 40000.0, "key_resistance": 45000.0, "volatility": "moderate"}), role="user")`
        *   *(Note: The observation is a concise JSON summary of `market_analysis_object_1`'s key findings.)*
    *   Tool Output (Conceptual): `{"success": True, "app_agent_id": "mock_task_123_xyz_market_analysis_BTC-USD_4h", "action": "store_memory"}`
*   **Task Output (to next task):** `market_analysis_object_1` (The full `MarketAnalysis` Pydantic object as a JSON string).
    *   *Side effect:* A summary of this analysis is stored in memory associated with the specified `app_agent_id`.

---

### Task 2: `strategy_application_task` (Executed by `StrategyAgent`)

*   **Agent's Goal (Refined):** Apply the `'{strategy_name}'` trading strategy... It leverages historical context by recalling relevant past analyses from memory and stores its own strategic advice for future learning.
*   **Inputs from Crew Context:** `symbol="BTC-USD"`, `timeframe="4h"`, `strategy_name="DarvasBoxStrategy"`, `strategy_config={...}`, `crew_run_id="mock_task_123_xyz"`. Also receives `market_analysis_object_1` from the previous task.
*   **Expected Memory Tool Usage (Recall - Optional):**
    *   The agent *MAY* use `recall_memories_tool` first.
    *   Call: `recall_memories_tool(app_agent_id="mock_task_123_xyz_market_analysis_BTC-USD_4h", query="What was the recent market condition and trend for BTC-USD 4h?")`
    *   Tool Output (Conceptual): `{"success": True, ..., "response": "{\"condition\": \"NEUTRAL\", \"trend\": \"SIDEWAYS\", ...}"}`
*   **Expected Primary Tool Usage:**
    *   The agent selects `apply_darvas_box_tool` based on `strategy_name="DarvasBoxStrategy"`.
    *   Call: `apply_darvas_box_tool(processed_market_data_json=technical_analysis_json_output_1_from_context, darvas_config={"lookback_period_highs": 90, ...})`
        *   Output: `strategy_application_json_output_1` (JSON string for `StrategyApplicationResult`, e.g., `{"symbol": "BTC-USD", "strategy_name": "DarvasBoxStrategy", "advice": "HOLD", ...}`)
*   **LLM Interaction (Conceptual):**
    *   Receives task description (instructs optional recall, mandatory strategy tool selection, and then store).
    *   If recall was performed, the recalled memory (`"{\"condition\": \"NEUTRAL\", ...}"`) is added to its context.
    *   It selects and uses the strategy-specific tool.
    *   Processes the tool's output to formulate the `StrategyApplicationResult`.
    *   Expected LLM Output (for `StrategyApplicationResult`): `{"symbol": "BTC-USD", "strategy_name": "DarvasBoxStrategy", "advice": "HOLD", "confidence_score": 0.6, ...}` (let's call this `strategy_application_object_1`)
*   **Expected Memory Tool Usage (Store - Mandatory):**
    *   The agent is instructed to use `store_memory_tool`.
    *   Call: `store_memory_tool(app_agent_id="mock_task_123_xyz_strategy_application_BTC-USD_DarvasBoxStrategy", observation=json.dumps({"advice": "HOLD", "confidence": 0.6, "rationale_summary": "No clear breakout identified."}), role="user")`
        *   *(Note: Observation is a JSON summary of `strategy_application_object_1`.)*
    *   Tool Output (Conceptual): `{"success": True, ..., "action": "store_memory"}`
*   **Task Output (to next task):** `strategy_application_object_1` (The full `StrategyApplicationResult` Pydantic object as a JSON string).
    *   *Side effect:* A summary of this strategy application is stored in memory.

---

### Task 3: `trade_decision_task` (Executed by `TradeAdvisorAgent`)

*   **Agent's Goal (Refined):** Synthesize market analysis and strategy advice... It meticulously reviews all available information, including historical context recalled from memory, and archives its final decisions for audit and review.
*   **Inputs from Crew Context:** `symbol="BTC-USD"`, `timeframe="4h"`, `strategy_name="DarvasBoxStrategy"`, `strategy_config={...}`, `crew_run_id="mock_task_123_xyz"`. Also receives `market_analysis_object_1` and `strategy_application_object_1` from previous tasks.
*   **Expected Memory Tool Usage (Recall - Recommended):**
    1.  Call: `recall_memories_tool(app_agent_id="mock_task_123_xyz_market_analysis_BTC-USD_4h", query="Retrieve latest market analysis summary for BTC-USD 4h.")`
        *   Tool Output (Conceptual): `{"success": True, ..., "response": "{\"condition\": \"NEUTRAL\", ...}"}`
    2.  Call: `recall_memories_tool(app_agent_id="mock_task_123_xyz_strategy_application_BTC-USD_DarvasBoxStrategy", query="Retrieve latest DarvasBoxStrategy advice for BTC-USD.")`
        *   Tool Output (Conceptual): `{"success": True, ..., "response": "{\"advice\": \"HOLD\", ...}"}`
*   **Expected Primary Tool Usage:**
    *   Call: `assess_trade_risk_tool(symbol="BTC-USD", proposed_action="HOLD", confidence_score=0.6, entry_price=..., stop_loss_price=..., ...)` (using details from `strategy_application_object_1` and market context from `market_analysis_object_1`).
        *   Output: `risk_assessment_json_output_1` (JSON string for `TradeRiskAssessmentOutput`, e.g., `{"risk_level": "LOW", ...}`)
*   **LLM Interaction (Conceptual):**
    *   Receives task description (instructs recall, risk assessment, and then store).
    *   Uses recalled memories, market analysis, strategy advice, and risk assessment output.
    *   Formulates the final `TradingDecision`.
    *   Expected LLM Output (for `TradingDecision`): `{"decision_id": "...", "symbol": "BTC-USD", "action": "HOLD", ...}` (let's call this `trading_decision_object_1`)
*   **Expected Memory Tool Usage (Store - Mandatory):**
    *   The agent is instructed to use `store_memory_tool`.
    *   Call: `store_memory_tool(app_agent_id="mock_task_123_xyz_trade_decision_BTC-USD", observation=json.dumps({"action": "HOLD", "symbol": "BTC-USD", "confidence": 0.65, "reason_summary": "Market neutral, strategy advises HOLD, risk assessment LOW.", "risk_level": "LOW"}), role="user")`
        *   *(Note: Observation is a JSON summary of `trading_decision_object_1`.)*
    *   Tool Output (Conceptual): `{"success": True, ..., "action": "store_memory"}`
*   **Task Output (Final Crew Output):** `trading_decision_object_1` (The full `TradingDecision` Pydantic object as a JSON string).
    *   *Side effect:* A summary of this final decision is stored in memory.

---

This conceptual run demonstrates how memory tools can be integrated into the crew's workflow, allowing agents to build and recall context, potentially improving their decision-making over time or across related tasks. The effectiveness of these memory interactions heavily depends on the LLM's ability to follow the detailed instructions in the task descriptions and the actual capabilities of the `MemoryService` and `letta-client`.
