/**
 * LLM Analytics Dashboard Component
 * Phase 10: Comprehensive LLM performance monitoring and analytics
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  TrendingUp,
  Clock,
  DollarSign,
  Activity,
  Zap,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  PieChart,
  RefreshCw,
  Settings,
  Filter,
  Download,
  Eye,
  MessageSquare,
  Target,
  Cpu,
  Database,
  Globe
} from 'lucide-react';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';

interface LLMProvider {
  provider: string;
  model_name: string;
  status: 'active' | 'inactive' | 'error';
  total_requests: number;
  total_tokens: number;
  avg_response_time: number;
  success_rate: number;
  cost_per_token: number;
  total_cost: number;
  last_request: string;
}

interface LLMUsageMetrics {
  provider: string;
  task_type: string;
  requests_last_24h: number;
  tokens_last_24h: number;
  avg_confidence: number;
  error_rate: number;
  cost_last_24h: number;
  popular_tasks: Array<{ task: string; count: number }>;
}

interface ConversationAnalytics {
  total_conversations: number;
  active_conversations: number;
  avg_participants: number;
  avg_messages_per_conversation: number;
  most_active_agents: Array<{ agent_id: string; message_count: number }>;
  common_topics: Array<{ topic: string; frequency: number }>;
}

interface PerformanceMetrics {
  accuracy_score: number;
  response_quality: number;
  consistency_score: number;
  cost_efficiency: number;
  speed_score: number;
  overall_score: number;
}

interface LLMAnalyticsDashboardProps {
  className?: string;
}

export const LLMAnalyticsDashboard: React.FC<LLMAnalyticsDashboardProps> = ({
  className = ''
}) => {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [usageMetrics, setUsageMetrics] = useState<LLMUsageMetrics[]>([]);
  const [conversationAnalytics, setConversationAnalytics] = useState<ConversationAnalytics | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<Record<string, PerformanceMetrics>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState('24h');
  const [selectedProvider, setSelectedProvider] = useState('all');
  const [showDetailedMetrics, setShowDetailedMetrics] = useState(false);

  // Subscribe to LLM events
  useEffect(() => {
    const subscriptions = [
      subscribe('llm.request_processed', (data) => {
        console.log('🧠 LLM request processed:', data);
        loadAllData();
      }),

      subscribe('llm.provider_status_changed', (data) => {
        console.log('⚙️ LLM provider status changed:', data);
        loadProviders();
      }),

      subscribe('conversation.analytics_updated', (data) => {
        console.log('💬 Conversation analytics updated:', data);
        loadConversationAnalytics();
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

  // Load data on mount
  useEffect(() => {
    loadAllData();
  }, [selectedTimeframe, selectedProvider]);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        loadProviders(),
        loadUsageMetrics(),
        loadConversationAnalytics(),
        loadPerformanceMetrics()
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProviders = async () => {
    // Mock provider data
    const mockProviders: LLMProvider[] = [
      {
        provider: 'openai_gpt4',
        model_name: 'gpt-4-turbo-preview',
        status: 'active',
        total_requests: 1247,
        total_tokens: 156832,
        avg_response_time: 2.3,
        success_rate: 98.2,
        cost_per_token: 0.00003,
        total_cost: 4.70,
        last_request: '2025-06-14T15:45:23Z'
      },
      {
        provider: 'anthropic_claude',
        model_name: 'claude-3-opus-20240229',
        status: 'active',
        total_requests: 892,
        total_tokens: 98543,
        avg_response_time: 1.8,
        success_rate: 99.1,
        cost_per_token: 0.000015,
        total_cost: 1.48,
        last_request: '2025-06-14T15:44:17Z'
      },
      {
        provider: 'huggingface_local',
        model_name: 'microsoft/DialoGPT-medium',
        status: 'active',
        total_requests: 2156,
        total_tokens: 67234,
        avg_response_time: 0.8,
        success_rate: 94.5,
        cost_per_token: 0.0,
        total_cost: 0.0,
        last_request: '2025-06-14T15:46:01Z'
      }
    ];

    setProviders(mockProviders);
  };

  const loadUsageMetrics = async () => {
    // Mock usage metrics
    const mockUsageMetrics: LLMUsageMetrics[] = [
      {
        provider: 'openai_gpt4',
        task_type: 'market_analysis',
        requests_last_24h: 245,
        tokens_last_24h: 32145,
        avg_confidence: 0.87,
        error_rate: 1.2,
        cost_last_24h: 0.96,
        popular_tasks: [
          { task: 'trend_analysis', count: 89 },
          { task: 'risk_assessment', count: 67 },
          { task: 'portfolio_optimization', count: 45 }
        ]
      },
      {
        provider: 'anthropic_claude',
        task_type: 'agent_communication',
        requests_last_24h: 178,
        tokens_last_24h: 19876,
        avg_confidence: 0.92,
        error_rate: 0.8,
        cost_last_24h: 0.30,
        popular_tasks: [
          { task: 'conversation_moderation', count: 76 },
          { task: 'decision_synthesis', count: 54 },
          { task: 'conflict_resolution', count: 23 }
        ]
      }
    ];

    setUsageMetrics(mockUsageMetrics);
  };

  const loadConversationAnalytics = async () => {
    // Mock conversation analytics
    const mockConversationAnalytics: ConversationAnalytics = {
      total_conversations: 127,
      active_conversations: 8,
      avg_participants: 3.2,
      avg_messages_per_conversation: 15.7,
      most_active_agents: [
        { agent_id: 'trend_follower_001', message_count: 234 },
        { agent_id: 'risk_manager_007', message_count: 198 },
        { agent_id: 'arbitrage_bot_003', message_count: 176 },
        { agent_id: 'mean_reversion_002', message_count: 145 }
      ],
      common_topics: [
        { topic: 'Market Analysis', frequency: 45 },
        { topic: 'Risk Assessment', frequency: 32 },
        { topic: 'Portfolio Rebalancing', frequency: 28 },
        { topic: 'Strategy Discussion', frequency: 22 }
      ]
    };

    setConversationAnalytics(mockConversationAnalytics);
  };

  const loadPerformanceMetrics = async () => {
    // Mock performance metrics
    const mockPerformanceMetrics: Record<string, PerformanceMetrics> = {
      'openai_gpt4': {
        accuracy_score: 0.89,
        response_quality: 0.92,
        consistency_score: 0.85,
        cost_efficiency: 0.73,
        speed_score: 0.78,
        overall_score: 0.83
      },
      'anthropic_claude': {
        accuracy_score: 0.94,
        response_quality: 0.96,
        consistency_score: 0.91,
        cost_efficiency: 0.87,
        speed_score: 0.82,
        overall_score: 0.90
      },
      'huggingface_local': {
        accuracy_score: 0.76,
        response_quality: 0.71,
        consistency_score: 0.78,
        cost_efficiency: 1.0,
        speed_score: 0.95,
        overall_score: 0.84
      }
    };

    setPerformanceMetrics(mockPerformanceMetrics);
  };

  const refreshData = async () => {
    emit('llm.refresh_analytics', {
      timeframe: selectedTimeframe,
      provider: selectedProvider
    });
    await loadAllData();
  };

  const exportAnalytics = () => {
    const data = {
      providers,
      usageMetrics,
      conversationAnalytics,
      performanceMetrics,
      exportedAt: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `llm-analytics-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-100';
      case 'inactive': return 'text-yellow-600 bg-yellow-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getPerformanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg shadow-lg border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
            <span className="text-gray-600">Loading LLM analytics...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Brain className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">LLM Analytics Dashboard</h3>
              <p className="text-sm text-gray-600">
                Performance monitoring and usage analytics for AI language models
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="1h">Last Hour</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>

            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="all">All Providers</option>
              {providers.map((provider) => (
                <option key={provider.provider} value={provider.provider}>
                  {provider.model_name}
                </option>
              ))}
            </select>

            <button
              onClick={refreshData}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh data"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            <button
              onClick={exportAnalytics}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Export analytics"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Overview Metrics */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-2">
              <Activity className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {providers.reduce((sum, p) => sum + p.total_requests, 0).toLocaleString()}
            </div>
            <p className="text-sm text-gray-600">Total Requests</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mx-auto mb-2">
              <Zap className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {providers.reduce((sum, p) => sum + p.total_tokens, 0).toLocaleString()}
            </div>
            <p className="text-sm text-gray-600">Total Tokens</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg mx-auto mb-2">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {(providers.reduce((sum, p) => sum + p.avg_response_time, 0) / providers.length).toFixed(1)}s
            </div>
            <p className="text-sm text-gray-600">Avg Response Time</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-2">
              <DollarSign className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              ${providers.reduce((sum, p) => sum + p.total_cost, 0).toFixed(2)}
            </div>
            <p className="text-sm text-gray-600">Total Cost</p>
          </div>
        </div>
      </div>

      {/* Provider Status */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h4 className="text-md font-medium text-gray-900 mb-4">Provider Status</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {providers.map((provider) => (
            <motion.div
              key={provider.provider}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 border border-gray-200 rounded-lg"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h5 className="font-medium text-gray-900">{provider.model_name}</h5>
                  <p className="text-sm text-gray-600">{provider.provider}</p>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(provider.status)}`}>
                  {provider.status}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Requests:</span>
                  <span className="font-medium">{provider.total_requests.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Success Rate:</span>
                  <span className={`font-medium ${getPerformanceColor(provider.success_rate / 100)}`}>
                    {provider.success_rate.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Avg Response:</span>
                  <span className="font-medium">{provider.avg_response_time.toFixed(1)}s</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Cost:</span>
                  <span className="font-medium">${provider.total_cost.toFixed(2)}</span>
                </div>
              </div>

              {/* Performance Bar */}
              <div className="mt-3">
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>Performance</span>
                  <span>{(performanceMetrics[provider.provider]?.overall_score * 100 || 0).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(performanceMetrics[provider.provider]?.overall_score * 100) || 0}%` }}
                  />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Usage Analytics */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-md font-medium text-gray-900">Usage Analytics</h4>
          <button
            onClick={() => setShowDetailedMetrics(!showDetailedMetrics)}
            className="px-3 py-1 text-sm text-purple-600 bg-purple-50 rounded hover:bg-purple-100 transition-colors"
          >
            <Eye className="w-3 h-3 mr-1 inline" />
            {showDetailedMetrics ? 'Hide' : 'Show'} Details
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Task Distribution Chart */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h5 className="font-medium text-gray-900 mb-3">Task Distribution</h5>
            <div className="space-y-3">
              {usageMetrics.map((metric) => (
                <div key={`${metric.provider}-${metric.task_type}`}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{metric.task_type.replace('_', ' ')}</span>
                    <span className="font-medium">{metric.requests_last_24h}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full"
                      style={{ 
                        width: `${(metric.requests_last_24h / Math.max(...usageMetrics.map(m => m.requests_last_24h))) * 100}%` 
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Conversation Analytics */}
          {conversationAnalytics && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h5 className="font-medium text-gray-900 mb-3">Conversation Analytics</h5>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Conversations:</span>
                  <span className="font-medium">{conversationAnalytics.total_conversations}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Active Now:</span>
                  <span className="font-medium text-green-600">{conversationAnalytics.active_conversations}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Avg Participants:</span>
                  <span className="font-medium">{conversationAnalytics.avg_participants.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Avg Messages:</span>
                  <span className="font-medium">{conversationAnalytics.avg_messages_per_conversation.toFixed(1)}</span>
                </div>
              </div>

              <div className="mt-4">
                <h6 className="text-sm font-medium text-gray-900 mb-2">Most Active Agents</h6>
                <div className="space-y-1">
                  {conversationAnalytics.most_active_agents.slice(0, 3).map((agent, index) => (
                    <div key={agent.agent_id} className="flex justify-between text-sm">
                      <span className="text-gray-600">#{index + 1} {agent.agent_id}</span>
                      <span className="font-medium">{agent.message_count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detailed Performance Metrics */}
      <AnimatePresence>
        {showDetailedMetrics && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 border-b border-gray-200"
          >
            <h4 className="text-md font-medium text-gray-900 mb-4">Detailed Performance Metrics</h4>
            
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 text-gray-600">Provider</th>
                    <th className="text-center py-2 text-gray-600">Accuracy</th>
                    <th className="text-center py-2 text-gray-600">Quality</th>
                    <th className="text-center py-2 text-gray-600">Consistency</th>
                    <th className="text-center py-2 text-gray-600">Cost Efficiency</th>
                    <th className="text-center py-2 text-gray-600">Speed</th>
                    <th className="text-center py-2 text-gray-600">Overall</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(performanceMetrics).map(([provider, metrics]) => (
                    <tr key={provider} className="border-b border-gray-100">
                      <td className="py-3 font-medium text-gray-900">
                        {providers.find(p => p.provider === provider)?.model_name || provider}
                      </td>
                      <td className="text-center py-3">
                        <span className={`font-medium ${getPerformanceColor(metrics.accuracy_score)}`}>
                          {(metrics.accuracy_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-center py-3">
                        <span className={`font-medium ${getPerformanceColor(metrics.response_quality)}`}>
                          {(metrics.response_quality * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-center py-3">
                        <span className={`font-medium ${getPerformanceColor(metrics.consistency_score)}`}>
                          {(metrics.consistency_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-center py-3">
                        <span className={`font-medium ${getPerformanceColor(metrics.cost_efficiency)}`}>
                          {(metrics.cost_efficiency * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-center py-3">
                        <span className={`font-medium ${getPerformanceColor(metrics.speed_score)}`}>
                          {(metrics.speed_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-center py-3">
                        <span className={`font-bold ${getPerformanceColor(metrics.overall_score)}`}>
                          {(metrics.overall_score * 100).toFixed(0)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Real-time Activity Feed */}
      <div className="px-6 py-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">Recent Activity</h4>
        
        <div className="space-y-3">
          <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <Brain className="w-4 h-4 text-blue-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Market analysis completed</p>
              <p className="text-xs text-gray-600">GPT-4 analyzed BTC/USD trends • 2 minutes ago</p>
            </div>
            <div className="text-xs text-gray-500">1,247 tokens</div>
          </div>

          <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Agent conversation facilitated</p>
              <p className="text-xs text-gray-600">Claude moderated risk discussion • 5 minutes ago</p>
            </div>
            <div className="text-xs text-gray-500">892 tokens</div>
          </div>

          <div className="flex items-center space-x-3 p-3 bg-purple-50 rounded-lg">
            <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
              <Target className="w-4 h-4 text-purple-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Trading strategy generated</p>
              <p className="text-xs text-gray-600">Local model created momentum strategy • 8 minutes ago</p>
            </div>
            <div className="text-xs text-gray-500">2,156 tokens</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LLMAnalyticsDashboard;