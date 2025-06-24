from typing import Optional, Dict, Any, List
from pydantic import ValidationError as PydanticValidationError # For direct validation if needed, though args_schema handles it
from loguru import logger
import json
from datetime import datetime # For TradeRiskAssessmentOutput timestamp

# Attempt to import the 'tool' decorator from crewai_tools
try:
    from crewai_tools import tool
except ImportError:
    logger.warning("crewai_tools.tool not found. Using a placeholder decorator '@tool_stub'.")
    def tool_stub(name: str, args_schema: Optional[Any] = None, description: Optional[str] = None):
        def decorator(func):
            func.tool_name = name
            func.args_schema = args_schema
            func.description = description
            logger.debug(f"Tool stub '{name}' registered with args_schema: {args_schema}, desc: {description}")
            return func
        return decorator
    tool = tool_stub

# Relative imports for models and enums
try:
    from ..models.crew_models import AssessTradeRiskArgs, TradeRiskAssessmentOutput
    from ..types.trading_types import RiskLevel, TradeAction
except ImportError as e:
    logger.critical(f"Failed to import necessary models/types for risk_assessment_tools: {e}. Tool may not function correctly.")
    # Define placeholders if imports fail for subtask execution context
    from pydantic import BaseModel, Field # Ensure BaseModel and Field are available for placeholders
    class RiskLevel: LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"
    class TradeAction: BUY="BUY"; SELL="SELL"; HOLD="HOLD"; INFO="INFO"
    class AssessTradeRiskArgs(BaseModel):
        symbol: str = Field("default_symbol")
        proposed_action: str = Field(TradeAction.HOLD)
        confidence_score: Optional[float] = None
        entry_price: Optional[float] = None
        stop_loss_price: Optional[float] = None
        take_profit_price: Optional[float] = None
        quantity_or_value: Optional[float] = None # Added
        current_portfolio_value: Optional[float] = None # Added
        existing_position_size: Optional[float] = None # Added
        portfolio_context: Optional[Dict[str, Any]] = None
        market_conditions_summary: Optional[str] = None
    class TradeRiskAssessmentOutput(BaseModel):
        risk_level: str = Field(RiskLevel.MEDIUM)
        warnings: List[str] = Field(default_factory=list)
        max_potential_loss_estimate_percent: Optional[float] = None
        max_potential_loss_value: Optional[float] = None # Added
        suggested_position_size_adjustment_factor: Optional[float] = None # Added
        sanity_checks_passed: bool = True
        assessment_summary: str = Field("Default stub summary")
        timestamp: datetime = Field(default_factory=datetime.utcnow)


