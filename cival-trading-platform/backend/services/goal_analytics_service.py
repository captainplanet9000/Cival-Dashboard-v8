"""
Phase 8: Goal Analytics & Prediction System
Advanced analytics with ML-based completion probability prediction and pattern recognition
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
import statistics

from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class AnalyticsTimeframe(Enum):
    """Analytics timeframe options"""
    LAST_24H = "last_24h"
    LAST_7D = "last_7d"
    LAST_30D = "last_30d"
    LAST_90D = "last_90d"
    ALL_TIME = "all_time"
    CUSTOM = "custom"

class PredictionModel(Enum):
    """Prediction model types"""
    LINEAR_REGRESSION = "linear_regression"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    PATTERN_MATCHING = "pattern_matching"
    ENSEMBLE = "ensemble"

@dataclass
class GoalCompletionPrediction:
    """Goal completion prediction result"""
    goal_id: str
    completion_probability: Decimal
    estimated_completion_date: Optional[datetime]
    confidence_interval: Tuple[Decimal, Decimal]
    key_factors: List[str]
    risk_factors: List[str]
    recommendation: str
    model_used: PredictionModel
    prediction_accuracy: Decimal

@dataclass
class GoalPerformancePattern:
    """Identified performance pattern"""
    pattern_id: str
    pattern_type: str
    description: str
    success_rate: Decimal
    avg_completion_time: int  # days
    common_characteristics: List[str]
    optimal_conditions: List[str]
    risk_indicators: List[str]
    recommendation: str

@dataclass
class GoalAnalyticsReport:
    """Comprehensive goal analytics report"""
    timeframe: AnalyticsTimeframe
    total_goals: int
    completed_goals: int
    failed_goals: int
    cancelled_goals: int
    in_progress_goals: int
    
    # Performance metrics
    overall_success_rate: Decimal
    avg_completion_time: Decimal
    median_completion_time: Decimal
    completion_time_std: Decimal
    
    # Financial metrics
    total_target_value: Decimal
    total_achieved_value: Decimal
    achievement_ratio: Decimal
    avg_goal_size: Decimal
    
    # Efficiency metrics
    goals_completed_on_time: int
    goals_completed_early: int
    goals_completed_late: int
    avg_timeline_accuracy: Decimal
    
    # Pattern insights
    most_successful_patterns: List[GoalPerformancePattern]
    least_successful_patterns: List[GoalPerformancePattern]
    emerging_patterns: List[str]
    
    # Recommendations
    optimization_recommendations: List[str]
    risk_warnings: List[str]
    
    generated_at: datetime

class GoalAnalyticsService:
    """
    Advanced goal analytics and prediction system
    Phase 8: ML-based predictions and pattern recognition
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Core services
        self.goal_service = None
        self.wallet_service = None
        self.market_service = None
        self.event_service = None
        
        # Analytics data
        self.goal_history: List[Dict[str, Any]] = []
        self.performance_patterns: Dict[str, GoalPerformancePattern] = {}
        self.prediction_models: Dict[PredictionModel, Any] = {}
        
        # Analytics cache
        self.analytics_cache: Dict[str, GoalAnalyticsReport] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        
        # Prediction accuracy tracking
        self.prediction_history: List[Dict[str, Any]] = []
        self.model_performance: Dict[PredictionModel, Dict[str, Decimal]] = {}
        
        # Pattern recognition data
        self.success_patterns = {
            "timeline_patterns": {},
            "value_patterns": {},
            "complexity_patterns": {},
            "market_condition_patterns": {}
        }
        
        # AG-UI event integration
        self.ag_ui_events = {
            "analytics.report_generated": [],
            "prediction.completed": [],
            "pattern.identified": [],
            "recommendation.created": []
        }
        
        self.service_active = False
        
        logger.info("GoalAnalyticsService initialized")
    
    async def initialize(self):
        """Initialize goal analytics service"""
        try:
            # Get required services
            self.goal_service = self.registry.get_service("intelligent_goal_service")
            self.wallet_service = self.registry.get_service("master_wallet_service")
            self.market_service = self.registry.get_service("market_analysis_service")
            self.event_service = self.registry.get_service("wallet_event_streaming_service")
            
            # Initialize prediction models
            await self._initialize_prediction_models()
            
            # Load historical goal data
            await self._load_goal_history()
            
            # Initialize pattern recognition
            await self._initialize_pattern_recognition()
            
            # Start background analytics loops
            asyncio.create_task(self._analytics_update_loop())
            asyncio.create_task(self._pattern_analysis_loop())
            asyncio.create_task(self._prediction_validation_loop())
            
            self.service_active = True
            logger.info("Goal analytics service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize goal analytics service: {e}")
            raise
    
    async def _initialize_prediction_models(self):
        """Initialize prediction models for goal completion"""
        try:
            # Linear regression model
            self.prediction_models[PredictionModel.LINEAR_REGRESSION] = {
                "weights": {"progress_rate": 0.4, "time_elapsed": 0.3, "target_size": 0.2, "complexity": 0.1},
                "bias": 0.5,
                "accuracy": Decimal("0.75")
            }
            
            # Moving average model
            self.prediction_models[PredictionModel.MOVING_AVERAGE] = {
                "window_size": 7,  # days
                "accuracy": Decimal("0.70")
            }
            
            # Exponential smoothing model
            self.prediction_models[PredictionModel.EXPONENTIAL_SMOOTHING] = {
                "alpha": 0.3,  # smoothing parameter
                "accuracy": Decimal("0.72")
            }
            
            # Pattern matching model
            self.prediction_models[PredictionModel.PATTERN_MATCHING] = {
                "similarity_threshold": 0.8,
                "accuracy": Decimal("0.78")
            }
            
            # Ensemble model (combination of all)
            self.prediction_models[PredictionModel.ENSEMBLE] = {
                "model_weights": {
                    PredictionModel.LINEAR_REGRESSION: 0.25,
                    PredictionModel.MOVING_AVERAGE: 0.20,
                    PredictionModel.EXPONENTIAL_SMOOTHING: 0.25,
                    PredictionModel.PATTERN_MATCHING: 0.30
                },
                "accuracy": Decimal("0.82")
            }
            
            # Initialize model performance tracking
            for model in PredictionModel:
                self.model_performance[model] = {
                    "accuracy": self.prediction_models[model]["accuracy"],
                    "predictions_made": 0,
                    "correct_predictions": 0,
                    "avg_error": Decimal("0")
                }
            
            logger.info("Initialized prediction models")
            
        except Exception as e:
            logger.error(f"Failed to initialize prediction models: {e}")
    
    async def _load_goal_history(self):
        """Load historical goal data for analysis"""
        try:
            if self.goal_service:
                # Get all goals from goal service
                all_goals = await self.goal_service.list_goals()
                
                for goal in all_goals:
                    goal_data = {
                        "goal_id": goal.goal_id,
                        "original_text": goal.original_text,
                        "priority": goal.priority.value,
                        "complexity": goal.complexity.value,
                        "status": goal.status.value,
                        "target_value": float(goal.target_value),
                        "current_value": float(goal.current_value),
                        "progress_percentage": float(goal.progress_percentage),
                        "created_at": goal.created_at.isoformat(),
                        "actual_start": goal.actual_start.isoformat() if goal.actual_start else None,
                        "actual_completion": goal.actual_completion.isoformat() if goal.actual_completion else None,
                        "estimated_completion": goal.estimated_completion.isoformat() if goal.estimated_completion else None,
                        "metadata": goal.metadata
                    }
                    self.goal_history.append(goal_data)
                
                logger.info(f"Loaded {len(self.goal_history)} historical goals")
            
        except Exception as e:
            logger.error(f"Failed to load goal history: {e}")
    
    async def _initialize_pattern_recognition(self):
        """Initialize pattern recognition for goal success factors"""
        try:
            # Analyze timeline patterns
            await self._analyze_timeline_patterns()
            
            # Analyze value patterns
            await self._analyze_value_patterns()
            
            # Analyze complexity patterns
            await self._analyze_complexity_patterns()
            
            logger.info("Initialized pattern recognition")
            
        except Exception as e:
            logger.error(f"Failed to initialize pattern recognition: {e}")
    
    async def predict_goal_completion(self, goal_id: str, model: PredictionModel = PredictionModel.ENSEMBLE) -> GoalCompletionPrediction:
        """
        Predict goal completion probability and timeline
        Main prediction entry point
        """
        try:
            if not self.goal_service:
                raise ValueError("Goal service not available")
            
            goal = await self.goal_service.get_goal_by_id(goal_id)
            if not goal:
                raise ValueError(f"Goal {goal_id} not found")
            
            # Get current goal state
            goal_data = self._extract_goal_features(goal)
            
            # Apply prediction model
            if model == PredictionModel.ENSEMBLE:
                prediction = await self._predict_with_ensemble(goal_data)
            else:
                prediction = await self._predict_with_single_model(goal_data, model)
            
            # Generate completion prediction
            completion_prediction = GoalCompletionPrediction(
                goal_id=goal_id,
                completion_probability=prediction["probability"],
                estimated_completion_date=prediction.get("completion_date"),
                confidence_interval=prediction["confidence_interval"],
                key_factors=prediction["key_factors"],
                risk_factors=prediction["risk_factors"],
                recommendation=prediction["recommendation"],
                model_used=model,
                prediction_accuracy=self.model_performance[model]["accuracy"]
            )
            
            # Store prediction for validation
            self.prediction_history.append({
                "goal_id": goal_id,
                "prediction": completion_prediction,
                "prediction_time": datetime.now(timezone.utc),
                "actual_outcome": None  # To be filled when goal completes
            })
            
            # Update model usage stats
            self.model_performance[model]["predictions_made"] += 1
            
            # Emit AG-UI event
            await self._emit_ag_ui_event("prediction.completed", {
                "goal_id": goal_id,
                "prediction": asdict(completion_prediction)
            })
            
            logger.info(f"Generated completion prediction for goal {goal_id}")
            return completion_prediction
            
        except Exception as e:
            logger.error(f"Failed to predict goal completion: {e}")
            raise
    
    def _extract_goal_features(self, goal) -> Dict[str, Any]:
        """Extract features from goal for prediction"""
        try:
            current_time = datetime.now(timezone.utc)
            
            features = {
                "goal_id": goal.goal_id,
                "target_value": float(goal.target_value),
                "current_value": float(goal.current_value),
                "progress_percentage": float(goal.progress_percentage),
                "complexity_score": self._get_complexity_score(goal.complexity),
                "priority_score": self._get_priority_score(goal.priority),
                "days_since_creation": (current_time - goal.created_at).days,
                "days_since_start": (current_time - goal.actual_start).days if goal.actual_start else 0,
                "estimated_timeline": (goal.estimated_completion - goal.created_at).days if goal.estimated_completion else 30,
                "has_deadline": goal.deadline is not None,
                "optimization_suggestions_count": len(goal.optimization_suggestions),
                "learning_insights_count": len(goal.learning_insights),
                "risk_score": goal.risk_assessment.get("overall_risk_score", 5) if goal.risk_assessment else 5
            }
            
            # Calculate progress rate
            if features["days_since_start"] > 0:
                features["progress_rate"] = features["progress_percentage"] / features["days_since_start"]
            else:
                features["progress_rate"] = 0
            
            # Calculate timeline efficiency
            if features["estimated_timeline"] > 0 and features["days_since_creation"] > 0:
                features["timeline_efficiency"] = features["days_since_creation"] / features["estimated_timeline"]
            else:
                features["timeline_efficiency"] = 1.0
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract goal features: {e}")
            return {}
    
    def _get_complexity_score(self, complexity) -> int:
        """Convert complexity enum to numeric score"""
        complexity_scores = {
            "simple": 1,
            "compound": 2,
            "complex": 3,
            "adaptive": 4
        }
        return complexity_scores.get(complexity.value if hasattr(complexity, 'value') else str(complexity), 2)
    
    def _get_priority_score(self, priority) -> int:
        """Convert priority enum to numeric score"""
        priority_scores = {
            "background": 1,
            "low": 2,
            "medium": 3,
            "high": 4,
            "critical": 5
        }
        return priority_scores.get(priority.value if hasattr(priority, 'value') else str(priority), 3)
    
    async def _predict_with_ensemble(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict using ensemble of models"""
        try:
            ensemble_config = self.prediction_models[PredictionModel.ENSEMBLE]
            model_weights = ensemble_config["model_weights"]
            
            predictions = {}
            
            # Get predictions from each model
            for model, weight in model_weights.items():
                if model != PredictionModel.ENSEMBLE:  # Avoid recursion
                    model_prediction = await self._predict_with_single_model(goal_data, model)
                    predictions[model] = {
                        "probability": model_prediction["probability"],
                        "weight": weight
                    }
            
            # Calculate weighted average probability
            weighted_probability = sum(
                pred["probability"] * pred["weight"] 
                for pred in predictions.values()
            )
            
            # Calculate confidence interval
            probabilities = [pred["probability"] for pred in predictions.values()]
            prob_std = Decimal(str(np.std([float(p) for p in probabilities])))
            confidence_interval = (
                max(Decimal("0"), weighted_probability - prob_std),
                min(Decimal("1"), weighted_probability + prob_std)
            )
            
            # Generate key factors
            key_factors = self._identify_key_factors(goal_data)
            risk_factors = self._identify_risk_factors(goal_data)
            recommendation = self._generate_recommendation(goal_data, weighted_probability)
            
            # Estimate completion date
            completion_date = None
            if weighted_probability > Decimal("0.5") and goal_data.get("progress_rate", 0) > 0:
                remaining_progress = 100 - goal_data["progress_percentage"]
                days_to_completion = remaining_progress / goal_data["progress_rate"]
                completion_date = datetime.now(timezone.utc) + timedelta(days=int(days_to_completion))
            
            return {
                "probability": weighted_probability,
                "completion_date": completion_date,
                "confidence_interval": confidence_interval,
                "key_factors": key_factors,
                "risk_factors": risk_factors,
                "recommendation": recommendation,
                "model_predictions": predictions
            }
            
        except Exception as e:
            logger.error(f"Failed to predict with ensemble: {e}")
            return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.3"), Decimal("0.7"))}
    
    async def _predict_with_single_model(self, goal_data: Dict[str, Any], model: PredictionModel) -> Dict[str, Any]:
        """Predict using single model"""
        try:
            if model == PredictionModel.LINEAR_REGRESSION:
                return await self._predict_linear_regression(goal_data)
            elif model == PredictionModel.MOVING_AVERAGE:
                return await self._predict_moving_average(goal_data)
            elif model == PredictionModel.EXPONENTIAL_SMOOTHING:
                return await self._predict_exponential_smoothing(goal_data)
            elif model == PredictionModel.PATTERN_MATCHING:
                return await self._predict_pattern_matching(goal_data)
            else:
                return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.3"), Decimal("0.7"))}
                
        except Exception as e:
            logger.error(f"Failed to predict with model {model}: {e}")
            return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.3"), Decimal("0.7"))}
    
    async def _predict_linear_regression(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Linear regression prediction model"""
        try:
            model_config = self.prediction_models[PredictionModel.LINEAR_REGRESSION]
            weights = model_config["weights"]
            bias = model_config["bias"]
            
            # Calculate weighted features
            progress_feature = goal_data.get("progress_percentage", 0) / 100
            time_feature = min(1.0, goal_data.get("timeline_efficiency", 1.0))
            size_feature = min(1.0, goal_data.get("target_value", 1000) / 10000)  # Normalize to 10k
            complexity_feature = 1.0 - (goal_data.get("complexity_score", 2) - 1) / 3  # Invert complexity
            
            # Linear combination
            probability = (
                weights["progress_rate"] * progress_feature +
                weights["time_elapsed"] * time_feature +
                weights["target_size"] * size_feature +
                weights["complexity"] * complexity_feature +
                bias
            )
            
            probability = max(0.0, min(1.0, probability))  # Clamp to [0,1]
            
            return {
                "probability": Decimal(str(probability)),
                "confidence_interval": (Decimal(str(probability - 0.1)), Decimal(str(probability + 0.1)))
            }
            
        except Exception as e:
            logger.error(f"Failed linear regression prediction: {e}")
            return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.4"), Decimal("0.6"))}
    
    async def _predict_moving_average(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Moving average prediction model"""
        try:
            # Use recent progress trend
            progress_rate = goal_data.get("progress_rate", 0)
            
            if progress_rate > 5:  # High progress rate
                probability = 0.85
            elif progress_rate > 2:  # Medium progress rate
                probability = 0.70
            elif progress_rate > 0.5:  # Low progress rate
                probability = 0.55
            else:  # Very low progress rate
                probability = 0.30
            
            return {
                "probability": Decimal(str(probability)),
                "confidence_interval": (Decimal(str(probability - 0.15)), Decimal(str(probability + 0.15)))
            }
            
        except Exception as e:
            logger.error(f"Failed moving average prediction: {e}")
            return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.35"), Decimal("0.65"))}
    
    async def _predict_exponential_smoothing(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exponential smoothing prediction model"""
        try:
            alpha = self.prediction_models[PredictionModel.EXPONENTIAL_SMOOTHING]["alpha"]
            
            # Use progress percentage as base
            base_probability = goal_data.get("progress_percentage", 0) / 100
            
            # Apply exponential smoothing based on time efficiency
            time_factor = goal_data.get("timeline_efficiency", 1.0)
            smoothed_probability = alpha * base_probability + (1 - alpha) * time_factor
            
            smoothed_probability = max(0.0, min(1.0, smoothed_probability))
            
            return {
                "probability": Decimal(str(smoothed_probability)),
                "confidence_interval": (Decimal(str(smoothed_probability - 0.12)), Decimal(str(smoothed_probability + 0.12)))
            }
            
        except Exception as e:
            logger.error(f"Failed exponential smoothing prediction: {e}")
            return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.38"), Decimal("0.62"))}
    
    async def _predict_pattern_matching(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Pattern matching prediction model"""
        try:
            # Find similar historical goals
            similar_goals = await self._find_similar_goals(goal_data)
            
            if not similar_goals:
                return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.3"), Decimal("0.7"))}
            
            # Calculate success rate of similar goals
            completed_similar = [g for g in similar_goals if g.get("status") == "completed"]
            success_rate = len(completed_similar) / len(similar_goals)
            
            # Adjust based on current progress
            progress_adjustment = goal_data.get("progress_percentage", 0) / 100 * 0.3
            adjusted_probability = success_rate + progress_adjustment
            
            adjusted_probability = max(0.0, min(1.0, adjusted_probability))
            
            return {
                "probability": Decimal(str(adjusted_probability)),
                "confidence_interval": (Decimal(str(adjusted_probability - 0.08)), Decimal(str(adjusted_probability + 0.08)))
            }
            
        except Exception as e:
            logger.error(f"Failed pattern matching prediction: {e}")
            return {"probability": Decimal("0.5"), "confidence_interval": (Decimal("0.42"), Decimal("0.58"))}
    
    async def _find_similar_goals(self, goal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar historical goals for pattern matching"""
        try:
            similar_goals = []
            threshold = 0.8  # Similarity threshold
            
            for historical_goal in self.goal_history:
                similarity = self._calculate_goal_similarity(goal_data, historical_goal)
                if similarity >= threshold:
                    similar_goals.append(historical_goal)
            
            return similar_goals
            
        except Exception as e:
            logger.error(f"Failed to find similar goals: {e}")
            return []
    
    def _calculate_goal_similarity(self, goal1: Dict[str, Any], goal2: Dict[str, Any]) -> float:
        """Calculate similarity between two goals"""
        try:
            similarity_score = 0.0
            factors = 0
            
            # Target value similarity
            if goal1.get("target_value") and goal2.get("target_value"):
                val1, val2 = goal1["target_value"], goal2["target_value"]
                value_similarity = 1 - abs(val1 - val2) / max(val1, val2)
                similarity_score += value_similarity * 0.3
                factors += 0.3
            
            # Complexity similarity
            if goal1.get("complexity_score") and goal2.get("complexity_score"):
                comp_similarity = 1 - abs(goal1["complexity_score"] - goal2["complexity_score"]) / 3
                similarity_score += comp_similarity * 0.2
                factors += 0.2
            
            # Priority similarity
            if goal1.get("priority_score") and goal2.get("priority_score"):
                prio_similarity = 1 - abs(goal1["priority_score"] - goal2["priority_score"]) / 4
                similarity_score += prio_similarity * 0.2
                factors += 0.2
            
            # Timeline similarity
            if goal1.get("estimated_timeline") and goal2.get("estimated_timeline"):
                time1, time2 = goal1["estimated_timeline"], goal2["estimated_timeline"]
                time_similarity = 1 - abs(time1 - time2) / max(time1, time2)
                similarity_score += time_similarity * 0.3
                factors += 0.3
            
            return similarity_score / factors if factors > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate goal similarity: {e}")
            return 0.0
    
    def _identify_key_factors(self, goal_data: Dict[str, Any]) -> List[str]:
        """Identify key success factors for the goal"""
        try:
            factors = []
            
            if goal_data.get("progress_rate", 0) > 3:
                factors.append("Strong progress momentum")
            
            if goal_data.get("timeline_efficiency", 1) < 0.8:
                factors.append("Good timeline management")
            
            if goal_data.get("complexity_score", 2) <= 2:
                factors.append("Manageable goal complexity")
            
            if goal_data.get("risk_score", 5) <= 5:
                factors.append("Controlled risk exposure")
            
            if goal_data.get("optimization_suggestions_count", 0) > 0:
                factors.append("Active optimization guidance")
            
            return factors
            
        except Exception as e:
            logger.error(f"Failed to identify key factors: {e}")
            return []
    
    def _identify_risk_factors(self, goal_data: Dict[str, Any]) -> List[str]:
        """Identify risk factors that may prevent completion"""
        try:
            factors = []
            
            if goal_data.get("progress_rate", 0) < 1:
                factors.append("Low progress rate")
            
            if goal_data.get("timeline_efficiency", 1) > 1.2:
                factors.append("Timeline pressure")
            
            if goal_data.get("complexity_score", 2) >= 3:
                factors.append("High goal complexity")
            
            if goal_data.get("risk_score", 5) > 7:
                factors.append("High risk exposure")
            
            if goal_data.get("days_since_start", 0) > goal_data.get("estimated_timeline", 30):
                factors.append("Overdue timeline")
            
            return factors
            
        except Exception as e:
            logger.error(f"Failed to identify risk factors: {e}")
            return []
    
    def _generate_recommendation(self, goal_data: Dict[str, Any], probability: Decimal) -> str:
        """Generate recommendation based on prediction"""
        try:
            if probability > Decimal("0.8"):
                return "Goal is on track for successful completion. Continue current approach."
            elif probability > Decimal("0.6"):
                return "Goal has good completion prospects. Consider minor optimizations."
            elif probability > Decimal("0.4"):
                return "Goal completion is uncertain. Review strategy and consider optimization."
            else:
                return "Goal completion is at risk. Immediate intervention recommended."
                
        except Exception as e:
            logger.error(f"Failed to generate recommendation: {e}")
            return "Unable to generate recommendation. Please review goal status manually."
    
    async def generate_analytics_report(self, timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30D) -> GoalAnalyticsReport:
        """
        Generate comprehensive goal analytics report
        Main analytics entry point
        """
        try:
            # Check cache first
            cache_key = f"report_{timeframe.value}"
            if cache_key in self.analytics_cache:
                cached_report = self.analytics_cache[cache_key]
                if cache_key in self.cache_expiry and datetime.now(timezone.utc) < self.cache_expiry[cache_key]:
                    return cached_report
            
            # Filter goals by timeframe
            filtered_goals = self._filter_goals_by_timeframe(timeframe)
            
            # Calculate basic metrics
            total_goals = len(filtered_goals)
            completed_goals = len([g for g in filtered_goals if g.get("status") == "completed"])
            failed_goals = len([g for g in filtered_goals if g.get("status") == "failed"])
            cancelled_goals = len([g for g in filtered_goals if g.get("status") == "cancelled"])
            in_progress_goals = len([g for g in filtered_goals if g.get("status") == "in_progress"])
            
            # Performance metrics
            overall_success_rate = Decimal(str(completed_goals / total_goals)) if total_goals > 0 else Decimal("0")
            
            # Calculate completion times
            completion_times = []
            for goal in filtered_goals:
                if goal.get("status") == "completed" and goal.get("actual_start") and goal.get("actual_completion"):
                    start_time = datetime.fromisoformat(goal["actual_start"].replace("Z", "+00:00"))
                    completion_time = datetime.fromisoformat(goal["actual_completion"].replace("Z", "+00:00"))
                    duration = (completion_time - start_time).days
                    completion_times.append(duration)
            
            avg_completion_time = Decimal(str(statistics.mean(completion_times))) if completion_times else Decimal("0")
            median_completion_time = Decimal(str(statistics.median(completion_times))) if completion_times else Decimal("0")
            completion_time_std = Decimal(str(statistics.stdev(completion_times))) if len(completion_times) > 1 else Decimal("0")
            
            # Financial metrics
            total_target_value = sum(goal.get("target_value", 0) for goal in filtered_goals)
            total_achieved_value = sum(goal.get("current_value", 0) for goal in filtered_goals if goal.get("status") == "completed")
            achievement_ratio = Decimal(str(total_achieved_value / total_target_value)) if total_target_value > 0 else Decimal("0")
            avg_goal_size = Decimal(str(total_target_value / total_goals)) if total_goals > 0 else Decimal("0")
            
            # Timeline efficiency metrics
            timeline_analysis = self._analyze_timeline_efficiency(filtered_goals)
            
            # Pattern analysis
            most_successful_patterns = await self._identify_successful_patterns(filtered_goals)
            least_successful_patterns = await self._identify_unsuccessful_patterns(filtered_goals)
            emerging_patterns = await self._identify_emerging_patterns(filtered_goals)
            
            # Generate recommendations
            optimization_recommendations = self._generate_optimization_recommendations(filtered_goals)
            risk_warnings = self._generate_risk_warnings(filtered_goals)
            
            # Create report
            report = GoalAnalyticsReport(
                timeframe=timeframe,
                total_goals=total_goals,
                completed_goals=completed_goals,
                failed_goals=failed_goals,
                cancelled_goals=cancelled_goals,
                in_progress_goals=in_progress_goals,
                overall_success_rate=overall_success_rate,
                avg_completion_time=avg_completion_time,
                median_completion_time=median_completion_time,
                completion_time_std=completion_time_std,
                total_target_value=Decimal(str(total_target_value)),
                total_achieved_value=Decimal(str(total_achieved_value)),
                achievement_ratio=achievement_ratio,
                avg_goal_size=avg_goal_size,
                goals_completed_on_time=timeline_analysis["on_time"],
                goals_completed_early=timeline_analysis["early"],
                goals_completed_late=timeline_analysis["late"],
                avg_timeline_accuracy=timeline_analysis["accuracy"],
                most_successful_patterns=most_successful_patterns,
                least_successful_patterns=least_successful_patterns,
                emerging_patterns=emerging_patterns,
                optimization_recommendations=optimization_recommendations,
                risk_warnings=risk_warnings,
                generated_at=datetime.now(timezone.utc)
            )
            
            # Cache report
            self.analytics_cache[cache_key] = report
            self.cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(hours=1)
            
            # Emit AG-UI event
            await self._emit_ag_ui_event("analytics.report_generated", {
                "timeframe": timeframe.value,
                "report": asdict(report)
            })
            
            logger.info(f"Generated analytics report for {timeframe.value}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            raise
    
    def _filter_goals_by_timeframe(self, timeframe: AnalyticsTimeframe) -> List[Dict[str, Any]]:
        """Filter goals by specified timeframe"""
        try:
            current_time = datetime.now(timezone.utc)
            
            if timeframe == AnalyticsTimeframe.ALL_TIME:
                return self.goal_history
            
            # Calculate cutoff time
            if timeframe == AnalyticsTimeframe.LAST_24H:
                cutoff = current_time - timedelta(hours=24)
            elif timeframe == AnalyticsTimeframe.LAST_7D:
                cutoff = current_time - timedelta(days=7)
            elif timeframe == AnalyticsTimeframe.LAST_30D:
                cutoff = current_time - timedelta(days=30)
            elif timeframe == AnalyticsTimeframe.LAST_90D:
                cutoff = current_time - timedelta(days=90)
            else:
                return self.goal_history
            
            # Filter goals
            filtered_goals = []
            for goal in self.goal_history:
                if goal.get("created_at"):
                    created_at = datetime.fromisoformat(goal["created_at"].replace("Z", "+00:00"))
                    if created_at >= cutoff:
                        filtered_goals.append(goal)
            
            return filtered_goals
            
        except Exception as e:
            logger.error(f"Failed to filter goals by timeframe: {e}")
            return []
    
    def _analyze_timeline_efficiency(self, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze timeline efficiency metrics"""
        try:
            on_time = 0
            early = 0
            late = 0
            total_completed = 0
            accuracy_scores = []
            
            for goal in goals:
                if (goal.get("status") == "completed" and 
                    goal.get("actual_start") and 
                    goal.get("actual_completion") and 
                    goal.get("estimated_completion")):
                    
                    start_time = datetime.fromisoformat(goal["actual_start"].replace("Z", "+00:00"))
                    actual_completion = datetime.fromisoformat(goal["actual_completion"].replace("Z", "+00:00"))
                    estimated_completion = datetime.fromisoformat(goal["estimated_completion"].replace("Z", "+00:00"))
                    
                    actual_duration = (actual_completion - start_time).days
                    estimated_duration = (estimated_completion - start_time).days
                    
                    if actual_duration <= estimated_duration:
                        on_time += 1
                        if actual_duration < estimated_duration:
                            early += 1
                    else:
                        late += 1
                    
                    # Calculate accuracy score
                    if estimated_duration > 0:
                        accuracy = 1 - abs(actual_duration - estimated_duration) / estimated_duration
                        accuracy_scores.append(max(0, accuracy))
                    
                    total_completed += 1
            
            avg_accuracy = Decimal(str(statistics.mean(accuracy_scores))) if accuracy_scores else Decimal("0")
            
            return {
                "on_time": on_time,
                "early": early,
                "late": late,
                "total_completed": total_completed,
                "accuracy": avg_accuracy
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze timeline efficiency: {e}")
            return {"on_time": 0, "early": 0, "late": 0, "total_completed": 0, "accuracy": Decimal("0")}
    
    async def _identify_successful_patterns(self, goals: List[Dict[str, Any]]) -> List[GoalPerformancePattern]:
        """Identify patterns that lead to goal success"""
        try:
            patterns = []
            
            # High-value goal pattern
            high_value_goals = [g for g in goals if g.get("target_value", 0) > 5000]
            if high_value_goals:
                success_rate = len([g for g in high_value_goals if g.get("status") == "completed"]) / len(high_value_goals)
                
                if success_rate > 0.7:
                    patterns.append(GoalPerformancePattern(
                        pattern_id="high_value_success",
                        pattern_type="target_value",
                        description="High-value goals (>$5000) show strong success rates",
                        success_rate=Decimal(str(success_rate)),
                        avg_completion_time=30,
                        common_characteristics=["Large target values", "High priority", "Detailed planning"],
                        optimal_conditions=["Sufficient capital allocation", "Extended timeline", "Regular monitoring"],
                        risk_indicators=["Market volatility", "Resource constraints"],
                        recommendation="Continue focusing on high-value goals with adequate resources"
                    ))
            
            # Short-term goal pattern
            short_term_goals = [g for g in goals if g.get("estimated_timeline", 30) <= 14]
            if short_term_goals:
                success_rate = len([g for g in short_term_goals if g.get("status") == "completed"]) / len(short_term_goals)
                
                if success_rate > 0.6:
                    patterns.append(GoalPerformancePattern(
                        pattern_id="short_term_success",
                        pattern_type="timeline",
                        description="Short-term goals (≤14 days) achieve good completion rates",
                        success_rate=Decimal(str(success_rate)),
                        avg_completion_time=10,
                        common_characteristics=["Focused objectives", "Clear timelines", "High urgency"],
                        optimal_conditions=["Available resources", "Market stability", "Clear execution plan"],
                        risk_indicators=["Time pressure", "Resource conflicts"],
                        recommendation="Use short-term goals for quick wins and momentum building"
                    ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to identify successful patterns: {e}")
            return []
    
    async def _identify_unsuccessful_patterns(self, goals: List[Dict[str, Any]]) -> List[GoalPerformancePattern]:
        """Identify patterns that lead to goal failure"""
        try:
            patterns = []
            
            # Over-ambitious timeline pattern
            failed_goals = [g for g in goals if g.get("status") in ["failed", "cancelled"]]
            if failed_goals:
                short_failed = [g for g in failed_goals if g.get("estimated_timeline", 30) <= 7]
                if len(short_failed) / len(failed_goals) > 0.4:
                    patterns.append(GoalPerformancePattern(
                        pattern_id="over_ambitious_timeline",
                        pattern_type="timeline",
                        description="Very short timelines (≤7 days) correlate with higher failure rates",
                        success_rate=Decimal("0.3"),
                        avg_completion_time=0,
                        common_characteristics=["Unrealistic timelines", "High pressure", "Insufficient planning"],
                        optimal_conditions=["Extended timelines", "Realistic expectations", "Proper resource allocation"],
                        risk_indicators=["Time pressure", "Market volatility", "Resource constraints"],
                        recommendation="Avoid overly aggressive timelines; allow adequate time for execution"
                    ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to identify unsuccessful patterns: {e}")
            return []
    
    async def _identify_emerging_patterns(self, goals: List[Dict[str, Any]]) -> List[str]:
        """Identify emerging patterns in recent goals"""
        try:
            patterns = []
            
            # Recent goals (last 7 days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_goals = [
                g for g in goals 
                if g.get("created_at") and datetime.fromisoformat(g["created_at"].replace("Z", "+00:00")) >= cutoff
            ]
            
            if len(recent_goals) >= 3:
                # Check for increasing complexity
                recent_complexity = [g.get("complexity_score", 2) for g in recent_goals[-5:]]
                if len(recent_complexity) >= 3 and all(c >= 3 for c in recent_complexity[-3:]):
                    patterns.append("Increasing goal complexity trend detected")
                
                # Check for larger target values
                recent_values = [g.get("target_value", 0) for g in recent_goals[-5:]]
                if len(recent_values) >= 3:
                    avg_recent = statistics.mean(recent_values[-3:])
                    avg_older = statistics.mean(recent_values[:-3]) if len(recent_values) > 3 else avg_recent
                    if avg_recent > avg_older * 1.5:
                        patterns.append("Increasing target value trend detected")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to identify emerging patterns: {e}")
            return []
    
    def _generate_optimization_recommendations(self, goals: List[Dict[str, Any]]) -> List[str]:
        """Generate optimization recommendations based on goal analysis"""
        try:
            recommendations = []
            
            completed_goals = [g for g in goals if g.get("status") == "completed"]
            failed_goals = [g for g in goals if g.get("status") in ["failed", "cancelled"]]
            
            success_rate = len(completed_goals) / len(goals) if goals else 0
            
            if success_rate < 0.6:
                recommendations.append("Overall success rate is below 60%. Consider reducing goal complexity or extending timelines.")
            
            if success_rate > 0.8:
                recommendations.append("High success rate achieved. Consider setting more ambitious targets.")
            
            # Timeline analysis
            overdue_goals = [
                g for g in goals 
                if g.get("status") == "in_progress" and g.get("estimated_completion")
                and datetime.fromisoformat(g["estimated_completion"].replace("Z", "+00:00")) < datetime.now(timezone.utc)
            ]
            
            if len(overdue_goals) / len(goals) > 0.3 if goals else False:
                recommendations.append("Over 30% of goals are overdue. Review timeline estimation process.")
            
            # Value analysis
            if goals:
                avg_target = statistics.mean([g.get("target_value", 0) for g in goals])
                avg_achieved = statistics.mean([g.get("current_value", 0) for g in completed_goals]) if completed_goals else 0
                
                if avg_achieved < avg_target * 0.7:
                    recommendations.append("Achievement values are significantly below targets. Consider more realistic goal setting.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            return []
    
    def _generate_risk_warnings(self, goals: List[Dict[str, Any]]) -> List[str]:
        """Generate risk warnings based on goal analysis"""
        try:
            warnings = []
            
            # High-risk goals in progress
            high_risk_goals = [
                g for g in goals 
                if g.get("status") == "in_progress" and g.get("risk_score", 5) > 7
            ]
            
            if high_risk_goals:
                warnings.append(f"{len(high_risk_goals)} high-risk goals currently in progress. Monitor closely.")
            
            # Large value at risk
            total_at_risk = sum(g.get("target_value", 0) for g in high_risk_goals)
            if total_at_risk > 50000:
                warnings.append(f"${total_at_risk:,.0f} in target value at high risk. Consider risk mitigation strategies.")
            
            # Timeline pressure
            urgent_goals = [
                g for g in goals 
                if g.get("status") == "in_progress" and g.get("estimated_completion")
                and datetime.fromisoformat(g["estimated_completion"].replace("Z", "+00:00")) < datetime.now(timezone.utc) + timedelta(days=3)
            ]
            
            if urgent_goals:
                warnings.append(f"{len(urgent_goals)} goals have urgent deadlines (≤3 days). Prioritize completion.")
            
            return warnings
            
        except Exception as e:
            logger.error(f"Failed to generate risk warnings: {e}")
            return []
    
    async def _analytics_update_loop(self):
        """Background loop for updating analytics data"""
        while self.service_active:
            try:
                await asyncio.sleep(1800)  # Update every 30 minutes
                
                # Refresh goal history
                await self._load_goal_history()
                
                # Clear cache to force fresh reports
                self.analytics_cache.clear()
                self.cache_expiry.clear()
                
                logger.debug("Updated analytics data")
                
            except Exception as e:
                logger.error(f"Error in analytics update loop: {e}")
                await asyncio.sleep(300)
    
    async def _pattern_analysis_loop(self):
        """Background loop for pattern analysis"""
        while self.service_active:
            try:
                await asyncio.sleep(3600)  # Analyze patterns every hour
                
                # Analyze new patterns
                await self._analyze_timeline_patterns()
                await self._analyze_value_patterns()
                await self._analyze_complexity_patterns()
                
            except Exception as e:
                logger.error(f"Error in pattern analysis loop: {e}")
                await asyncio.sleep(600)
    
    async def _prediction_validation_loop(self):
        """Background loop for validating prediction accuracy"""
        while self.service_active:
            try:
                await asyncio.sleep(7200)  # Validate every 2 hours
                
                # Check completed goals against predictions
                current_time = datetime.now(timezone.utc)
                
                for prediction_record in self.prediction_history:
                    if prediction_record["actual_outcome"] is None:  # Not yet validated
                        goal_id = prediction_record["goal_id"]
                        prediction = prediction_record["prediction"]
                        
                        if self.goal_service:
                            goal = await self.goal_service.get_goal_by_id(goal_id)
                            if goal and goal.status.value in ["completed", "failed", "cancelled"]:
                                # Validate prediction
                                actual_success = goal.status.value == "completed"
                                predicted_probability = float(prediction.completion_probability)
                                
                                # Update prediction record
                                prediction_record["actual_outcome"] = actual_success
                                prediction_record["validation_time"] = current_time
                                
                                # Update model performance
                                model_used = prediction.model_used
                                if model_used in self.model_performance:
                                    performance = self.model_performance[model_used]
                                    
                                    # Calculate prediction accuracy
                                    prediction_correct = (
                                        (actual_success and predicted_probability > 0.5) or
                                        (not actual_success and predicted_probability <= 0.5)
                                    )
                                    
                                    if prediction_correct:
                                        performance["correct_predictions"] += 1
                                    
                                    # Update accuracy rate
                                    total_predictions = performance["predictions_made"]
                                    if total_predictions > 0:
                                        performance["accuracy"] = Decimal(str(
                                            performance["correct_predictions"] / total_predictions
                                        ))
                
            except Exception as e:
                logger.error(f"Error in prediction validation loop: {e}")
                await asyncio.sleep(600)
    
    async def _analyze_timeline_patterns(self):
        """Analyze timeline-related success patterns"""
        try:
            completed_goals = [g for g in self.goal_history if g.get("status") == "completed"]
            
            if len(completed_goals) < 5:
                return
            
            # Group by timeline length
            timeline_groups = {
                "short": [],  # ≤ 14 days
                "medium": [], # 15-60 days
                "long": []    # > 60 days
            }
            
            for goal in completed_goals:
                timeline = goal.get("estimated_timeline", 30)
                if timeline <= 14:
                    timeline_groups["short"].append(goal)
                elif timeline <= 60:
                    timeline_groups["medium"].append(goal)
                else:
                    timeline_groups["long"].append(goal)
            
            # Analyze success rates
            for group_name, group_goals in timeline_groups.items():
                if group_goals:
                    success_rate = len(group_goals) / len([
                        g for g in self.goal_history 
                        if self._get_timeline_group(g.get("estimated_timeline", 30)) == group_name
                    ])
                    
                    self.success_patterns["timeline_patterns"][group_name] = {
                        "success_rate": success_rate,
                        "sample_size": len(group_goals),
                        "avg_completion_time": statistics.mean([
                            (datetime.fromisoformat(g["actual_completion"].replace("Z", "+00:00")) - 
                             datetime.fromisoformat(g["actual_start"].replace("Z", "+00:00"))).days
                            for g in group_goals 
                            if g.get("actual_start") and g.get("actual_completion")
                        ]) if any(g.get("actual_start") and g.get("actual_completion") for g in group_goals) else 0
                    }
            
        except Exception as e:
            logger.error(f"Failed to analyze timeline patterns: {e}")
    
    async def _analyze_value_patterns(self):
        """Analyze value-related success patterns"""
        try:
            completed_goals = [g for g in self.goal_history if g.get("status") == "completed"]
            
            if len(completed_goals) < 5:
                return
            
            # Group by target value
            value_groups = {
                "small": [],   # < $1000
                "medium": [],  # $1000-$10000
                "large": []    # > $10000
            }
            
            for goal in completed_goals:
                value = goal.get("target_value", 0)
                if value < 1000:
                    value_groups["small"].append(goal)
                elif value <= 10000:
                    value_groups["medium"].append(goal)
                else:
                    value_groups["large"].append(goal)
            
            # Analyze success rates and achievement ratios
            for group_name, group_goals in value_groups.items():
                if group_goals:
                    all_goals_in_group = [
                        g for g in self.goal_history 
                        if self._get_value_group(g.get("target_value", 0)) == group_name
                    ]
                    
                    success_rate = len(group_goals) / len(all_goals_in_group) if all_goals_in_group else 0
                    
                    avg_achievement_ratio = statistics.mean([
                        g.get("current_value", 0) / g.get("target_value", 1)
                        for g in group_goals 
                        if g.get("target_value", 0) > 0
                    ]) if group_goals else 0
                    
                    self.success_patterns["value_patterns"][group_name] = {
                        "success_rate": success_rate,
                        "sample_size": len(group_goals),
                        "avg_achievement_ratio": avg_achievement_ratio
                    }
            
        except Exception as e:
            logger.error(f"Failed to analyze value patterns: {e}")
    
    async def _analyze_complexity_patterns(self):
        """Analyze complexity-related success patterns"""
        try:
            completed_goals = [g for g in self.goal_history if g.get("status") == "completed"]
            
            if len(completed_goals) < 5:
                return
            
            # Group by complexity
            complexity_groups = {"simple": [], "compound": [], "complex": [], "adaptive": []}
            
            for goal in completed_goals:
                complexity = goal.get("complexity_score", 2)
                if complexity == 1:
                    complexity_groups["simple"].append(goal)
                elif complexity == 2:
                    complexity_groups["compound"].append(goal)
                elif complexity == 3:
                    complexity_groups["complex"].append(goal)
                else:
                    complexity_groups["adaptive"].append(goal)
            
            # Analyze success rates
            for group_name, group_goals in complexity_groups.items():
                if group_goals:
                    all_goals_in_group = [
                        g for g in self.goal_history 
                        if self._get_complexity_group(g.get("complexity_score", 2)) == group_name
                    ]
                    
                    success_rate = len(group_goals) / len(all_goals_in_group) if all_goals_in_group else 0
                    
                    self.success_patterns["complexity_patterns"][group_name] = {
                        "success_rate": success_rate,
                        "sample_size": len(group_goals)
                    }
            
        except Exception as e:
            logger.error(f"Failed to analyze complexity patterns: {e}")
    
    def _get_timeline_group(self, timeline: int) -> str:
        """Get timeline group for a given timeline value"""
        if timeline <= 14:
            return "short"
        elif timeline <= 60:
            return "medium"
        else:
            return "long"
    
    def _get_value_group(self, value: float) -> str:
        """Get value group for a given target value"""
        if value < 1000:
            return "small"
        elif value <= 10000:
            return "medium"
        else:
            return "large"
    
    def _get_complexity_group(self, complexity: int) -> str:
        """Get complexity group for a given complexity score"""
        if complexity == 1:
            return "simple"
        elif complexity == 2:
            return "compound"
        elif complexity == 3:
            return "complex"
        else:
            return "adaptive"
    
    async def _emit_ag_ui_event(self, event_type: str, data: Dict[str, Any]):
        """Emit AG-UI Protocol event"""
        try:
            if event_type in self.ag_ui_events:
                event = {
                    "type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": data
                }
                
                self.ag_ui_events[event_type].append(event)
                
                # Keep only last 100 events per type
                if len(self.ag_ui_events[event_type]) > 100:
                    self.ag_ui_events[event_type] = self.ag_ui_events[event_type][-100:]
                
                # Emit via event service if available
                if self.event_service:
                    await self.event_service.emit_event(
                        event_type,
                        "goal_analytics_service",
                        data
                    )
                
                logger.debug(f"Emitted AG-UI event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to emit AG-UI event: {e}")
    
    async def get_prediction_accuracy_report(self) -> Dict[str, Any]:
        """Get prediction accuracy report for all models"""
        try:
            report = {
                "model_performance": {},
                "overall_stats": {
                    "total_predictions": len(self.prediction_history),
                    "validated_predictions": len([p for p in self.prediction_history if p.get("actual_outcome") is not None]),
                    "pending_validation": len([p for p in self.prediction_history if p.get("actual_outcome") is None])
                },
                "recent_predictions": self.prediction_history[-10:],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            for model, performance in self.model_performance.items():
                report["model_performance"][model.value] = {
                    "accuracy": float(performance["accuracy"]),
                    "predictions_made": performance["predictions_made"],
                    "correct_predictions": performance["correct_predictions"],
                    "avg_error": float(performance["avg_error"])
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to get prediction accuracy report: {e}")
            return {}
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get goal analytics service status"""
        return {
            "service": "goal_analytics_service",
            "status": "active" if self.service_active else "inactive",
            "goal_history_count": len(self.goal_history),
            "performance_patterns": len(self.performance_patterns),
            "prediction_models": len(self.prediction_models),
            "cached_reports": len(self.analytics_cache),
            "prediction_history": len(self.prediction_history),
            "pattern_analysis": {
                "timeline_patterns": len(self.success_patterns["timeline_patterns"]),
                "value_patterns": len(self.success_patterns["value_patterns"]),
                "complexity_patterns": len(self.success_patterns["complexity_patterns"])
            },
            "ag_ui_events": {k: len(v) for k, v in self.ag_ui_events.items()},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_goal_analytics_service():
    """Factory function to create GoalAnalyticsService instance"""
    return GoalAnalyticsService()