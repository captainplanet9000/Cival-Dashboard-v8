/**
 * AG-UI Protocol Configuration for Trading Platform
 * Phase 8: Foundation setup for real-time agent communication
 */

import { TransportConfig } from './ag-ui-protocol-v2';

interface ConnectionConfig {
  websocket: {
    url: string;
    reconnect: boolean;
    maxReconnectAttempts: number;
    reconnectInterval: number;
    heartbeat: {
      enabled: boolean;
      interval: number;
      timeout: number;
    };
  };
  http: {
    baseUrl: string;
    timeout: number;
    retries: number;
  };
  auth: {
    type: string;
    tokenKey: string;
    refreshTokenKey: string;
    autoRefresh: boolean;
  };
}

interface EventTransport {
  primary: {
    type: string;
    config: any;
  };
  fallback: {
    type: string;
    config: any;
  };
  buffer: {
    enabled: boolean;
    maxSize: number;
    persistToDisk: boolean;
    flushOnReconnect: boolean;
  };
}

// Trading Platform Event Types for AG-UI Protocol
export interface TradingEvents {
  // Goal Management Events (Phase 8)
  'goal.created': GoalCreatedEvent;
  'goal.analyzed': GoalAnalyzedEvent;
  'goal.progress_updated': GoalProgressUpdatedEvent;
  'goal.completed': GoalCompletedEvent;
  'goal.optimization_suggested': GoalOptimizationEvent;
  'goal.decomposed': GoalDecomposedEvent;
  'goal.cancelled': GoalCancelledEvent;
  
  // Analytics Events (Phase 8)
  'analytics.report_generated': AnalyticsReportEvent;
  'prediction.completed': PredictionCompletedEvent;
  'pattern.identified': PatternIdentifiedEvent;
  'recommendation.created': RecommendationEvent;
  
  // Wallet Events (Future phases)
  'wallet.created': WalletCreatedEvent;
  'wallet.updated': WalletUpdatedEvent;
  'wallet.balance_changed': WalletBalanceEvent;
  'wallet.transaction': WalletTransactionEvent;
  
  // Agent Events (Future phases)
  'agent.decision': AgentDecisionEvent;
  'agent.communication': AgentCommunicationEvent;
  'agent.performance_update': AgentPerformanceEvent;
  'agent.strategy_change': AgentStrategyEvent;
  
  // Trading Events (Future phases)
  'trade.executed': TradeExecutedEvent;
  'trade.signal_generated': TradeSignalEvent;
  'trade.risk_alert': RiskAlertEvent;
  'trade.position_update': PositionUpdateEvent;
  
  // System Events
  'system.health_check': SystemHealthEvent;
  'system.error': SystemErrorEvent;
  'system.notification': SystemNotificationEvent;
}

// Goal Management Event Interfaces
export interface GoalCreatedEvent {
  goal: GoalData;
  parsing_confidence: number;
  timestamp: string;
}

export interface GoalAnalyzedEvent {
  goal: GoalData;
  risk_assessment: RiskAssessment;
  optimization_suggestions: string[];
  timestamp: string;
}

export interface GoalProgressUpdatedEvent {
  goal: GoalData;
  previous_value: number;
  new_value: number;
  progress_insights: string[];
  timestamp: string;
}

export interface GoalCompletedEvent {
  goal: GoalData;
  completion_insights: string[];
  completion_efficiency: number;
  timestamp: string;
}

export interface GoalOptimizationEvent {
  goal: GoalData;
  optimization_result: OptimizationResult;
  timestamp: string;
}

export interface GoalDecomposedEvent {
  goal: GoalData;
  decomposition: GoalDecomposition;
  timestamp: string;
}

export interface GoalCancelledEvent {
  goal: GoalData;
  reason: string;
  timestamp: string;
}

// Analytics Event Interfaces
export interface AnalyticsReportEvent {
  timeframe: string;
  report: AnalyticsReport;
  timestamp: string;
}

export interface PredictionCompletedEvent {
  goal_id: string;
  prediction: CompletionPrediction;
  timestamp: string;
}

export interface PatternIdentifiedEvent {
  pattern: PerformancePattern;
  confidence: number;
  timestamp: string;
}

export interface RecommendationEvent {
  type: 'optimization' | 'risk_warning' | 'strategy';
  recommendation: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
}

// Future Event Interfaces (Placeholder for upcoming phases)
export interface WalletCreatedEvent {
  wallet_id: string;
  config: any;
  timestamp: string;
}

export interface WalletUpdatedEvent {
  wallet_id: string;
  changes: any;
  timestamp: string;
}

