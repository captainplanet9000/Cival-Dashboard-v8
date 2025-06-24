from typing import Optional, Any
from pydantic import BaseModel, Field, ValidationError, model_validator, confloat, conint
from loguru import logger
from enum import Enum

class DarvasBoxConfig(BaseModel):
    """
    Configuration parameters for the Darvas Box trading strategy.

    This model defines the settings used to identify Darvas Boxes,
    confirm breakouts, and set initial stop-loss levels.
    """
    lookback_period_highs: int = Field(
        default=252,
        description="Lookback period (in trading days, approx. 1 year) for identifying new 52-week highs.",
        gt=0
    )
    box_definition_period: int = Field(
        default=10,
        description="Lookback period (in trading days) from a new high to define the potential box top and subsequent bottom.",
        gt=0
    )
    volume_increase_factor: float = Field(
        default=1.5,
        description="Minimum factor by which volume must increase on breakout compared to an average (e.g., 1.5 for 50% increase over avg volume).",
        gt=0
    )
    box_range_tolerance_percent: float = Field(
        default=1.0,
        description="Tolerance (as a percentage of price) for minor penetrations of box boundaries that don't invalidate the box.",
        ge=0,
        le=10
    )
    min_box_duration: int = Field(
        default=3,
        description="Minimum number of trading days a potential box must consolidate (price stays within top and bottom) before a breakout is considered valid.",
        gt=0
    )
    stop_loss_percent_from_bottom: float = Field(
        default=2.0,
        description="Percentage below the confirmed box bottom to set the initial stop-loss after a breakout.",
        gt=0,
        le=10
    )

    class Config:
        extra = "forbid"
        use_enum_values = True


class WilliamsAlligatorConfig(BaseModel):
    """
    Configuration parameters for the Williams Alligator trading indicator.

    This model defines the periods and shifts for the Jaw, Teeth, and Lips
    smoothed moving averages that make up the Alligator indicator.
    """
    jaw_period: int = Field(default=13, description="Period for the Jaw (blue line) smoothed moving average.", gt=0)
    jaw_shift: int = Field(default=8, description="Shift for the Jaw (blue line). Represents future offset.", ge=0)
    teeth_period: int = Field(default=8, description="Period for the Teeth (red line) smoothed moving average.", gt=0)
    teeth_shift: int = Field(default=5, description="Shift for the Teeth (red line). Represents future offset.", ge=0)
    lips_period: int = Field(default=5, description="Period for the Lips (green line) smoothed moving average.", gt=0)
    lips_shift: int = Field(default=3, description="Shift for the Lips (green line). Represents future offset.", ge=0)
    price_source_column: str = Field(default="close", description="Column name in OHLCV data to use for calculating averages (e.g., 'close', 'hlc3').")

    class Config:
        extra = "forbid"
        use_enum_values = True


class RenkoBrickSizeMethod(str, Enum):
    """Method to determine Renko brick size."""
    FIXED = "fixed"
    ATR = "atr"


class RenkoConfig(BaseModel):
    """
    Configuration parameters for generating Renko charts/bricks.
    """
    brick_size_method: RenkoBrickSizeMethod = Field(
        default=RenkoBrickSizeMethod.ATR,
        description="Method to determine Renko brick size ('fixed' or 'atr')."
    )
    brick_size_value: Optional[float] = Field(
        default=None,
        description="Brick size if method is 'fixed'. Must be a positive float if set."
    )
    atr_period: int = Field(
        default=14,
        description="Period for ATR calculation if method is 'atr'.",
        gt=0
    )
    price_source_column: str = Field(
        default="close",
        description="Column name in OHLCV data to use for Renko brick calculations (typically 'close' or 'hl')."
    )

    class Config:
        extra = "forbid"
        use_enum_values = True

<<<<<<< HEAD
    @model_validator(mode='after')
    def check_fixed_brick_size_value(cls, values: Any) -> Any:
        if isinstance(values, BaseModel):
            method = values.brick_size_method
            val = values.brick_size_value

            if method == RenkoBrickSizeMethod.FIXED:
                if val is None or val <= 0:
                    raise ValueError("brick_size_value must be a positive float when brick_size_method is 'fixed'.")
        return values


class HeikinAshiConfig(BaseModel):
    """
    Configuration parameters for Heikin Ashi based signal generation or analysis.

    Defines settings for identifying trends based on consecutive Heikin Ashi
    candle colors and wick sizes, and optional additional smoothing.
    """
    min_trend_candles: int = Field(
        default=3,
        description="Minimum number of consecutive Heikin Ashi candles of the same color to confirm a strong trend.",
        gt=1
    )
    small_wick_threshold_percent: float = Field(
        default=10.0,
        description="Percentage of the Heikin Ashi candle body size. Wicks smaller than this threshold (relative to body size) are considered 'small', often indicating trend strength.",
        ge=0.0,
        le=100.0
    )
    price_smoothing_period: Optional[int] = Field(
        default=None,
        description="Optional period for additional smoothing of Heikin Ashi Open/High/Low/Close prices (e.g., applying an SMA). If None, no extra smoothing is applied.",
        # gt=0 if Field is not None else None # Pydantic v1 style conditional validation
        # For Pydantic v2, if this needs to be >0 when set, a model_validator would be better.
        # For now, allow positive integer if set.
        gt=0 # This will apply if not None. If None, it's fine.
    )

    class Config:
        extra = "forbid"
        use_enum_values = True # For any future enums

    @model_validator(mode='after')
    def check_smoothing_period(cls, values: Any) -> Any:
        if isinstance(values, BaseModel):
            if values.price_smoothing_period is not None and values.price_smoothing_period <= 0:
                 raise ValueError("price_smoothing_period must be a positive integer if provided.")
        return values


