from ..models.compliance_models import ComplianceRule, ComplianceCheckRequest, ComplianceCheckResult, ViolatedRuleInfo
from ..models.event_bus_models import TradeSignalEventPayload # For type hint
from typing import List, Dict, Any, Optional
from loguru import logger
import uuid # For default rule_id if not provided when creating rules manually

class RegulatoryComplianceService:
    def __init__(self, rules: List[ComplianceRule]):
        self.rules = rules
        logger.info(f"RegulatoryComplianceService initialized with {len(rules)} rules.")
        # For stateful rules like max_daily_trades - this would need a persistent store
        # Example: self._daily_trade_counts: Dict[str, Dict[str, int]] = {} # agent_id -> symbol_date_key -> count
        # For this version, stateful rules are placeholders.

    async def check_action_compliance(self, request: ComplianceCheckRequest) -> ComplianceCheckResult:
        result = ComplianceCheckResult()
        signal = request.trade_signal_payload

        logger.debug(f"Compliance Check for Agent {request.agent_id} (Type: {request.agent_type}), Signal: {signal.symbol}, Action: {signal.action}, Qty: {signal.quantity}, Price: {signal.price_target}")

        for rule in self.rules:
            # Check applicability
            applicable_by_id = True
            if rule.applies_to_agent_id and request.agent_id not in rule.applies_to_agent_id:
                applicable_by_id = False

            applicable_by_type = True
            if rule.applies_to_agent_type and request.agent_type not in rule.applies_to_agent_type:
                applicable_by_type = False

            if not applicable_by_id or not applicable_by_type:
                # logger.debug(f"Rule '{rule.rule_id}' not applicable to agent {request.agent_id} (type {request.agent_type}). Skipping.")
                continue

            logger.debug(f"Applying Rule '{rule.rule_id}' ({rule.description}) to Agent {request.agent_id}")

            violated = False
            reason = ""

            if rule.condition_type == "max_order_value_usd":
                if signal.quantity is not None and signal.price_target is not None:
                    order_value = signal.quantity * signal.price_target
                    limit_value = rule.parameters.get("value", float('inf'))
                    if order_value > limit_value:
                        violated = True
                        reason = f"Order value {order_value:.2f} USD exceeds limit {limit_value} USD."
                else:
                    logger.warning(f"Rule '{rule.rule_id}' (max_order_value_usd) skipped: quantity or price_target missing in signal.")

            elif rule.condition_type == "restricted_symbols":
                restricted_symbols_list = rule.parameters.get("symbols", [])
                if not isinstance(restricted_symbols_list, list):
                    logger.warning(f"Rule '{rule.rule_id}' (restricted_symbols) has invalid 'symbols' parameter type: {type(restricted_symbols_list)}. Expected list. Skipping rule.")
                    continue
                if signal.symbol in restricted_symbols_list:
                    violated = True
                    reason = f"Symbol {signal.symbol} is restricted."

            elif rule.condition_type == "max_daily_trades_for_symbol":
                # This is a placeholder for true stateful daily counting.
                # A real implementation would use a DB or Redis and consider dates.
                # For now, it logs a warning and doesn't enforce.
                # To make it testable for violation, one might add a specific parameter for testing.
                rule_symbol = rule.parameters.get("symbol")
                # limit = rule.parameters.get("limit") # Not used in placeholder

                if rule_symbol is None: # Rule needs a symbol defined to be coherent
                    logger.warning(f"Compliance rule '{rule.rule_id}' (max_daily_trades_for_symbol) is missing 'symbol' in parameters. Skipping rule.")
                    continue

                if signal.symbol == rule_symbol: # Only apply if the rule is for the signal's symbol
                    logger.warning(f"Compliance rule '{rule.rule_id}' ({rule.description}) for symbol {signal.symbol} is a stateful placeholder and does not currently enforce limits. Action allowed by default for this rule.")
                    # Example for testing violation:
                    # if rule.parameters.get("test_violate_if_match", False):
                    #    violated = True
                    #    reason = f"Test violation for max_daily_trades_for_symbol on {signal.symbol}."
                else:
                    # This rule is for a different symbol, so it's not violated by this signal.
                    pass


            if violated:
                logger.warning(f"Compliance Violation for Agent {request.agent_id} on rule '{rule.rule_id}' ({rule.description}). Reason: {reason}")
                result.is_compliant = False
                result.violated_rules.append(ViolatedRuleInfo(rule_id=rule.rule_id, description=rule.description, reason=reason))

        if result.is_compliant:
            logger.info(f"Compliance check PASSED for Agent {request.agent_id}, Action: {request.action_type}, Symbol: {signal.symbol}, Qty: {signal.quantity}, Price: {signal.price_target}")
        else:
            logger.warning(f"Compliance check FAILED for Agent {request.agent_id}, Action: {request.action_type}, Symbol: {signal.symbol}. Violations: {len(result.violated_rules)}")
            for v_rule in result.violated_rules:
                logger.warning(f"  - Violated Rule ID: {v_rule.rule_id}, Description: {v_rule.description}, Reason: {v_rule.reason}")
        return result