@tool(
    "Assess Trade Risk Tool",
    args_schema=AssessTradeRiskArgs,
    description="Assesses the risk of a proposed trading action based on its parameters, and optional market and portfolio context. Returns a structured risk assessment."
)
def assess_trade_risk_tool(
    symbol: str,
    proposed_action: str, # String input, validated by AssessTradeRiskArgs Pydantic model
    confidence_score: Optional[float] = None,
    entry_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None,
    quantity_or_value: Optional[float] = None, # New arg
    current_portfolio_value: Optional[float] = None, # New arg
    existing_position_size: Optional[float] = None, # New arg
    portfolio_context: Optional[Dict[str, Any]] = None,
    market_conditions_summary: Optional[str] = None
) -> str:
    """
    Assesses the risk of a proposed trading action using enhanced parameters.

    Args:
        symbol: The trading symbol.
        proposed_action: The proposed trading action (string: "BUY", "SELL", "HOLD").
        confidence_score: Confidence of the proposed action (0.0 to 1.0).
        entry_price: Proposed entry price.
        stop_loss_price: Proposed stop-loss price.
        take_profit_price: Proposed take-profit price.
        quantity_or_value: Proposed quantity or monetary value of the trade.
        current_portfolio_value: Total current value of the portfolio.
        existing_position_size: Size of any existing position in the same symbol.
        portfolio_context: Additional portfolio context dictionary.
        market_conditions_summary: Text summary of current market conditions.

    Returns:
        A JSON string representing a `TradeRiskAssessmentOutput` Pydantic model.
    """
    logger.info(f"TOOL: Assessing risk for symbol '{symbol}', action '{proposed_action}', confidence {confidence_score}.")
    logger.debug(f"quantity_or_value: {quantity_or_value}, current_portfolio_value: {current_portfolio_value}, existing_position_size: {existing_position_size}")
    if portfolio_context: logger.debug(f"Portfolio context: {str(portfolio_context)[:200]}")
    if market_conditions_summary: logger.debug(f"Market conditions summary: {market_conditions_summary}")

    try:
        # Use the Pydantic model for initial validation of string action to enum
        validated_args = AssessTradeRiskArgs(
            symbol=symbol, proposed_action=proposed_action, confidence_score=confidence_score,
            entry_price=entry_price, stop_loss_price=stop_loss_price, take_profit_price=take_profit_price,
            quantity_or_value=quantity_or_value, current_portfolio_value=current_portfolio_value,
            existing_position_size=existing_position_size, portfolio_context=portfolio_context,
            market_conditions_summary=market_conditions_summary
        )
        action_enum = validated_args.proposed_action
    except PydanticValidationError as e:
        logger.error(f"TOOL: Input validation error for AssessTradeRiskArgs: {e}")
        error_messages = [f"{err['msg']} (Field: {'.'.join(map(str, err['loc']))})" for err in e.errors()]
        err_output = TradeRiskAssessmentOutput(
            risk_level=RiskLevel.HIGH,
            warnings=error_messages,
            assessment_summary=f"Failed to assess risk due to input validation errors: {error_messages[0] if error_messages else 'Unknown validation error'}.",
            sanity_checks_passed=False
        )
        return err_output.model_dump_json(indent=2, exclude_none=True)

    args = validated_args # Use the validated args from now on

    # Initialize variables
    warnings: List[str] = []
    risk_level: RiskLevel = RiskLevel.LOW # Use RiskLevel enum
    assessment_summary: str = ""
    max_potential_loss_value: Optional[float] = None
    max_potential_loss_estimate_percent: Optional[float] = None
    suggested_position_size_adjustment_factor: float = 1.0
    sanity_checks_passed: bool = True

    trade_value: Optional[float] = None
    loss_per_unit: Optional[float] = None # Define loss_per_unit here

    # Handle HOLD action first
    if args.proposed_action == TradeAction.HOLD:
        risk_level = RiskLevel.LOW
        warnings = ["HOLD action proposed, no new market risk assessed."]
        assessment_summary = f"HOLD action for {args.symbol} assessed: Low immediate risk. Market conditions: {args.market_conditions_summary or 'not specified'}."
        # All loss/adjustment factors remain None or default for HOLD
        output = TradeRiskAssessmentOutput(
            risk_level=risk_level.value, # Ensure enum value is passed
            warnings=warnings,
            assessment_summary=assessment_summary,
            sanity_checks_passed=True, # Sanity checks are N/A for HOLD in this context
            timestamp=datetime.utcnow()
            # max_potential_loss_value, max_potential_loss_estimate_percent, suggested_position_size_adjustment_factor default to None/1.0
        )
        return output.model_dump_json(indent=2, exclude_none=True)

    # Trade Value Calculation (assuming quantity_or_value is quantity for BUY/SELL)
    if args.quantity_or_value is not None and args.entry_price is not None:
        trade_value = args.quantity_or_value * args.entry_price



    # Stop-Loss Sanity & Max Loss Calculation
    if args.entry_price is not None and args.stop_loss_price is not None:
        if args.proposed_action == TradeAction.BUY:
            if args.stop_loss_price >= args.entry_price:
                warnings.append("Critical: Stop-loss for BUY order is at or above the entry price.")
                sanity_checks_passed = False
            else:
                loss_per_unit = args.entry_price - args.stop_loss_price
        elif args.proposed_action == TradeAction.SELL:
            if args.stop_loss_price <= args.entry_price:
                warnings.append("Critical: Stop-loss for SELL order is at or below the entry price.")
                sanity_checks_passed = False
            else:
                loss_per_unit = args.stop_loss_price - args.entry_price

        if loss_per_unit is not None and loss_per_unit > 0 and args.quantity_or_value is not None:
            max_potential_loss_value = loss_per_unit * args.quantity_or_value
            if trade_value is not None and trade_value > 0: # trade_value could be zero if entry_price is zero
                max_potential_loss_estimate_percent = round((max_potential_loss_value / trade_value) * 100, 2)

    # Reward/Risk Ratio (RRR) Calculation
    if args.entry_price is not None and args.stop_loss_price is not None and args.take_profit_price is not None and loss_per_unit is not None and loss_per_unit > 0:
        potential_reward_per_unit = None
        if args.proposed_action == TradeAction.BUY and args.take_profit_price > args.entry_price:
            potential_reward_per_unit = args.take_profit_price - args.entry_price
        elif args.proposed_action == TradeAction.SELL and args.take_profit_price < args.entry_price:
            potential_reward_per_unit = args.entry_price - args.take_profit_price

        if potential_reward_per_unit is not None and potential_reward_per_unit > 0:
            rrr = potential_reward_per_unit / loss_per_unit
            if rrr < 1.5: # Configurable threshold
                warnings.append(f"Poor Reward/Risk Ratio ({rrr:.2f}) found, which is less than 1.5.")
                risk_level = max(risk_level, RiskLevel.MEDIUM)
        elif (args.proposed_action == TradeAction.BUY and args.take_profit_price <= args.entry_price) or \
             (args.proposed_action == TradeAction.SELL and args.take_profit_price >= args.entry_price):
            warnings.append("Take-profit price is not logical (e.g., below entry for BUY, or above entry for SELL).")
            sanity_checks_passed = False


    # Position Sizing vs. Portfolio Risk
    if max_potential_loss_value is not None and args.current_portfolio_value is not None and args.current_portfolio_value > 0:
        loss_as_portfolio_percent = (max_potential_loss_value / args.current_portfolio_value) * 100
        if loss_as_portfolio_percent > 2.0: # Configurable max risk per trade %
            warnings.append(f"Potential loss ({loss_as_portfolio_percent:.1f}%) exceeds max risk per trade (2% of portfolio).")
            risk_level = max(risk_level, RiskLevel.HIGH)
            suggested_position_size_adjustment_factor = min(suggested_position_size_adjustment_factor, 0.5)
        elif loss_as_portfolio_percent > 1.0:
            warnings.append(f"Potential loss ({loss_as_portfolio_percent:.1f}%) is moderate (1-2% of portfolio).")
            risk_level = max(risk_level, RiskLevel.MEDIUM)
            suggested_position_size_adjustment_factor = min(suggested_position_size_adjustment_factor, 0.75)


    # Concentration Risk (Simple)
    if args.existing_position_size is not None and args.existing_position_size > 0:
        warnings.append(f"Increasing exposure to an existing position of size {args.existing_position_size} in {args.symbol}.")
        risk_level = max(risk_level, RiskLevel.MEDIUM)

    # Confidence Score Impact
    if args.confidence_score is not None:
        if args.confidence_score < 0.5:
            warnings.append(f"Proposed action has low confidence ({args.confidence_score:.2f}).")
            risk_level = max(risk_level, RiskLevel.MEDIUM) # Changed from HIGH to MEDIUM as per subtask
            suggested_position_size_adjustment_factor = min(suggested_position_size_adjustment_factor, 0.25) # Suggest significant reduction or avoiding
        elif args.confidence_score < 0.7:
            warnings.append(f"Proposed action has moderate confidence ({args.confidence_score:.2f}).")
            risk_level = max(risk_level, RiskLevel.LOW) # No change if already higher
            suggested_position_size_adjustment_factor = min(suggested_position_size_adjustment_factor, 0.75)
    else: # No confidence score provided for a trade action
        warnings.append("Confidence score not provided; risk assessment less certain.")
        risk_level = max(risk_level, RiskLevel.MEDIUM)


    # Market Conditions Impact
    if args.market_conditions_summary and "volatile" in args.market_conditions_summary.lower():
        warnings.append("Market conditions reported as volatile, increasing uncertainty.")
        risk_level = max(risk_level, RiskLevel.MEDIUM)
        suggested_position_size_adjustment_factor = min(suggested_position_size_adjustment_factor, 0.75)

    # Final risk_level if sanity checks failed
    if not sanity_checks_passed:
        risk_level = RiskLevel.HIGH
        # Ensure adjustment factor reflects avoiding trade if sanity fails critically
        suggested_position_size_adjustment_factor = 0.0
        if not any("Critical:" in w for w in warnings): # Add a generic sanity fail warning if not already specific
            warnings.append("Critical: Trade proposal failed basic sanity checks.")


    # Construct assessment_summary
    if warnings:
        assessment_summary = f"Trade for {args.symbol} ({args.proposed_action.value}) assessed with {risk_level.value} risk. Key warnings: {'; '.join(warnings[:3])}"
        if len(warnings) > 3:
            assessment_summary += f" ...and {len(warnings)-3} more."
    else:
        assessment_summary = f"Trade for {args.symbol} ({args.proposed_action.value}) assessed with {risk_level.value} risk. No major warnings from automated checks."

    # If adjustment factor is 1.0, it means no downward adjustment suggested by specific checks.
    # Set to None in output if no adjustment needed, unless sanity failed (then 0.0).
    if suggested_position_size_adjustment_factor == 1.0 and sanity_checks_passed:
        final_adjustment_factor = None
    else:
        final_adjustment_factor = suggested_position_size_adjustment_factor


    output = TradeRiskAssessmentOutput(
        risk_level=risk_level.value, # Ensure enum value is passed
        warnings=warnings,
        max_potential_loss_estimate_percent=max_potential_loss_estimate_percent,
        max_potential_loss_value=max_potential_loss_value,
        suggested_position_size_adjustment_factor=final_adjustment_factor,
        sanity_checks_passed=sanity_checks_passed,
        assessment_summary=assessment_summary,
        timestamp=datetime.utcnow()
    )

    try:
        return output.model_dump_json(indent=2, exclude_none=True)
    except Exception as e:
        logger.error(f"TOOL: Error serializing TradeRiskAssessmentOutput to JSON for {args.symbol}: {e}")
        return json.dumps({"error": "Failed to serialize risk assessment output.", "details": str(e)})


