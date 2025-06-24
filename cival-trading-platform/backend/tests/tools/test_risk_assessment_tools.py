import pytest
import json
from typing import Dict, Any, Optional, List

from python_ai_services.tools.risk_assessment_tools import assess_trade_risk_tool
# Assuming AssessTradeRiskArgs and TradeRiskAssessmentOutput are in crew_models
from python_ai_services.models.crew_models import AssessTradeRiskArgs, TradeRiskAssessmentOutput
from python_ai_services.types.trading_types import RiskLevel, TradeAction

# --- Tests for assess_trade_risk_tool ---

def test_assess_trade_risk_tool_low_risk_buy():
    """Test with parameters indicative of a low-risk buy."""
    args_dict = {
        "symbol":"GOODCO",
        "proposed_action": TradeAction.BUY.value, # Pass string as LLM would
        "confidence_score":0.85,
        "entry_price":100.0,
        "stop_loss_price":98.0, # 2% stop loss
        "take_profit_price":110.0,
        "quantity_or_value":10, # e.g., 10 shares
        "current_portfolio_value": 50000.0,
        "existing_position_size": 0.0,
        "portfolio_context":{"max_portfolio_risk_percent": 2.0}, # Max 2% of portfolio per trade
        "market_conditions_summary":"Market is stable and trending upwards."
    }

    result_json = assess_trade_risk_tool(**args_dict)

    assert isinstance(result_json, str)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)

    assert parsed_result.risk_level == RiskLevel.LOW
    assert not parsed_result.warnings, f"Expected no warnings, got: {parsed_result.warnings}"
    assert parsed_result.sanity_checks_passed is True
    assert "low risk" in parsed_result.assessment_summary.lower()
    # RRR for this trade: (110-100) / (100-98) = 10 / 2 = 5.0, which is good.
    assert parsed_result.max_potential_loss_estimate_percent == 2.00 # ( (100-98)*10 / (100*10) ) * 100 (loss per unit / entry price per unit)
    assert parsed_result.max_potential_loss_value == (100.0 - 98.0) * 10 # 20.0
    # Portfolio risk: 20.0 / 50000.0 * 100 = 0.04%, which is very low.
    assert parsed_result.suggested_position_size_adjustment_factor is None # Should be None if 1.0 and sanity passed

def test_assess_trade_risk_tool_high_risk_conditions():
    """Test with multiple parameters that trigger high-risk conditions."""
    args_dict = {
        "symbol":"VOLCOIN",
        "proposed_action":"BUY",
        "confidence_score":0.4,
        "entry_price":50.0,
        "stop_loss_price":40.0, # 20% stop loss
        "quantity_or_value": 100, # Trade value 5000
        "current_portfolio_value": 10000, # Max loss 1000 (10% of portfolio)
        "market_conditions_summary":"Market is extremely volatile with negative news."
    }

    result_json = assess_trade_risk_tool(**args_dict)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)

    assert parsed_result.risk_level == RiskLevel.HIGH
    assert len(parsed_result.warnings) >= 3 # Low confidence, volatile market, high portfolio risk
    assert any("low confidence (0.40)" in w.lower() for w in parsed_result.warnings)
    assert any("volatile" in w.lower() for w in parsed_result.warnings)
    # Max loss value = (220-200)*50 = 1000. Trade value = 200*50 = 10000. Max loss estimate % = (1000/10000)*100 = 10%
    # Portfolio risk: 1000 / 20000 * 100 = 5.0%
    assert any("potential loss (5.0%) exceeds max risk per trade (2% of portfolio)" in w.lower() for w in parsed_result.warnings)
    assert parsed_result.max_potential_loss_estimate_percent == 10.0 # ( (220-200) / 200 ) * 100, assuming stop loss is per unit
    assert parsed_result.max_potential_loss_value == (220.0 - 200.0) * 50 # 1000.0
    # Factor from low confidence (0.25) vs factor from portfolio risk (0.5). Min is 0.25
    assert parsed_result.suggested_position_size_adjustment_factor == 0.25

def test_assess_trade_risk_tool_sanity_check_fail_buy():
    args_dict = {
        "symbol":"BADSL", "proposed_action":"BUY", "confidence_score":0.9,
        "entry_price":100.0, "stop_loss_price":105.0, "quantity_or_value":10
    }
    result_json = assess_trade_risk_tool(**args_dict)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)

    assert parsed_result.risk_level == RiskLevel.HIGH
    assert parsed_result.sanity_checks_passed is False
    assert any("stop-loss for buy order is at or above the entry price" in w.lower() for w in parsed_result.warnings)
    assert parsed_result.suggested_position_size_adjustment_factor == 0.0

def test_assess_trade_risk_tool_sanity_check_fail_sell():
    args_dict = {
        "symbol":"BADSLSELL", "proposed_action":"SELL", "confidence_score":0.9,
        "entry_price":100.0, "stop_loss_price":95.0, "quantity_or_value":10
    }
    result_json = assess_trade_risk_tool(**args_dict)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)

    assert parsed_result.risk_level == RiskLevel.HIGH
    assert parsed_result.sanity_checks_passed is False
    assert any("stop-loss for sell order is at or below the entry price" in w.lower() for w in parsed_result.warnings)
    assert parsed_result.suggested_position_size_adjustment_factor == 0.0

def test_assess_trade_risk_tool_hold_action():
    args_dict = {
        "symbol":"STABLECO", "proposed_action":"HOLD", "confidence_score":0.95,
        "market_conditions_summary":"Market is choppy, recommending hold."
    }
    result_json = assess_trade_risk_tool(**args_dict)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)

    assert parsed_result.risk_level == RiskLevel.LOW
    assert len(parsed_result.warnings) == 1 # "HOLD action proposed..."
    assert "hold action proposed" in parsed_result.warnings[0].lower()
    assert f"hold action for {args_dict['symbol']} assessed: low immediate risk" in parsed_result.assessment_summary.lower()
    assert parsed_result.max_potential_loss_estimate_percent is None
    assert parsed_result.max_potential_loss_value is None
    assert parsed_result.suggested_position_size_adjustment_factor is None # None for HOLD


def test_assess_trade_risk_tool_high_portfolio_risk_triggers_adjustment():
    args_dict = {
        "symbol":"PORTFOLIORISK", "proposed_action":"BUY", "confidence_score":0.75, # Medium confidence
        "entry_price":100.0, "stop_loss_price":95.0, # 5% SL on price
        "quantity_or_value":30, # Trade value = 30 * 100 = 3000
        "current_portfolio_value":10000.0 # Potential loss = (100-95)*30 = 150. 150/10000 = 1.5% of portfolio
    }
    result_json = assess_trade_risk_tool(**args_dict)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)
    assert parsed_result.risk_level == RiskLevel.MEDIUM
    assert any("potential loss (1.5%) is moderate (1-2% of portfolio)" in w.lower() for w in parsed_result.warnings)
    # Confidence 0.75 (factor 0.75), portfolio risk 1.5% (factor 0.75). Min is 0.75
    assert parsed_result.suggested_position_size_adjustment_factor == 0.75

    args_dict["quantity_or_value"] = 50 # Trade value = 5000, Potential loss = 250 (2.5% of portfolio)
    result_json_2 = assess_trade_risk_tool(**args_dict)
    data2 = json.loads(result_json_2)
    parsed_result_2 = TradeRiskAssessmentOutput(**data2)
    assert parsed_result_2.risk_level == RiskLevel.HIGH
    assert any("potential loss (2.5%) exceeds max risk per trade (2% of portfolio)" in w.lower() for w in parsed_result_2.warnings)
    # Confidence 0.75 (factor 0.75), portfolio risk 2.5% (factor 0.5). Min is 0.5
    assert parsed_result_2.suggested_position_size_adjustment_factor == 0.5


def test_assess_trade_risk_tool_with_existing_position():
    args_dict = {
        "symbol":"EXISTING", "proposed_action":"BUY", "confidence_score":0.8,
        "entry_price":200.0, "stop_loss_price":190.0, "quantity_or_value":5,
        "current_portfolio_value":20000.0, "existing_position_size": 10.0
    }
    result_json = assess_trade_risk_tool(**args_dict)
    data = json.loads(result_json)
    parsed_result = TradeRiskAssessmentOutput(**data)
    assert any("existing position" in w.lower() for w in parsed_result.warnings)
    assert parsed_result.risk_level == RiskLevel.MEDIUM # Existing position escalates to medium


def test_assess_trade_risk_tool_rrr_calculation_and_impact():
    """Test Reward/Risk Ratio calculation and its impact."""
    # Good RRR
    args_good_rrr = {
        "symbol":"GOODRRR", "proposed_action":"BUY", "confidence_score":0.8,
        "entry_price":100.0, "stop_loss_price":95.0, # Loss per unit = 5
        "take_profit_price":115.0, # Reward per unit = 15. RRR = 15/5 = 3.0
        "quantity_or_value":10, "current_portfolio_value":100000
    }
    result_json_good = assess_trade_risk_tool(**args_good_rrr)
    data_good = json.loads(result_json_good)
    parsed_good = TradeRiskAssessmentOutput(**data_good)
    assert parsed_good.risk_level == RiskLevel.LOW # Assuming other factors are low
    assert not any("poor reward/risk ratio" in w.lower() for w in parsed_good.warnings)

    # Poor RRR
    args_poor_rrr = {**args_good_rrr, "symbol":"POORRRR", "take_profit_price":105.0} # Reward per unit = 5. RRR = 5/5 = 1.0
    result_json_poor = assess_trade_risk_tool(**args_poor_rrr)
    data_poor = json.loads(result_json_poor)
    parsed_poor = TradeRiskAssessmentOutput(**data_poor)
    assert parsed_poor.risk_level == RiskLevel.MEDIUM
    assert any("poor reward/risk ratio (1.00) found, which is less than 1.5" in w.lower() for w in parsed_poor.warnings)

    # Illogical Take Profit for BUY
    args_illogical_tp_buy = {**args_good_rrr, "symbol":"ILLOGICALTPBUY", "take_profit_price":90.0} # TP below entry for BUY
    result_json_ill_buy = assess_trade_risk_tool(**args_illogical_tp_buy)
    data_ill_buy = json.loads(result_json_ill_buy)
    parsed_ill_buy = TradeRiskAssessmentOutput(**data_ill_buy)
    assert parsed_ill_buy.sanity_checks_passed is False
    assert parsed_ill_buy.risk_level == RiskLevel.HIGH
    assert any("take-profit price is not logical" in w.lower() for w in parsed_ill_buy.warnings)

    # Illogical Take Profit for SELL
    args_illogical_tp_sell = {
        "symbol":"ILLOGICALTPSELL", "proposed_action":"SELL", "confidence_score":0.8,
        "entry_price":100.0, "stop_loss_price":105.0, # Loss per unit = 5
        "take_profit_price":110.0, # TP above entry for SELL
        "quantity_or_value":10, "current_portfolio_value":100000
    }
    result_json_ill_sell = assess_trade_risk_tool(**args_illogical_tp_sell)
    data_ill_sell = json.loads(result_json_ill_sell)
    parsed_ill_sell = TradeRiskAssessmentOutput(**data_ill_sell)
    assert parsed_ill_sell.sanity_checks_passed is False
    assert parsed_ill_sell.risk_level == RiskLevel.HIGH
    assert any("take-profit price is not logical" in w.lower() for w in parsed_ill_sell.warnings)


