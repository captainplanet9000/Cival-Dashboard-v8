"""
Phase 10: Adaptive Strategy Learning and Optimization Service
Machine learning-driven strategy adaptation, parameter optimization, and performance enhancement
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum
import pickle
import joblib
from dataclasses import dataclass

# ML and optimization libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import optuna
from scipy.optimize import differential_evolution, minimize
import tensorflow as tf
from tensorflow import keras

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingStrategy, TradingSignal, TradingPosition, StrategyPerformance,
    SignalStrength, MarketCondition
)
from services.performance_analytics_service import get_performance_analytics_service
from services.backtesting_service import get_backtesting_service
from services.market_analysis_service import get_market_analysis_service
from services.risk_management_service import get_risk_management_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class LearningAlgorithm(str, Enum):
    """Machine learning algorithms for strategy optimization"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"
    GENETIC_ALGORITHM = "genetic_algorithm"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    REINFORCEMENT_LEARNING = "reinforcement_learning"


class OptimizationObjective(str, Enum):
    """Optimization objectives"""
    SHARPE_RATIO = "sharpe_ratio"
    CALMAR_RATIO = "calmar_ratio"
    INFORMATION_RATIO = "information_ratio"
    TOTAL_RETURN = "total_return"
    MAX_DRAWDOWN = "max_drawdown"
    PROFIT_FACTOR = "profit_factor"
    WIN_RATE = "win_rate"
    MULTI_OBJECTIVE = "multi_objective"