if __name__ == '__main__':
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

    # Example 1: BUY signal, looks reasonable
    args1_dict = {
        "symbol":"AAPL", "proposed_action":"BUY", "confidence_score":0.8, "entry_price":170.0,
        "stop_loss_price":165.0, "quantity_or_value":10, "current_portfolio_value": 50000,
        "market_conditions_summary":"Market is stable."
    }
    logger.info(f"\n--- Example 1: Reasonable BUY ({args1_dict['symbol']}) ---")
    result1_json = assess_trade_risk_tool(**args1_dict)
    logger.info(f"Risk Assessment Tool Output 1:\n{json.dumps(json.loads(result1_json), indent=2)}")

    # Example 2: SELL signal, low confidence, volatile market, large portfolio risk
    args2_dict = {
        "symbol":"TSLA", "proposed_action":"SELL", "confidence_score":0.45, "entry_price":200.0,
        "stop_loss_price":220.0, # 20 loss per share (10%)
        "quantity_or_value": 50, # Trade value 10000, potential loss 1000
        "current_portfolio_value": 20000, # Loss is 5% of portfolio
        "market_conditions_summary":"Market is extremely volatile."
    }
    logger.info(f"\n--- Example 2: Risky SELL ({args2_dict['symbol']}) ---")
    result2_json = assess_trade_risk_tool(**args2_dict)
    logger.info(f"Risk Assessment Tool Output 2:\n{json.dumps(json.loads(result2_json), indent=2)}")

    # Example 3: HOLD signal
    args3_dict = {"symbol":"MSFT", "proposed_action":"HOLD", "confidence_score":0.9}
    logger.info(f"\n--- Example 3: HOLD Action ({args3_dict['symbol']}) ---")
    result3_json = assess_trade_risk_tool(**args3_dict)
    logger.info(f"Risk Assessment Tool Output 3:\n{json.dumps(json.loads(result3_json), indent=2)}")

    # Example 4: Sanity check fail (BUY stop loss above entry)
    args4_dict = {"symbol":"GOOG", "proposed_action":"BUY", "confidence_score":0.9, "entry_price":150.0, "stop_loss_price":155.0, "quantity_or_value":10}
    logger.info(f"\n--- Example 4: Sanity Check Fail ({args4_dict['symbol']}) ---")
    result4_json = assess_trade_risk_tool(**args4_dict)
    logger.info(f"Risk Assessment Tool Output 4:\n{json.dumps(json.loads(result4_json), indent=2)}")

    # Example 5: Existing position warning
    args5_dict = {
        "symbol":"NVDA", "proposed_action":"BUY", "confidence_score":0.75, "entry_price":900.0,
        "stop_loss_price":880.0, "quantity_or_value":5, "current_portfolio_value":100000,
        "existing_position_size": 10 # Already holding 10 shares
    }
    logger.info(f"\n--- Example 5: Existing Position ({args5_dict['symbol']}) ---")
    result5_json = assess_trade_risk_tool(**args5_dict)
    logger.info(f"Risk Assessment Tool Output 5:\n{json.dumps(json.loads(result5_json), indent=2)}")