def test_assess_trade_risk_tool_confidence_score_impacts():
    # Low confidence
    args_low_conf = {"symbol":"LOWCONF", "proposed_action":"BUY", "confidence_score":0.4, "entry_price":10, "stop_loss_price":9, "quantity_or_value":1}
    res_low_conf = json.loads(assess_trade_risk_tool(**args_low_conf))
    assert res_low_conf["risk_level"] == RiskLevel.MEDIUM
    assert any("low confidence (0.40)" in w.lower() for w in res_low_conf["warnings"])
    assert res_low_conf["suggested_position_size_adjustment_factor"] == 0.25

    # Moderate confidence
    args_mod_conf = {"symbol":"MODCONF", "proposed_action":"BUY", "confidence_score":0.6, "entry_price":10, "stop_loss_price":9, "quantity_or_value":1}
    res_mod_conf = json.loads(assess_trade_risk_tool(**args_mod_conf))
    assert res_mod_conf["risk_level"] == RiskLevel.LOW # Assuming other factors are low
    assert any("moderate confidence (0.60)" in w.lower() for w in res_mod_conf["warnings"])
    assert res_mod_conf["suggested_position_size_adjustment_factor"] == 0.75

    # No confidence score
    args_no_conf = {"symbol":"NOCONF", "proposed_action":"BUY", "entry_price":10, "stop_loss_price":9, "quantity_or_value":1}
    res_no_conf = json.loads(assess_trade_risk_tool(**args_no_conf))
    assert res_no_conf["risk_level"] == RiskLevel.MEDIUM
    assert any("confidence score not provided" in w.lower() for w in res_no_conf["warnings"])


def test_assess_trade_risk_tool_market_conditions_impact():
    args_volatile = {
        "symbol":"VOLMKT", "proposed_action":"BUY", "confidence_score":0.8,
        "entry_price":100, "stop_loss_price":98, "quantity_or_value":1,
        "market_conditions_summary":"Crypto market is extremely volatile today."
    }
    res_volatile = json.loads(assess_trade_risk_tool(**args_volatile))
    assert res_volatile["risk_level"] == RiskLevel.MEDIUM
    assert any("volatile" in w.lower() for w in res_volatile["warnings"])
    assert res_volatile["suggested_position_size_adjustment_factor"] == 0.75 # Adjusted due to volatility


def test_assess_trade_risk_tool_no_adjustment_factor_if_no_issues():
    args_perfect = {
        "symbol":"PERFECT", "proposed_action":"BUY", "confidence_score":0.9,
        "entry_price":100.0, "stop_loss_price":98.0, "take_profit_price":110.0, # Good RRR
        "quantity_or_value":1, "current_portfolio_value":100000, # Low portfolio risk
        "market_conditions_summary":"Stable"
    }
    res_perfect = json.loads(assess_trade_risk_tool(**args_perfect))
    assert res_perfect["risk_level"] == RiskLevel.LOW
    assert not res_perfect["warnings"]
    assert res_perfect["suggested_position_size_adjustment_factor"] is None # Should be None if 1.0 and sanity passed


def test_assess_trade_risk_tool_args_schema():
    if hasattr(assess_trade_risk_tool, 'args_schema'):
        assert assess_trade_risk_tool.args_schema == AssessTradeRiskArgs
    elif hasattr(assess_trade_risk_tool, '_crew_tool_input_schema'):
         assert assess_trade_risk_tool._crew_tool_input_schema == AssessTradeRiskArgs
    else:
        pytest.skip("Tool schema attribute not found.")

def test_assess_trade_risk_tool_invalid_input_via_pydantic_schema():
    """Test that invalid input caught by Pydantic schema within the tool returns error JSON."""
    # Example: proposed_action is an invalid string not in TradeAction enum
    args_dict_invalid_action = {
        "symbol":"INVALIDACTION", "proposed_action":"MAYBEBUY", "confidence_score":0.7
    }
    result_json = assess_trade_risk_tool(**args_dict_invalid_action)
    data = json.loads(result_json)
    assert "error" in data
    assert "Failed to assess risk due to input validation errors" in data["assessment_summary"]
    assert any("Input tag 'MAYBEBUY' found using 'str_to_instance'" in detail_msg for detail_msg in data["warnings"])