if __name__ == '__main__':
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

    # --- Darvas Box Examples ---
    logger.info("--- Default Darvas Box Configuration ---")
    default_darvas_config = DarvasBoxConfig()
    logger.info(default_darvas_config.model_dump_json(indent=2))
    # ... (other Darvas examples remain) ...
    custom_darvas_data = {
            "lookback_period_highs": 200, "box_definition_period": 7,
            "volume_increase_factor": 2.0, "box_range_tolerance_percent": 0.5,
            "min_box_duration": 4, "stop_loss_percent_from_bottom": 1.5
    } # Defined for brevity for later examples

    # --- Williams Alligator Examples ---
    logger.info("\n\n--- Default Williams Alligator Configuration ---")
    default_alligator_config = WilliamsAlligatorConfig()
    logger.info(default_alligator_config.model_dump_json(indent=2))
    # ... (other Alligator examples remain) ...
    custom_alligator_data = {
            "jaw_period": 21, "jaw_shift": 13, "teeth_period": 13, "teeth_shift": 8,
            "lips_period": 8, "lips_shift": 5, "price_source_column": "hlc3"
    }

    # --- Renko Config Examples ---
    logger.info("\n\n--- Default Renko Configuration (ATR) ---")
    default_renko_config = RenkoConfig()
    logger.info(default_renko_config.model_dump_json(indent=2))
    # ... (other Renko examples remain) ...

    # --- Heikin Ashi Config Examples ---
    logger.info("\n\n--- Default Heikin Ashi Configuration ---")
    default_ha_config = HeikinAshiConfig()
    logger.info(default_ha_config.model_dump_json(indent=2))

    logger.info("\n--- Custom Heikin Ashi Configuration ---")
    try:
        custom_ha_data = {
            "min_trend_candles": 5,
            "small_wick_threshold_percent": 5.0,
            "price_smoothing_period": 3
        }
        custom_ha_config = HeikinAshiConfig(**custom_ha_data)
        logger.info(custom_ha_config.model_dump_json(indent=2))
    except ValidationError as e:
        logger.error(f"Error creating custom Heikin Ashi config: {e}")

    logger.info("\n--- Invalid Heikin Ashi Configuration (min_trend_candles too small) ---")
    try:
        invalid_ha_data_value = {**custom_ha_data, "min_trend_candles": 1}
        HeikinAshiConfig(**invalid_ha_data_value)
    except ValidationError as e:
        logger.error(f"Error creating invalid HA config (min_trend_candles) (as expected): {e}")

    logger.info("\n--- Invalid Heikin Ashi Configuration (price_smoothing_period zero) ---")
    try:
        invalid_ha_data_smoothing = {**custom_ha_data, "price_smoothing_period": 0}
        HeikinAshiConfig(**invalid_ha_data_smoothing)
    except ValidationError as e: # This will be caught by the model_validator
        logger.error(f"Error creating invalid HA config (price_smoothing_period) (as expected): {e}")

    logger.info("\n--- Invalid Heikin Ashi Configuration (extra field) ---")
    try:
        invalid_ha_data_extra = {**custom_ha_data, "unexpected_field": True}
        HeikinAshiConfig(**invalid_ha_data_extra)
    except ValidationError as e:
        logger.error(f"Error creating invalid HA config (extra field) (as expected): {e}")


class ElliottWaveConfig(BaseModel):
    """
    Configuration parameters for the Elliott Wave analysis (stub implementation).

    These parameters define rules for identifying potential Elliott Wave patterns,
    focusing on simplified impulse and corrective wave characteristics.
    Note: True Elliott Wave analysis is complex and subjective; this config supports a basic, rule-based heuristic.
    """
    price_source_column: str = Field(
        default="close",
        description="Price column to use for swing detection (e.g., 'close', 'hlc3')."
    )
    zigzag_threshold_percent: float = Field(
        default=5.0,
        description="Minimum percentage change to define a new leg in Zigzag pattern for swing detection.",
        gt=0,
        le=100
    )

    # Impulse Wave Rules (simplified placeholders)
    wave2_max_retracement_w1: confloat(ge=0.0, le=1.0) = Field(
        default=0.786, # Common Fibonacci level, cannot exceed 100% of Wave 1
        description="Wave 2 max retracement of Wave 1 (e.g., 0.618, 0.786). Cannot exceed 1.0 (100% retracement)."
    )
    wave3_min_extension_w1: confloat(gt=0.0) = Field(
        default=1.618, # Wave 3 is often the longest and strongest, minimum 1.618 of Wave 1
        description="Wave 3 min extension of Wave 1 (e.g., 1.618, 2.618). Must be > Wave 1 length (conceptual)."
    )
    wave4_max_retracement_w3: confloat(ge=0.0, le=1.0) = Field(
        default=0.5, # Common Fibonacci level, cannot exceed 100% of Wave 3
        description="Wave 4 max retracement of Wave 3 (e.g., 0.382, 0.5). Cannot exceed 1.0."
    )
    wave4_overlap_w1_allowed: bool = Field(
        default=False,
        description="Whether Wave 4 is allowed to overlap with Wave 1 price territory (typically not in impulses)."
    )
    wave5_min_equality_w1_or_extension_w1w3: Optional[confloat(gt=0.0)] = Field(
        default=0.618, # Can be equal to W1, or an extension of W1-W3 distance, or other relations
        description="Wave 5 target: min equality to W1 (e.g. 1.0) or min extension of W1-W3 distance (e.g. 0.618)."
    )

    # Corrective Wave Rules (ABC - even more simplified placeholders)
    waveB_max_retracement_wA: confloat(ge=0.0, le=1.0) = Field(
        default=0.786,
        description="Wave B max retracement of Wave A in a correction."
    )
    waveC_min_equality_wA_or_extension_wA: confloat(gt=0.0) = Field(
        default=1.0,
        description="Wave C target: min equality to W_A (e.g. 1.0) or min extension of W_A (e.g. 1.618)."
    )

    max_waves_to_identify: conint(ge=3, le=5) = Field(
        default=5,
        description="Maximum number of impulse waves (3 or 5) the stub might attempt to identify conceptually."
    )

    class Config:
        extra = "forbid"
        use_enum_values = True


    # --- Elliott Wave Config Examples ---
    logger.info("\n\n--- Default Elliott Wave Configuration ---")
    default_ew_config = ElliottWaveConfig()
    logger.info(default_ew_config.model_dump_json(indent=2))

    logger.info("\n--- Custom Elliott Wave Configuration ---")
    try:
        custom_ew_data = {
            "price_source_column": "hlc3",
            "zigzag_threshold_percent": 3.0,
            "wave2_max_retracement_w1": 0.618,
            "wave3_min_extension_w1": 2.0,
            "wave4_max_retracement_w3": 0.382,
            "wave4_overlap_w1_allowed": True, # For some commodities or specific market conditions
            "max_waves_to_identify": 3
        }
        custom_ew_config = ElliottWaveConfig(**custom_ew_data)
        logger.info(custom_ew_config.model_dump_json(indent=2))
    except ValidationError as e:
        logger.error(f"Error creating custom Elliott Wave config: {e}")

    logger.info("\n--- Invalid Elliott Wave Configuration (zigzag_threshold_percent too high) ---")
    try:
        invalid_ew_data_zigzag = {**custom_ew_data, "zigzag_threshold_percent": 150.0}
        ElliottWaveConfig(**invalid_ew_data_zigzag)
    except ValidationError as e:
        logger.error(f"Error creating invalid EW config (zigzag_threshold_percent) (as expected): {e}")

    logger.info("\n--- Invalid Elliott Wave Configuration (wave2_max_retracement_w1 > 1.0) ---")
    try:
        invalid_ew_data_w2_retracement = {**custom_ew_data, "wave2_max_retracement_w1": 1.1}
        ElliottWaveConfig(**invalid_ew_data_w2_retracement)
    except ValidationError as e:
        logger.error(f"Error creating invalid EW config (wave2_max_retracement_w1) (as expected): {e}")

    logger.info("\n--- Invalid Elliott Wave Configuration (extra field) ---")
    try:
        invalid_ew_data_extra = {**custom_ew_data, "non_existent_parameter": "invalid"}
        ElliottWaveConfig(**invalid_ew_data_extra)
    except ValidationError as e:
        logger.error(f"Error creating invalid EW config (extra field) (as expected): {e}")

import uuid
from datetime import datetime

class StrategyGoalAlignment(BaseModel):
    alignment_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    strategy_id: uuid.UUID
    goal_id: uuid.UUID
    # How well this strategy is expected to contribute to the goal
    expected_contribution_score: Optional[float] = Field(default=None, ge=0, le=1)
    notes: Optional[str] = None

class StrategyTimeframe(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"

class StrategyPerformanceTeaser(BaseModel):
    # From StrategyConfig
    strategy_id: uuid.UUID
    strategy_name: str
    strategy_type: str
    is_active: bool
    symbols: List[str]
    timeframe: StrategyTimeframe

    # From latest PerformanceMetrics
    latest_performance_record_timestamp: Optional[datetime] = None
    latest_net_profit_percentage: Optional[float] = None
    latest_sharpe_ratio: Optional[float] = None
    latest_sortino_ratio: Optional[float] = None
    latest_max_drawdown_percentage: Optional[float] = None
    total_trades_from_latest_metrics: Optional[int] = None

    class Config:
        from_attributes = True