export interface WalletBalanceEvent {
  wallet_id: string;
  old_balance: number;
  new_balance: number;
  timestamp: string;
}

export interface WalletTransactionEvent {
  wallet_id: string;
  transaction: any;
  timestamp: string;
}

export interface AgentDecisionEvent {
  agent_id: string;
  decision: any;
  reasoning: string;
  timestamp: string;
}

export interface AgentCommunicationEvent {
  from_agent: string;
  to_agent: string;
  message: string;
  timestamp: string;
}

export interface AgentPerformanceEvent {
  agent_id: string;
  performance_metrics: any;
  timestamp: string;
}

export interface AgentStrategyEvent {
  agent_id: string;
  old_strategy: string;
  new_strategy: string;
  timestamp: string;
}

export interface TradeExecutedEvent {
  trade_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  timestamp: string;
}

export interface TradeSignalEvent {
  signal_id: string;
  symbol: string;
  signal_type: string;
  strength: number;
  timestamp: string;
}

export interface RiskAlertEvent {
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
}

export interface PositionUpdateEvent {
  position_id: string;
  symbol: string;
  size: number;
  pnl: number;
  timestamp: string;
}

export interface SystemHealthEvent {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  metrics: any;
  timestamp: string;
}

export interface SystemErrorEvent {
  service: string;
  error_type: string;
  message: string;
  timestamp: string;
}

export interface SystemNotificationEvent {
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
}

// Data Interfaces
export interface GoalData {
  goal_id: string;
  original_text: string;
  parsed_objective: string;
  priority: string;
  complexity: string;
  status: string;
  target_value: number;
  current_value: number;
  progress_percentage: number;
  optimization_suggestions: string[];
  risk_assessment: RiskAssessment;
  learning_insights: string[];
  estimated_completion?: string;
  actual_start?: string;
  actual_completion?: string;
  deadline?: string;
  created_at: string;
  updated_at: string;
  wallet_id?: string;
  allocation_id?: string;
  metadata: any;
}

export interface RiskAssessment {
  overall_risk_score: number;
  risk_factors: string[];
  mitigation_strategies: string[];
  probability_of_loss: number;
  maximum_potential_loss: number;
  risk_category: string;
}

export interface OptimizationResult {
  strategy: string;
  recommended_actions: string[];
  risk_adjustments: string[];
  timeline_optimization: string;
}

export interface GoalDecomposition {
  primary_objective: string;
  sub_objectives: string[];
  success_metrics: string[];
  time_constraints?: number;
  resource_requirements: any;
  risk_factors: string[];
  completion_probability: number;
}

export interface AnalyticsReport {
  timeframe: string;
  total_goals: number;
  completed_goals: number;
  failed_goals: number;
  cancelled_goals: number;
  in_progress_goals: number;
  overall_success_rate: number;
  avg_completion_time: number;
  median_completion_time: number;
  completion_time_std: number;
  total_target_value: number;
  total_achieved_value: number;
  achievement_ratio: number;
  avg_goal_size: number;
  goals_completed_on_time: number;
  goals_completed_early: number;
  goals_completed_late: number;
  avg_timeline_accuracy: number;
  most_successful_patterns: PerformancePattern[];
  least_successful_patterns: PerformancePattern[];
  emerging_patterns: string[];
  optimization_recommendations: string[];
  risk_warnings: string[];
  generated_at: string;
}

export interface CompletionPrediction {
  goal_id: string;
  completion_probability: number;
  estimated_completion_date?: string;
  confidence_interval: [number, number];
  key_factors: string[];
  risk_factors: string[];
  recommendation: string;
  model_used: string;
  prediction_accuracy: number;
}

export interface PerformancePattern {
  pattern_id: string;
  pattern_type: string;
  description: string;
  success_rate: number;
  avg_completion_time: number;
  common_characteristics: string[];
  optimal_conditions: string[];
  risk_indicators: string[];
  recommendation: string;
}

// AG-UI Connection Configuration
export const connectionConfig: ConnectionConfig = {
  // WebSocket connection for real-time events
  websocket: {
    url: process.env.NODE_ENV === 'production' 
      ? 'wss://your-production-domain.com/ws'
      : 'ws://localhost:8000/ws',
    reconnect: true,
    maxReconnectAttempts: 10,
    reconnectInterval: 5000,
    heartbeat: {
      enabled: true,
      interval: 30000,
      timeout: 5000
    }
  },
  
  // HTTP fallback for reliability
  http: {
    baseUrl: process.env.NODE_ENV === 'production'
      ? 'https://your-production-domain.com/api/v1'
      : 'http://localhost:8000/api/v1',
    timeout: 10000,
    retries: 3
  },
  
  // Authentication
  auth: {
    type: 'bearer',
    tokenKey: 'authToken',
    refreshTokenKey: 'refreshToken',
    autoRefresh: true
  }
};