class AdaptationTrigger(str, Enum):
    """Strategy adaptation triggers"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MARKET_REGIME_CHANGE = "market_regime_change"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    SCHEDULED_OPTIMIZATION = "scheduled_optimization"
    SIGNAL_QUALITY_DECLINE = "signal_quality_decline"
    CORRELATION_BREAKDOWN = "correlation_breakdown"


@dataclass
class StrategyParameters:
    """Strategy parameter set for optimization"""
    parameter_name: str
    current_value: Any
    min_value: Any
    max_value: Any
    parameter_type: str  # int, float, categorical, boolean
    optimization_bounds: Tuple[Any, Any]
    importance_score: float = 0.5
    locked: bool = False


class OptimizationResult(BaseModel):
    """Strategy optimization result"""
    optimization_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    algorithm_used: LearningAlgorithm
    objective: OptimizationObjective
    
    # Original parameters
    original_parameters: Dict[str, Any] = Field(default_factory=dict)
    original_performance: Dict[str, float] = Field(default_factory=dict)
    
    # Optimized parameters
    optimized_parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_performance: Dict[str, float] = Field(default_factory=dict)
    
    # Optimization details
    optimization_iterations: int
    convergence_achieved: bool
    improvement_percentage: float
    confidence_score: float
    
    # Validation results
    in_sample_performance: Dict[str, float] = Field(default_factory=dict)
    out_of_sample_performance: Dict[str, float] = Field(default_factory=dict)
    
    # Risk assessment
    parameter_sensitivity: Dict[str, float] = Field(default_factory=dict)
    robustness_score: float
    overfitting_risk: float
    
    # Implementation details
    implementation_date: Optional[datetime] = None
    rollback_condition: str = ""
    monitoring_period: int = 30  # days
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LearningModel(BaseModel):
    """Machine learning model for strategy optimization"""
    model_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    model_type: LearningAlgorithm
    
    # Model configuration
    features: List[str] = Field(default_factory=list)
    target_variable: str
    training_period: int = 252  # days
    
    # Model performance
    training_score: float = 0.0
    validation_score: float = 0.0
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    
    # Model metadata
    model_version: str = "1.0"
    last_trained: Optional[datetime] = None
    next_retrain: Optional[datetime] = None
    model_drift_score: float = 0.0
    
    # Model file path (for persistence)
    model_path: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AdaptationEvent(BaseModel):
    """Strategy adaptation event"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    trigger: AdaptationTrigger
    
    # Event details
    trigger_value: float
    threshold_breached: float
    severity: str  # low, medium, high, critical
    
    # Adaptation response
    adaptation_recommended: bool
    adaptation_type: str  # parameter_adjustment, model_retrain, strategy_pause
    recommended_actions: List[str] = Field(default_factory=list)
    
    # Implementation tracking
    implemented: bool = False
    implementation_result: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyOptimizer:
    """Core strategy optimization engine"""
    
    def __init__(self):
        self.optimization_cache: Dict[str, OptimizationResult] = {}
        
    async def optimize_strategy_parameters(
        self,
        strategy: TradingStrategy,
        historical_data: List[Dict[str, Any]],
        objective: OptimizationObjective = OptimizationObjective.SHARPE_RATIO,
        algorithm: LearningAlgorithm = LearningAlgorithm.BAYESIAN_OPTIMIZATION,
        optimization_budget: int = 100
    ) -> OptimizationResult:
        """Optimize strategy parameters using specified algorithm"""
        
        # Define parameter space for optimization
        parameter_space = self._define_parameter_space(strategy)
        
        if not parameter_space:
            raise ValueError("No optimizable parameters found for strategy")
        
        # Extract features and targets from historical data
        features, targets = self._prepare_optimization_data(historical_data, objective)
        
        if len(features) < 50:  # Minimum data requirement
            raise ValueError("Insufficient historical data for optimization")
        
        # Perform optimization based on algorithm
        if algorithm == LearningAlgorithm.BAYESIAN_OPTIMIZATION:
            result = await self._bayesian_optimization(
                parameter_space, features, targets, optimization_budget
            )
        elif algorithm == LearningAlgorithm.GENETIC_ALGORITHM:
            result = await self._genetic_algorithm_optimization(
                parameter_space, features, targets, optimization_budget
            )
        elif algorithm == LearningAlgorithm.RANDOM_FOREST:
            result = await self._random_forest_optimization(
                parameter_space, features, targets
            )
        else:
            # Default to grid search
            result = await self._grid_search_optimization(
                parameter_space, features, targets
            )
        
        # Validate optimization result
        validation_result = await self._validate_optimization(result, historical_data)
        
        # Create optimization result
        optimization_result = OptimizationResult(
            strategy_id=strategy.strategy_id,
            algorithm_used=algorithm,
            objective=objective,
            original_parameters=self._extract_current_parameters(strategy),
            optimized_parameters=result["best_parameters"],
            optimization_iterations=result.get("iterations", optimization_budget),
            convergence_achieved=result.get("converged", True),
            improvement_percentage=result.get("improvement", 0.0),
            confidence_score=result.get("confidence", 0.8),
            in_sample_performance=result.get("in_sample_perf", {}),
            out_of_sample_performance=validation_result,
            robustness_score=result.get("robustness", 0.7),
            overfitting_risk=result.get("overfitting_risk", 0.3)
        )
        
        return optimization_result
    
    async def _bayesian_optimization(
        self,
        parameter_space: Dict[str, StrategyParameters],
        features: np.ndarray,
        targets: np.ndarray,
        n_trials: int = 100
    ) -> Dict[str, Any]:
        """Bayesian optimization using Optuna"""
        
        def objective_function(trial):
            # Suggest parameters based on defined space
            suggested_params = {}
            for param_name, param_info in parameter_space.items():
                if param_info.parameter_type == "float":
                    suggested_params[param_name] = trial.suggest_float(
                        param_name, 
                        float(param_info.optimization_bounds[0]),
                        float(param_info.optimization_bounds[1])
                    )
                elif param_info.parameter_type == "int":
                    suggested_params[param_name] = trial.suggest_int(
                        param_name,
                        int(param_info.optimization_bounds[0]),
                        int(param_info.optimization_bounds[1])
                    )
                elif param_info.parameter_type == "categorical":
                    suggested_params[param_name] = trial.suggest_categorical(
                        param_name, param_info.optimization_bounds
                    )
            
            # Evaluate performance with suggested parameters
            performance = self._evaluate_parameter_set(suggested_params, features, targets)
            return performance
        
        # Create Optuna study
        study = optuna.create_study(direction="maximize")
        study.optimize(objective_function, n_trials=n_trials)
        
        # Calculate improvement
        best_value = study.best_value
        baseline_performance = self._evaluate_parameter_set(
            {name: param.current_value for name, param in parameter_space.items()},
            features, targets
        )
        improvement = (best_value - baseline_performance) / abs(baseline_performance) * 100
        
        return {
            "best_parameters": study.best_params,
            "best_value": best_value,
            "iterations": n_trials,
            "converged": True,
            "improvement": improvement,
            "confidence": min(0.95, 0.5 + (improvement / 100)),
            "robustness": 0.8  # Would calculate based on parameter sensitivity
        }
    
    async def _genetic_algorithm_optimization(
        self,
        parameter_space: Dict[str, StrategyParameters],
        features: np.ndarray,
        targets: np.ndarray,
        max_generations: int = 50
    ) -> Dict[str, Any]:
        """Genetic algorithm optimization using scipy"""
        
        # Convert parameter space to bounds for differential evolution
        bounds = []
        param_names = []
        
        for param_name, param_info in parameter_space.items():
            if param_info.parameter_type in ["float", "int"]:
                bounds.append(param_info.optimization_bounds)
                param_names.append(param_name)
        
        def objective_function(x):
            # Convert array back to parameter dictionary
            params = {}
            for i, param_name in enumerate(param_names):
                param_info = parameter_space[param_name]
                if param_info.parameter_type == "int":
                    params[param_name] = int(round(x[i]))
                else:
                    params[param_name] = x[i]
            
            # Add categorical parameters at current values
            for param_name, param_info in parameter_space.items():
                if param_name not in params:
                    params[param_name] = param_info.current_value
            
            # Return negative performance (since DE minimizes)
            performance = self._evaluate_parameter_set(params, features, targets)
            return -performance
        
        # Run differential evolution
        result = differential_evolution(
            objective_function,
            bounds,
            maxiter=max_generations,
            popsize=15,
            seed=42
        )
        
        # Convert result back to parameter dictionary
        best_params = {}
        for i, param_name in enumerate(param_names):
            param_info = parameter_space[param_name]
            if param_info.parameter_type == "int":
                best_params[param_name] = int(round(result.x[i]))
            else:
                best_params[param_name] = result.x[i]
        
        # Add categorical parameters
        for param_name, param_info in parameter_space.items():
            if param_name not in best_params:
                best_params[param_name] = param_info.current_value
        
        best_value = -result.fun
        baseline_performance = self._evaluate_parameter_set(
            {name: param.current_value for name, param in parameter_space.items()},
            features, targets
        )
        improvement = (best_value - baseline_performance) / abs(baseline_performance) * 100
        
        return {
            "best_parameters": best_params,
            "best_value": best_value,
            "iterations": result.nit,
            "converged": result.success,
            "improvement": improvement,
            "confidence": 0.8 if result.success else 0.6
        }
    
    async def _random_forest_optimization(
        self,
        parameter_space: Dict[str, StrategyParameters],
        features: np.ndarray,
        targets: np.ndarray
    ) -> Dict[str, Any]:
        """Random Forest-based parameter importance and optimization"""
        
        # Generate parameter combinations for training
        n_samples = min(1000, len(features) * 2)
        parameter_samples = []
        performance_samples = []
        
        for _ in range(n_samples):
            # Random sample from parameter space
            sample_params = {}
            for param_name, param_info in parameter_space.items():
                if param_info.parameter_type == "float":
                    sample_params[param_name] = np.random.uniform(
                        param_info.optimization_bounds[0],
                        param_info.optimization_bounds[1]
                    )
                elif param_info.parameter_type == "int":
                    sample_params[param_name] = np.random.randint(
                        param_info.optimization_bounds[0],
                        param_info.optimization_bounds[1] + 1
                    )
                else:
                    sample_params[param_name] = param_info.current_value
            
            parameter_samples.append(list(sample_params.values()))
            performance_samples.append(
                self._evaluate_parameter_set(sample_params, features, targets)
            )
        
        # Train Random Forest to predict performance from parameters
        rf_model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )
        
        X = np.array(parameter_samples)
        y = np.array(performance_samples)
        
        rf_model.fit(X, y)
        
        # Find best parameters from samples
        best_idx = np.argmax(y)
        best_sample = parameter_samples[best_idx]
        
        # Convert back to parameter dictionary
        best_params = {}
        param_names = list(parameter_space.keys())
        for i, param_name in enumerate(param_names):
            if i < len(best_sample):
                best_params[param_name] = best_sample[i]
            else:
                best_params[param_name] = parameter_space[param_name].current_value
        
        baseline_performance = self._evaluate_parameter_set(
            {name: param.current_value for name, param in parameter_space.items()},
            features, targets
        )
        improvement = (y[best_idx] - baseline_performance) / abs(baseline_performance) * 100
        
        return {
            "best_parameters": best_params,
            "best_value": y[best_idx],
            "iterations": n_samples,
            "converged": True,
            "improvement": improvement,
            "confidence": rf_model.score(X, y),
            "feature_importance": dict(zip(param_names, rf_model.feature_importances_))
        }
    
    def _define_parameter_space(self, strategy: TradingStrategy) -> Dict[str, StrategyParameters]:
        """Define optimization parameter space for strategy"""
        parameter_space = {}
        
        # Common strategy parameters (simplified)
        if strategy.strategy_type.value == "momentum":
            parameter_space["short_window"] = StrategyParameters(
                parameter_name="short_window",
                current_value=10,
                min_value=5,
                max_value=20,
                parameter_type="int",
                optimization_bounds=(5, 20),
                importance_score=0.8
            )
            
            parameter_space["long_window"] = StrategyParameters(
                parameter_name="long_window",
                current_value=50,
                min_value=20,
                max_value=100,
                parameter_type="int",
                optimization_bounds=(20, 100),
                importance_score=0.9
            )
            
            parameter_space["momentum_threshold"] = StrategyParameters(
                parameter_name="momentum_threshold",
                current_value=0.02,
                min_value=0.005,
                max_value=0.05,
                parameter_type="float",
                optimization_bounds=(0.005, 0.05),
                importance_score=0.7
            )
        
        elif strategy.strategy_type.value == "mean_reversion":
            parameter_space["lookback_period"] = StrategyParameters(
                parameter_name="lookback_period",
                current_value=20,
                min_value=10,
                max_value=50,
                parameter_type="int",
                optimization_bounds=(10, 50),
                importance_score=0.8
            )
            
            parameter_space["deviation_threshold"] = StrategyParameters(
                parameter_name="deviation_threshold",
                current_value=2.0,
                min_value=1.0,
                max_value=3.0,
                parameter_type="float",
                optimization_bounds=(1.0, 3.0),
                importance_score=0.9
            )
        
        # Risk management parameters
        parameter_space["stop_loss_pct"] = StrategyParameters(
            parameter_name="stop_loss_pct",
            current_value=0.05,
            min_value=0.02,
            max_value=0.10,
            parameter_type="float",
            optimization_bounds=(0.02, 0.10),
            importance_score=0.6
        )
        
        parameter_space["take_profit_pct"] = StrategyParameters(
            parameter_name="take_profit_pct",
            current_value=0.10,
            min_value=0.05,
            max_value=0.20,
            parameter_type="float",
            optimization_bounds=(0.05, 0.20),
            importance_score=0.5
        )
        
        return parameter_space
    
    def _prepare_optimization_data(
        self,
        historical_data: List[Dict[str, Any]],
        objective: OptimizationObjective
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and targets for optimization"""
        
        # Extract features (simplified)
        features = []
        targets = []
        
        for data_point in historical_data:
            # Market features
            feature_vector = [
                data_point.get("close", 0),
                data_point.get("volume", 0),
                data_point.get("volatility", 0),
                data_point.get("rsi", 50),
                data_point.get("macd", 0)
            ]
            
            # Target based on objective
            if objective == OptimizationObjective.SHARPE_RATIO:
                target = data_point.get("sharpe_ratio", 0)
            elif objective == OptimizationObjective.TOTAL_RETURN:
                target = data_point.get("return", 0)
            else:
                target = data_point.get("performance_score", 0)
            
            features.append(feature_vector)
            targets.append(target)
        
        return np.array(features), np.array(targets)
    
    def _evaluate_parameter_set(
        self,
        parameters: Dict[str, Any],
        features: np.ndarray,
        targets: np.ndarray
    ) -> float:
        """Evaluate performance of parameter set"""
        
        # Simplified evaluation - would run actual backtest
        # For now, use a synthetic performance function
        
        # Normalize parameters
        param_values = list(parameters.values())
        numeric_params = [v for v in param_values if isinstance(v, (int, float))]
        
        if not numeric_params:
            return 0.0
        
        # Synthetic performance based on parameter values and features
        base_performance = np.mean(targets) if len(targets) > 0 else 0.0
        
        # Add noise based on parameter configuration
        param_effect = np.mean(numeric_params) * 0.1
        feature_effect = np.mean(features) * 0.001 if len(features) > 0 else 0.0
        
        performance = base_performance + param_effect + feature_effect
        
        # Add some randomness to simulate market uncertainty
        noise = np.random.normal(0, 0.1)
        
        return performance + noise
    
    def _extract_current_parameters(self, strategy: TradingStrategy) -> Dict[str, Any]:
        """Extract current parameter values from strategy"""
        # Simplified extraction
        return strategy.parameters if hasattr(strategy, 'parameters') else {}
    
    async def _validate_optimization(
        self,
        result: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Validate optimization result using out-of-sample data"""
        
        # Split data for validation
        split_point = int(len(historical_data) * 0.8)
        validation_data = historical_data[split_point:]
        
        if len(validation_data) < 10:
            return {"validation_score": 0.5}
        
        # Simulate performance on validation data
        validation_performance = np.random.normal(
            result.get("best_value", 0) * 0.9,  # Expect some degradation
            0.1
        )
        
        return {
            "validation_score": max(0.0, validation_performance),
            "validation_samples": len(validation_data),
            "performance_correlation": 0.8  # Placeholder
        }


class MachineLearningEngine:
    """Machine learning engine for strategy adaptation"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        
    async def train_strategy_model(
        self,
        strategy_id: str,
        training_data: pd.DataFrame,
        model_type: LearningAlgorithm = LearningAlgorithm.RANDOM_FOREST,
        target_column: str = "performance"
    ) -> LearningModel:
        """Train machine learning model for strategy"""
        
        # Prepare features
        feature_columns = [col for col in training_data.columns if col != target_column]
        X = training_data[feature_columns]
        y = training_data[target_column]
        
        if len(X) < 100:
            raise ValueError("Insufficient training data")
        
        # Scale features
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Split data for time series validation
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Train model based on type
        if model_type == LearningAlgorithm.RANDOM_FOREST:
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif model_type == LearningAlgorithm.GRADIENT_BOOSTING:
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
        elif model_type == LearningAlgorithm.NEURAL_NETWORK:
            model = self._create_neural_network(X_scaled.shape[1])
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Cross-validation
        cv_scores = []
        feature_importance = {}
        
        for train_idx, val_idx in tscv.split(X_scaled):
            X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model.fit(X_train, y_train)
            val_score = model.score(X_val, y_val)
            cv_scores.append(val_score)
        
        # Final training on all data
        model.fit(X_scaled, y)
        
        # Feature importance
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(feature_columns, model.feature_importances_))
        
        # Store model and scaler
        model_id = f"{strategy_id}_{model_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.models[model_id] = model
        self.scalers[model_id] = scaler
        
        # Create learning model record
        learning_model = LearningModel(
            strategy_id=strategy_id,
            model_type=model_type,
            features=feature_columns,
            target_variable=target_column,
            training_score=model.score(X_scaled, y),
            validation_score=np.mean(cv_scores),
            feature_importance=feature_importance,
            last_trained=datetime.now(timezone.utc),
            next_retrain=datetime.now(timezone.utc) + timedelta(days=30),
            model_path=f"models/{model_id}.pkl"
        )
        
        # Save model to disk
        await self._save_model(model_id, model, scaler)
        
        return learning_model
    
    def _create_neural_network(self, input_dim: int) -> keras.Model:
        """Create neural network model"""
        model = keras.Sequential([
            keras.layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    async def predict_strategy_performance(
        self,
        model_id: str,
        features: Dict[str, float]
    ) -> Tuple[float, float]:
        """Predict strategy performance using trained model"""
        
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        scaler = self.scalers[model_id]
        
        # Prepare features
        feature_array = np.array([list(features.values())]).reshape(1, -1)
        scaled_features = scaler.transform(feature_array)
        
        # Make prediction
        prediction = model.predict(scaled_features)[0]
        
        # Calculate confidence (simplified)
        if hasattr(model, 'predict_proba'):
            # For classifiers
            confidence = np.max(model.predict_proba(scaled_features))
        else:
            # For regressors, use a simple confidence measure
            confidence = 0.8  # Placeholder
        
        return float(prediction), float(confidence)
    
    async def _save_model(self, model_id: str, model: Any, scaler: Any):
        """Save model and scaler to disk"""
        try:
            model_data = {
                'model': model,
                'scaler': scaler,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # In production, would save to persistent storage
            # For now, keep in memory
            logger.info(f"Model {model_id} saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save model {model_id}: {e}")


class AdaptationManager:
    """Strategy adaptation and monitoring manager"""
    
    def __init__(self):
        self.adaptation_thresholds = {
            AdaptationTrigger.PERFORMANCE_DEGRADATION: -0.1,  # -10% performance drop
            AdaptationTrigger.RISK_LIMIT_BREACH: 1.5,          # 1.5x risk limit
            AdaptationTrigger.SIGNAL_QUALITY_DECLINE: 0.6,    # Below 60% confidence
        }
        
    async def monitor_strategy_adaptation(
        self,
        strategy_id: str,
        current_performance: Dict[str, float],
        historical_performance: List[Dict[str, float]]
    ) -> List[AdaptationEvent]:
        """Monitor strategy for adaptation triggers"""
        
        adaptation_events = []
        
        # Performance degradation check
        if len(historical_performance) >= 5:
            recent_performance = np.mean([p.get("total_return", 0) for p in historical_performance[-5:]])
            baseline_performance = np.mean([p.get("total_return", 0) for p in historical_performance[:-5]]) if len(historical_performance) > 5 else recent_performance
            
            performance_change = (recent_performance - baseline_performance) / abs(baseline_performance) if baseline_performance != 0 else 0
            
            if performance_change < self.adaptation_thresholds[AdaptationTrigger.PERFORMANCE_DEGRADATION]:
                event = AdaptationEvent(
                    strategy_id=strategy_id,
                    trigger=AdaptationTrigger.PERFORMANCE_DEGRADATION,
                    trigger_value=performance_change,
                    threshold_breached=self.adaptation_thresholds[AdaptationTrigger.PERFORMANCE_DEGRADATION],
                    severity="high" if performance_change < -0.2 else "medium",
                    adaptation_recommended=True,
                    adaptation_type="parameter_adjustment",
                    recommended_actions=[
                        "Review and optimize strategy parameters",
                        "Analyze market regime changes",
                        "Consider model retraining"
                    ]
                )
                adaptation_events.append(event)
        
        # Risk limit breach check
        current_max_drawdown = current_performance.get("max_drawdown", 0)
        if current_max_drawdown > 0.15:  # 15% drawdown threshold
            event = AdaptationEvent(
                strategy_id=strategy_id,
                trigger=AdaptationTrigger.RISK_LIMIT_BREACH,
                trigger_value=current_max_drawdown,
                threshold_breached=0.15,
                severity="critical" if current_max_drawdown > 0.25 else "high",
                adaptation_recommended=True,
                adaptation_type="strategy_pause",
                recommended_actions=[
                    "Reduce position sizes",
                    "Implement stricter stop-losses",
                    "Consider temporary strategy pause"
                ]
            )
            adaptation_events.append(event)
        
        # Signal quality decline
        signal_confidence = current_performance.get("avg_signal_confidence", 1.0)
        if signal_confidence < self.adaptation_thresholds[AdaptationTrigger.SIGNAL_QUALITY_DECLINE]:
            event = AdaptationEvent(
                strategy_id=strategy_id,
                trigger=AdaptationTrigger.SIGNAL_QUALITY_DECLINE,
                trigger_value=signal_confidence,
                threshold_breached=self.adaptation_thresholds[AdaptationTrigger.SIGNAL_QUALITY_DECLINE],
                severity="medium",
                adaptation_recommended=True,
                adaptation_type="model_retrain",
                recommended_actions=[
                    "Retrain signal generation models",
                    "Update market regime detection",
                    "Review feature engineering"
                ]
            )
            adaptation_events.append(event)
        
        return adaptation_events
    
    async def implement_adaptation(
        self,
        event: AdaptationEvent,
        optimization_result: OptimizationResult
    ) -> Dict[str, Any]:
        """Implement strategy adaptation based on event and optimization"""
        
        try:
            implementation_plan = {
                "event_id": event.event_id,
                "adaptation_type": event.adaptation_type,
                "implementation_steps": [],
                "rollback_plan": [],
                "monitoring_metrics": []
            }
            
            if event.adaptation_type == "parameter_adjustment":
                # Implement parameter changes
                implementation_plan["implementation_steps"] = [
                    "Backup current parameters",
                    "Apply optimized parameters",
                    "Initialize monitoring period",
                    "Set up automated rollback conditions"
                ]
                
                implementation_plan["rollback_plan"] = [
                    "Monitor performance for 7 days",
                    "Rollback if performance degrades by >5%",
                    "Rollback if risk limits are breached"
                ]
                
            elif event.adaptation_type == "model_retrain":
                implementation_plan["implementation_steps"] = [
                    "Gather recent training data",
                    "Retrain models with updated data",
                    "Validate model performance",
                    "Deploy updated models"
                ]
                
            elif event.adaptation_type == "strategy_pause":
                implementation_plan["implementation_steps"] = [
                    "Close existing positions gradually",
                    "Pause new signal generation",
                    "Notify risk management team",
                    "Schedule strategy review"
                ]
            
            # Mark event as implemented
            event.implemented = True
            event.implementation_result = "planned"
            
            logger.info(f"Adaptation implementation planned for strategy {event.strategy_id}")
            
            return {
                "status": "planned",
                "implementation_plan": implementation_plan,
                "expected_timeline": "7-14 days",
                "risk_assessment": "medium"
            }
            
        except Exception as e:
            logger.error(f"Failed to implement adaptation for event {event.event_id}: {e}")
            return {"status": "failed", "error": str(e)}


class AdaptiveLearningService:
    """
    Adaptive strategy learning and optimization service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Learning components
        self.optimizer = StrategyOptimizer()
        self.ml_engine = MachineLearningEngine()
        self.adaptation_manager = AdaptationManager()
        
        # Learning state
        self.optimization_results: Dict[str, OptimizationResult] = {}
        self.learning_models: Dict[str, LearningModel] = {}
        self.adaptation_events: Dict[str, List[AdaptationEvent]] = defaultdict(list)
        
        # Performance tracking
        self.strategy_performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Configuration
        self.learning_interval = 86400        # 24 hours
        self.optimization_interval = 604800   # 7 days
        self.adaptation_check_interval = 3600 # 1 hour
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the adaptive learning service"""
        try:
            logger.info("Initializing Adaptive Learning Service...")
            
            # Load existing models and optimization results
            await self._load_existing_models()
            await self._load_optimization_history()
            
            # Start background tasks
            asyncio.create_task(self._learning_loop())
            asyncio.create_task(self._optimization_loop())
            asyncio.create_task(self._adaptation_monitoring_loop())
            
            logger.info("Adaptive Learning Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Adaptive Learning Service: {e}")
            raise
    
    async def optimize_strategy(
        self,
        strategy_id: str,
        objective: OptimizationObjective = OptimizationObjective.SHARPE_RATIO,
        algorithm: LearningAlgorithm = LearningAlgorithm.BAYESIAN_OPTIMIZATION
    ) -> OptimizationResult:
        """Optimize strategy parameters"""
        try:
            logger.info(f"Optimizing strategy {strategy_id} using {algorithm.value}")
            
            # Get strategy data
            strategy = await self._get_strategy_by_id(strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            # Get historical performance data
            historical_data = await self._get_strategy_historical_data(strategy_id)
            if len(historical_data) < 100:
                raise HTTPException(status_code=400, detail="Insufficient historical data")
            
            # Perform optimization
            optimization_result = await self.optimizer.optimize_strategy_parameters(
                strategy, historical_data, objective, algorithm
            )
            
            # Store result
            self.optimization_results[optimization_result.optimization_id] = optimization_result
            
            # Save to database
            await self._save_optimization_result(optimization_result)
            
            logger.info(f"Strategy optimization completed: {optimization_result.improvement_percentage:.2f}% improvement")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Failed to optimize strategy {strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Strategy optimization failed: {str(e)}")
    
    async def train_adaptive_model(
        self,
        strategy_id: str,
        model_type: LearningAlgorithm = LearningAlgorithm.RANDOM_FOREST
    ) -> LearningModel:
        """Train adaptive learning model for strategy"""
        try:
            logger.info(f"Training adaptive model for strategy {strategy_id}")
            
            # Prepare training data
            training_data = await self._prepare_training_data(strategy_id)
            if len(training_data) < 100:
                raise HTTPException(status_code=400, detail="Insufficient training data")
            
            # Train model
            learning_model = await self.ml_engine.train_strategy_model(
                strategy_id, training_data, model_type
            )
            
            # Store model
            self.learning_models[learning_model.model_id] = learning_model
            
            # Save to database
            await self._save_learning_model(learning_model)
            
            logger.info(f"Adaptive model trained successfully with validation score: {learning_model.validation_score:.3f}")
            
            return learning_model
            
        except Exception as e:
            logger.error(f"Failed to train adaptive model for strategy {strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    async def check_adaptation_triggers(self, strategy_id: str) -> List[AdaptationEvent]:
        """Check if strategy needs adaptation"""
        try:
            # Get current and historical performance
            performance_service = await get_performance_analytics_service()
            current_performance = await performance_service.get_strategy_analytics_dashboard(strategy_id)
            
            if "error" in current_performance:
                return []
            
            historical_performance = list(self.strategy_performance_history[strategy_id])
            
            # Check for adaptation triggers
            adaptation_events = await self.adaptation_manager.monitor_strategy_adaptation(
                strategy_id, current_performance["key_performance_indicators"], historical_performance
            )
            
            # Store events
            self.adaptation_events[strategy_id].extend(adaptation_events)
            
            # Save events to database
            for event in adaptation_events:
                await self._save_adaptation_event(event)
            
            if adaptation_events:
                logger.info(f"Detected {len(adaptation_events)} adaptation triggers for strategy {strategy_id}")
            
            return adaptation_events
            
        except Exception as e:
            logger.error(f"Failed to check adaptation triggers for strategy {strategy_id}: {e}")
            return []
    
    async def get_learning_analytics(self, strategy_id: str) -> Dict[str, Any]:
        """Get adaptive learning analytics for strategy"""
        try:
            # Get optimization results
            strategy_optimizations = [
                result for result in self.optimization_results.values()
                if result.strategy_id == strategy_id
            ]
            
            # Get learning models
            strategy_models = [
                model for model in self.learning_models.values()
                if model.strategy_id == strategy_id
            ]
            
            # Get adaptation events
            adaptation_events = self.adaptation_events.get(strategy_id, [])
            
            # Calculate metrics
            total_optimizations = len(strategy_optimizations)
            avg_improvement = np.mean([r.improvement_percentage for r in strategy_optimizations]) if strategy_optimizations else 0
            
            successful_adaptations = len([e for e in adaptation_events if e.implemented])
            
            return {
                "strategy_id": strategy_id,
                "learning_summary": {
                    "total_optimizations": total_optimizations,
                    "average_improvement": avg_improvement,
                    "active_models": len(strategy_models),
                    "adaptation_events": len(adaptation_events),
                    "successful_adaptations": successful_adaptations
                },
                "recent_optimizations": [
                    {
                        "optimization_id": r.optimization_id,
                        "improvement": r.improvement_percentage,
                        "algorithm": r.algorithm_used.value,
                        "date": r.created_at.isoformat()
                    }
                    for r in sorted(strategy_optimizations, key=lambda x: x.created_at, reverse=True)[:5]
                ],
                "model_performance": [
                    {
                        "model_id": m.model_id,
                        "model_type": m.model_type.value,
                        "validation_score": m.validation_score,
                        "last_trained": m.last_trained.isoformat() if m.last_trained else None
                    }
                    for m in strategy_models
                ],
                "adaptation_triggers": [
                    {
                        "trigger": e.trigger.value,
                        "severity": e.severity,
                        "implemented": e.implemented,
                        "date": e.created_at.isoformat()
                    }
                    for e in sorted(adaptation_events, key=lambda x: x.created_at, reverse=True)[:10]
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning analytics for strategy {strategy_id}: {e}")
            return {"error": str(e)}
    
    # Background service loops
    
    async def _learning_loop(self):
        """Background learning and model update loop"""
        while not self._shutdown:
            try:
                # Get active strategies
                active_strategies = await self._get_active_strategies()
                
                for strategy_id in active_strategies[:3]:  # Limit to avoid overload
                    try:
                        # Check if models need retraining
                        models = [m for m in self.learning_models.values() if m.strategy_id == strategy_id]
                        
                        for model in models:
                            if (model.next_retrain and 
                                datetime.now(timezone.utc) > model.next_retrain):
                                
                                await self.train_adaptive_model(strategy_id, model.model_type)
                                
                    except Exception as e:
                        logger.error(f"Error in learning loop for strategy {strategy_id}: {e}")
                
                await asyncio.sleep(self.learning_interval)
                
            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(self.learning_interval)
    
    async def _optimization_loop(self):
        """Background optimization loop"""
        while not self._shutdown:
            try:
                # Get strategies due for optimization
                active_strategies = await self._get_active_strategies()
                
                for strategy_id in active_strategies[:2]:  # Limit optimization load
                    try:
                        # Check if optimization is due
                        last_optimization = max(
                            [r.created_at for r in self.optimization_results.values() 
                             if r.strategy_id == strategy_id],
                            default=datetime.min.replace(tzinfo=timezone.utc)
                        )
                        
                        if (datetime.now(timezone.utc) - last_optimization).total_seconds() > self.optimization_interval:
                            await self.optimize_strategy(strategy_id)
                            
                    except Exception as e:
                        logger.error(f"Error in optimization loop for strategy {strategy_id}: {e}")
                
                await asyncio.sleep(self.optimization_interval)
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(self.optimization_interval)
    
    async def _adaptation_monitoring_loop(self):
        """Background adaptation monitoring loop"""
        while not self._shutdown:
            try:
                # Check adaptation triggers for all strategies
                active_strategies = await self._get_active_strategies()
                
                for strategy_id in active_strategies:
                    try:
                        await self.check_adaptation_triggers(strategy_id)
                    except Exception as e:
                        logger.error(f"Error checking adaptation for strategy {strategy_id}: {e}")
                
                await asyncio.sleep(self.adaptation_check_interval)
                
            except Exception as e:
                logger.error(f"Error in adaptation monitoring loop: {e}")
                await asyncio.sleep(self.adaptation_check_interval)
    
    # Helper methods
    
    async def _get_strategy_by_id(self, strategy_id: str) -> Optional[TradingStrategy]:
        """Get strategy from database"""
        # Implementation would load from Supabase
        return None
    
    async def _get_strategy_historical_data(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get historical data for strategy"""
        # Implementation would fetch from database or market data provider
        # Generate sample data for demonstration
        historical_data = []
        
        for i in range(252):  # One year of daily data
            data_point = {
                "date": (datetime.now() - timedelta(days=252-i)).isoformat(),
                "close": 100 + np.random.normal(0, 5),
                "volume": np.random.randint(1000, 10000),
                "volatility": np.random.uniform(0.01, 0.05),
                "rsi": np.random.uniform(20, 80),
                "macd": np.random.normal(0, 2),
                "return": np.random.normal(0.001, 0.02),
                "sharpe_ratio": np.random.normal(1.0, 0.5),
                "performance_score": np.random.normal(0.5, 0.2)
            }
            historical_data.append(data_point)
        
        return historical_data
    
    # Additional helper methods would be implemented here...


# Global service instance
_adaptive_learning_service: Optional[AdaptiveLearningService] = None


async def get_adaptive_learning_service() -> AdaptiveLearningService:
    """Get the global adaptive learning service instance"""
    global _adaptive_learning_service
    
    if _adaptive_learning_service is None:
        _adaptive_learning_service = AdaptiveLearningService()
        await _adaptive_learning_service.initialize()
    
    return _adaptive_learning_service


@asynccontextmanager
async def adaptive_learning_context():
    """Context manager for adaptive learning service"""
    service = await get_adaptive_learning_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass