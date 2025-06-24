/**
 * Real-Time Dashboard Component
 * Phase 11: Live monitoring of autonomous agents and trading operations
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Brain,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  Target,
  Users,
  MessageSquare,
  BarChart3,
  PieChart,
  RefreshCw,
  Play,
  Pause,
  Settings,
  Maximize2,
  Minimize2,
  Filter,
  Bell,
  BellOff
} from 'lucide-react';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';

interface AgentStatus {
  agent_id: string;
  name: string;
  status: 'active' | 'busy' | 'paused' | 'error';
  performance_score: number;
  last_activity: string;
  current_task?: string;
  pnl: number;
  trades_today: number;
}

interface TradingMetrics {
  total_portfolio_value: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  active_positions: number;
  open_orders: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
}

interface DecisionEvent {
  decision_id: string;
  type: string;
  participants: string[];
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result?: string;
  confidence?: number;
  timestamp: string;
}

interface MarketAlert {
  alert_id: string;
  type: 'opportunity' | 'risk' | 'system' | 'performance';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  agent_id?: string;
  timestamp: string;
  is_resolved: boolean;
}

interface RealTimeDashboardProps {
  className?: string;
}

export const RealTimeDashboard: React.FC<RealTimeDashboardProps> = ({
  className = ''
}) => {
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
  const [tradingMetrics, setTradingMetrics] = useState<TradingMetrics | null>(null);
  const [recentDecisions, setRecentDecisions] = useState<DecisionEvent[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<MarketAlert[]>([]);
  const [isLive, setIsLive] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');
  const [selectedFilter, setSelectedFilter] = useState('all');

  const dashboardRef = useRef<HTMLDivElement>(null);

  // Subscribe to real-time events
  useEffect(() => {
    const subscriptions = [
      subscribe('agents.status_update', (data) => {
        console.log('🤖 Agent status update:', data);
        updateAgentStatuses(data.agent_status);
      }),

      subscribe('trading.metrics_update', (data) => {
        console.log('📊 Trading metrics update:', data);
        setTradingMetrics(data);
      }),

      subscribe('decision.completed', (data) => {
        console.log('🎯 Decision completed:', data);
        addDecisionEvent(data);
      }),

      subscribe('alert.created', (data) => {
        console.log('🚨 Alert created:', data);
        addAlert(data);
      }),

      subscribe('alert.resolved', (data) => {
        console.log('✅ Alert resolved:', data);
        resolveAlert(data.alert_id);
      }),

      subscribe('portfolio.position_update', (data) => {
        console.log('💼 Position update:', data);
        // Update relevant metrics
      }),

      subscribe('llm.request_processed', (data) => {
        console.log('🧠 LLM request processed:', data);
        // Update LLM activity indicators
      })
    ];

    return () => {
      subscriptions.forEach(subscriptionId => {
        if (subscriptionId) {
          unsubscribe(subscriptionId);
        }
      });
    };
  }, []);

  // Auto-refresh data
  useEffect(() => {
    if (isLive) {
      const interval = setInterval(() => {
        refreshDashboardData();
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [isLive]);

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    // Load mock data
    const mockAgentStatuses: AgentStatus[] = [
      {
        agent_id: 'trend_follower_001',
        name: 'Marcus Momentum',
        status: 'active',
        performance_score: 78.5,
        last_activity: new Date().toISOString(),
        current_task: 'Analyzing BTC/USD trend',
        pnl: 1250.75,
        trades_today: 5
      },
      {
        agent_id: 'arbitrage_bot_003',
        name: 'Alex Arbitrage',
        status: 'busy',
        performance_score: 82.1,
        last_activity: new Date().toISOString(),
        current_task: 'Executing arbitrage opportunity',
        pnl: 675.50,
        trades_today: 12
      },
      {
        agent_id: 'mean_reversion_002',
        name: 'Sophia Reversion',
        status: 'active',
        performance_score: 69.3,
        last_activity: new Date().toISOString(),
        current_task: 'Monitoring oversold conditions',
        pnl: 420.25,
        trades_today: 3
      },
      {
        agent_id: 'risk_manager_007',
        name: 'Riley Risk',
        status: 'active',
        performance_score: 91.8,
        last_activity: new Date().toISOString(),
        current_task: 'Portfolio risk assessment',
        pnl: 0, // Risk manager doesn't trade
        trades_today: 0
      }
    ];

    const mockTradingMetrics: TradingMetrics = {
      total_portfolio_value: 52346.25,
      daily_pnl: 1346.50,
      daily_pnl_percentage: 2.64,
      active_positions: 8,
      open_orders: 3,
      win_rate: 68.4,
      sharpe_ratio: 1.85,
      max_drawdown: 8.2
    };

    const mockDecisions: DecisionEvent[] = [
      {
        decision_id: 'dec_001',
        type: 'portfolio_allocation',
        participants: ['trend_follower_001', 'risk_manager_007'],
        status: 'completed',
        result: 'Increase BTC allocation by 5%',
        confidence: 0.87,
        timestamp: new Date(Date.now() - 300000).toISOString() // 5 minutes ago
      },
      {
        decision_id: 'dec_002',
        type: 'trading',
        participants: ['arbitrage_bot_003'],
        status: 'in_progress',
        timestamp: new Date(Date.now() - 120000).toISOString() // 2 minutes ago
      }
    ];

    const mockAlerts: MarketAlert[] = [
      {
        alert_id: 'alert_001',
        type: 'opportunity',
        severity: 'high',
        title: 'High Arbitrage Spread Detected',
        message: 'BTC/USD spread between Binance and Coinbase: 0.23%',
        agent_id: 'arbitrage_bot_003',
        timestamp: new Date(Date.now() - 180000).toISOString(),
        is_resolved: false
      },
      {
        alert_id: 'alert_002',
        type: 'risk',
        severity: 'medium',
        title: 'Portfolio Exposure Warning',
        message: 'BTC exposure approaching 40% limit',
        agent_id: 'risk_manager_007',
        timestamp: new Date(Date.now() - 600000).toISOString(),
        is_resolved: false
      }
    ];

    setAgentStatuses(mockAgentStatuses);
    setTradingMetrics(mockTradingMetrics);
    setRecentDecisions(mockDecisions);
    setActiveAlerts(mockAlerts);
  };

  const refreshDashboardData = () => {
    emit('dashboard.refresh_request', {
      timeframe: selectedTimeframe,
      filter: selectedFilter
    });
  };

  const updateAgentStatuses = (agentStatusData: Record<string, any>) => {
    const updatedStatuses = Object.entries(agentStatusData).map(([agentId, data]) => ({
      agent_id: agentId,
      name: data.name || agentId,
      status: data.status,
      performance_score: data.performance?.performance_score || 0,
      last_activity: new Date().toISOString(),
      current_task: data.current_task,
      pnl: data.performance?.total_pnl || 0,
      trades_today: data.performance?.total_trades || 0
    }));

    setAgentStatuses(updatedStatuses);
  };

  const addDecisionEvent = (decision: any) => {
    const newDecision: DecisionEvent = {
      decision_id: decision.decision_id,
      type: decision.decision_type,
      participants: decision.participating_agents || [],
      status: 'completed',
      result: decision.recommendation,
      confidence: decision.confidence,
      timestamp: new Date().toISOString()
    };

    setRecentDecisions(prev => [newDecision, ...prev.slice(0, 9)]); // Keep last 10
  };

  const addAlert = (alert: any) => {
    const newAlert: MarketAlert = {
      alert_id: alert.alert_id,
      type: alert.alert_type,
      severity: alert.severity,
      title: alert.title,
      message: alert.message,
      agent_id: alert.agent_id,
      timestamp: new Date().toISOString(),
      is_resolved: false
    };

    setActiveAlerts(prev => [newAlert, ...prev]);

    // Play alert sound if enabled
    if (alertsEnabled && alert.severity !== 'low') {
      playAlertSound(alert.severity);
    }
  };

  const resolveAlert = (alertId: string) => {
    setActiveAlerts(prev =>
      prev.map(alert =>
        alert.alert_id === alertId
          ? { ...alert, is_resolved: true }
          : alert
      )
    );
  };

  const playAlertSound = (severity: string) => {
    // In a real implementation, this would play appropriate alert sounds
    console.log(`Alert sound: ${severity}`);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-100';
      case 'busy': return 'text-blue-600 bg-blue-100';
      case 'paused': return 'text-yellow-600 bg-yellow-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-100 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-100 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-100 border-blue-200';
      default: return 'text-gray-600 bg-gray-100 border-gray-200';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  if (!tradingMetrics) {
    return (
      <div className={`bg-white rounded-lg shadow-lg border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
            <span className="text-gray-600">Loading real-time data...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      ref={dashboardRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`bg-white rounded-lg shadow-lg border border-gray-200 ${isExpanded ? 'fixed inset-4 z-50' : ''} ${className}`}
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Real-Time Dashboard</h3>
              <p className="text-sm text-gray-600">
                Live monitoring of autonomous trading operations
              </p>
            </div>
            {isLive && (
              <div className="flex items-center space-x-2 text-green-600">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">LIVE</span>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="5m">5 minutes</option>
              <option value="15m">15 minutes</option>
              <option value="1h">1 hour</option>
              <option value="4h">4 hours</option>
              <option value="1d">1 day</option>
            </select>

            <button
              onClick={() => setAlertsEnabled(!alertsEnabled)}
              className={`p-2 rounded-lg transition-colors ${
                alertsEnabled ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
              }`}
              title={alertsEnabled ? 'Disable alerts' : 'Enable alerts'}
            >
              {alertsEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
            </button>

            <button
              onClick={() => setIsLive(!isLive)}
              className={`p-2 rounded-lg transition-colors ${
                isLive ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'
              }`}
              title={isLive ? 'Pause live updates' : 'Resume live updates'}
            >
              {isLive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>

            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title={isExpanded ? 'Minimize' : 'Expand'}
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            <button
              onClick={refreshDashboardData}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh data"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mx-auto mb-2">
              <DollarSign className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(tradingMetrics.total_portfolio_value)}
            </div>
            <p className="text-sm text-gray-600">Portfolio Value</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-2">
              {tradingMetrics.daily_pnl >= 0 ? (
                <TrendingUp className="w-6 h-6 text-blue-600" />
              ) : (
                <TrendingDown className="w-6 h-6 text-blue-600" />
              )}
            </div>
            <div className={`text-2xl font-bold ${tradingMetrics.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(tradingMetrics.daily_pnl)}
            </div>
            <p className="text-sm text-gray-600">
              Daily P&L ({tradingMetrics.daily_pnl_percentage >= 0 ? '+' : ''}{tradingMetrics.daily_pnl_percentage.toFixed(2)}%)
            </p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-2">
              <Target className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {tradingMetrics.active_positions}
            </div>
            <p className="text-sm text-gray-600">Active Positions</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg mx-auto mb-2">
              <BarChart3 className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {tradingMetrics.win_rate.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-600">Win Rate</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
        {/* Agent Status */}
        <div>
          <h4 className="text-md font-medium text-gray-900 mb-4 flex items-center">
            <Users className="w-4 h-4 mr-2" />
            Agent Status
          </h4>
          
          <div className="space-y-3">
            {agentStatuses.map((agent) => (
              <motion.div
                key={agent.agent_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="p-4 border border-gray-200 rounded-lg"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      agent.status === 'active' ? 'bg-green-400' :
                      agent.status === 'busy' ? 'bg-blue-400' :
                      agent.status === 'paused' ? 'bg-yellow-400' : 'bg-red-400'
                    }`}></div>
                    <div>
                      <h5 className="font-medium text-gray-900">{agent.name}</h5>
                      <p className="text-sm text-gray-600">{agent.current_task || 'Idle'}</p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">
                      Score: {agent.performance_score.toFixed(1)}
                    </div>
                    <div className="text-sm text-gray-600">
                      {agent.trades_today} trades • {formatCurrency(agent.pnl)}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Recent Decisions & Alerts */}
        <div>
          <h4 className="text-md font-medium text-gray-900 mb-4 flex items-center">
            <Brain className="w-4 h-4 mr-2" />
            Recent Activity
          </h4>
          
          <div className="space-y-3">
            {/* Active Alerts */}
            {activeAlerts.filter(alert => !alert.is_resolved).slice(0, 3).map((alert) => (
              <motion.div
                key={alert.alert_id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 border rounded-lg ${getSeverityColor(alert.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5" />
                    <div>
                      <h6 className="font-medium text-sm">{alert.title}</h6>
                      <p className="text-xs opacity-90">{alert.message}</p>
                    </div>
                  </div>
                  <span className="text-xs opacity-75">{formatTimestamp(alert.timestamp)}</span>
                </div>
              </motion.div>
            ))}

            {/* Recent Decisions */}
            {recentDecisions.slice(0, 3).map((decision) => (
              <motion.div
                key={decision.decision_id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 border border-gray-200 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-2">
                    {decision.status === 'completed' ? (
                      <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />
                    ) : decision.status === 'in_progress' ? (
                      <Clock className="w-4 h-4 text-blue-600 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5" />
                    )}
                    <div>
                      <h6 className="font-medium text-sm text-gray-900">
                        {decision.type.replace('_', ' ')} Decision
                      </h6>
                      <p className="text-xs text-gray-600">
                        {decision.result || 'In progress...'}
                      </p>
                      <p className="text-xs text-gray-500">
                        Agents: {decision.participants.join(', ')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {decision.confidence && (
                      <div className="text-xs text-gray-600">
                        {(decision.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      {formatTimestamp(decision.timestamp)}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default RealTimeDashboard;