// Event Transport Configuration
export const eventTransport: EventTransport = {
  // Primary transport: WebSocket for real-time
  primary: {
    type: 'websocket',
    config: connectionConfig.websocket
  },
  
  // Fallback transport: Server-Sent Events
  fallback: {
    type: 'sse',
    config: {
      url: `${connectionConfig.http.baseUrl}/events`,
      reconnect: true,
      maxReconnectAttempts: 5
    }
  },
  
  // Buffer configuration for offline resilience
  buffer: {
    enabled: true,
    maxSize: 1000,
    persistToDisk: true,
    flushOnReconnect: true
  }
};

// Main AG-UI Configuration
export const agUIConfig = {
  // Connection settings
  connection: connectionConfig,
  
  // Event transport
  transport: eventTransport,
  
  // Event processing
  events: {
    // Default event handlers
    onConnect: () => {
      console.log('🟢 AG-UI Protocol connected to trading platform');
    },
    
    onDisconnect: () => {
      console.log('🔴 AG-UI Protocol disconnected from trading platform');
    },
    
    onError: (error: Error) => {
      console.error('❌ AG-UI Protocol error:', error);
    },
    
    onReconnect: () => {
      console.log('🔄 AG-UI Protocol reconnected to trading platform');
    }
  },
  
  // Data validation and transformation
  validation: {
    enabled: true,
    strict: false, // Allow unknown event types for future extensibility
    transformIncoming: true,
    transformOutgoing: true
  },
  
  // Performance settings
  performance: {
    batchEvents: true,
    batchSize: 10,
    batchTimeout: 100, // ms
    compression: true
  },
  
  // Development settings
  debug: process.env.NODE_ENV === 'development',
  
  // Feature flags
  features: {
    realtimeUpdates: true,
    eventReplay: true,
    eventHistory: true,
    performanceMetrics: true,
    errorRecovery: true
  }
};

// Utility functions for AG-UI integration
export const agUIUtils = {
  /**
   * Create a goal event for AG-UI
   */
  createGoalEvent: (type: keyof TradingEvents, data: any) => ({
    type,
    timestamp: new Date().toISOString(),
    data
  }),
  
  /**
   * Format goal data for AG-UI transport
   */
  formatGoalData: (goal: any): GoalData => ({
    goal_id: goal.goal_id || '',
    original_text: goal.original_text || '',
    parsed_objective: goal.parsed_objective || '',
    priority: goal.priority || 'medium',
    complexity: goal.complexity || 'simple',
    status: goal.status || 'pending',
    target_value: Number(goal.target_value || 0),
    current_value: Number(goal.current_value || 0),
    progress_percentage: Number(goal.progress_percentage || 0),
    optimization_suggestions: goal.optimization_suggestions || [],
    risk_assessment: goal.risk_assessment || {
      overall_risk_score: 5,
      risk_factors: [],
      mitigation_strategies: [],
      probability_of_loss: 0.3,
      maximum_potential_loss: 0,
      risk_category: 'medium'
    },
    learning_insights: goal.learning_insights || [],
    estimated_completion: goal.estimated_completion,
    actual_start: goal.actual_start,
    actual_completion: goal.actual_completion,
    deadline: goal.deadline,
    created_at: goal.created_at || new Date().toISOString(),
    updated_at: goal.updated_at || new Date().toISOString(),
    wallet_id: goal.wallet_id,
    allocation_id: goal.allocation_id,
    metadata: goal.metadata || {}
  }),
  
  /**
   * Validate event data structure
   */
  validateEventData: (eventType: keyof TradingEvents, data: any): boolean => {
    try {
      // Basic validation - in production, use more robust schema validation
      return data && typeof data === 'object' && data.timestamp;
    } catch (error) {
      console.error('Event validation failed:', error);
      return false;
    }
  },
  
  /**
   * Get event priority for processing
   */
  getEventPriority: (eventType: keyof TradingEvents): 'high' | 'medium' | 'low' => {
    const highPriorityEvents = [
      'goal.completed',
      'trade.executed',
      'system.error',
      'agent.decision'
    ];
    
    const mediumPriorityEvents = [
      'goal.created',
      'goal.progress_updated',
      'wallet.transaction',
      'prediction.completed'
    ];
    
    if (highPriorityEvents.includes(eventType as any)) {
      return 'high';
    } else if (mediumPriorityEvents.includes(eventType as any)) {
      return 'medium';
    } else {
      return 'low';
    }
  }
};

export default agUIConfig;