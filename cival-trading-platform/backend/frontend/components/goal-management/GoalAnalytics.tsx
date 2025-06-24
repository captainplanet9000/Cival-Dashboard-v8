/**
 * Goal Analytics Component
 * Phase 8: Performance visualization with real-time AG-UI data
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Target,
  Clock,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Brain,
  Calendar,
  Filter,
  Download,
  RefreshCw
} from 'lucide-react';

import { eventTransport, subscribe, unsubscribe, emit } from '../../ag-ui-setup/event-transport';
import { AnalyticsReport, PerformancePattern } from '../../ag-ui-setup/ag-ui-config';

interface GoalAnalyticsProps {
  className?: string;
  timeframe?: 'last_24h' | 'last_7d' | 'last_30d' | 'last_90d' | 'all_time';
  onTimeframeChange?: (timeframe: string) => void;
}

const CHART_COLORS = {
  primary: '#3B82F6',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  secondary: '#6B7280',
  accent: '#8B5CF6'
};

const TIMEFRAME_OPTIONS = [
  { value: 'last_24h', label: 'Last 24 Hours' },
  { value: 'last_7d', label: 'Last 7 Days' },
  { value: 'last_30d', label: 'Last 30 Days' },
  { value: 'last_90d', label: 'Last 90 Days' },
  { value: 'all_time', label: 'All Time' }
];

export const GoalAnalytics: React.FC<GoalAnalyticsProps> = ({
  className = '',
  timeframe = 'last_30d',
  onTimeframeChange
}) => {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState<'completion' | 'performance' | 'timeline' | 'patterns'>('completion');
  const [showPatterns, setShowPatterns] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  
  // Subscribe to analytics events
  useEffect(() => {
    const subscriptions = [
      subscribe('analytics.report_generated', (data) => {
        if (data.timeframe === timeframe) {
          console.log('📊 Analytics report received:', data);
          setAnalyticsData(data.report);
          setIsLoading(false);
          setLastUpdated(new Date());
        }
      }),
      
      subscribe('pattern.identified', (data) => {
        console.log('🔍 New pattern identified:', data);
        // Refresh analytics to include new pattern
        requestAnalyticsReport();
      })
    ];
    
    return () => {
      subscriptions.forEach(subscriptionId => {
        if (typeof subscriptionId === 'string') {
          unsubscribe(subscriptionId);
        }
      });
    };
  }, [timeframe]);
  
  // Request analytics report
  const requestAnalyticsReport = () => {
    setIsLoading(true);
    emit('analytics.request_report', {
      timeframe,
      include_patterns: true,
      include_predictions: true
    });
  };
  
  // Initial data load
  useEffect(() => {
    requestAnalyticsReport();
  }, [timeframe]);
  
  // Handle timeframe change
  const handleTimeframeChange = (newTimeframe: string) => {
    if (onTimeframeChange) {
      onTimeframeChange(newTimeframe);
    }
    requestAnalyticsReport();
  };
  
  // Prepare chart data
  const chartData = React.useMemo(() => {
    if (!analyticsData) return null;
    
    const completionData = [
      { name: 'Completed', value: analyticsData.completed_goals, color: CHART_COLORS.success },
      { name: 'In Progress', value: analyticsData.in_progress_goals, color: CHART_COLORS.primary },
      { name: 'Failed', value: analyticsData.failed_goals, color: CHART_COLORS.danger },
      { name: 'Cancelled', value: analyticsData.cancelled_goals, color: CHART_COLORS.secondary }
    ];
    
    const timelineData = [
      { name: 'On Time', value: analyticsData.goals_completed_on_time, color: CHART_COLORS.success },
      { name: 'Early', value: analyticsData.goals_completed_early, color: CHART_COLORS.accent },
      { name: 'Late', value: analyticsData.goals_completed_late, color: CHART_COLORS.warning }
    ];
    
    const performanceData = [
      {
        name: 'Success Rate',
        value: analyticsData.overall_success_rate,
        target: 80,
        color: CHART_COLORS.success
      },
      {
        name: 'Timeline Accuracy',
        value: analyticsData.avg_timeline_accuracy,
        target: 90,
        color: CHART_COLORS.primary
      },
      {
        name: 'Achievement Ratio',
        value: analyticsData.achievement_ratio,
        target: 95,
        color: CHART_COLORS.accent
      }
    ];
    
    return {
      completion: completionData,
      timeline: timelineData,
      performance: performanceData
    };
  }, [analyticsData]);
  
  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };
  
  // Format percentage
  const formatPercent = (value: number) => {
    return `${value.toFixed(1)}%`;
  };
  
  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
            <span className="text-gray-600">Loading analytics...</span>
          </div>
        </div>
      </div>
    );
  }
  
  if (!analyticsData) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="text-center py-8">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">No analytics data available</p>
          <button
            onClick={requestAnalyticsReport}
            className="mt-3 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            Refresh Data
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <BarChart3 className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Goal Analytics</h3>
              <p className="text-sm text-gray-600">
                Performance insights and pattern analysis
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Timeframe Selector */}
            <select
              value={timeframe}
              onChange={(e) => handleTimeframeChange(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {TIMEFRAME_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            
            <button
              onClick={requestAnalyticsReport}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh data"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => setShowPatterns(!showPatterns)}
              className={`p-2 transition-colors ${
                showPatterns ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
              }`}
              title="Show patterns"
            >
              <Brain className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Key Metrics */}
      <div className="p-6 border-b border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mx-auto mb-2">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {formatPercent(analyticsData.overall_success_rate)}
            </div>
            <p className="text-sm text-gray-600">Success Rate</p>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-2">
              <Target className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {analyticsData.total_goals}
            </div>
            <p className="text-sm text-gray-600">Total Goals</p>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg mx-auto mb-2">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {analyticsData.avg_completion_time.toFixed(1)}d
            </div>
            <p className="text-sm text-gray-600">Avg. Completion</p>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-2">
              <DollarSign className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(analyticsData.total_achieved_value)}
            </div>
            <p className="text-sm text-gray-600">Total Achieved</p>
          </div>
        </div>
      </div>
      
      {/* Metric Selector */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex space-x-1">
          {[
            { key: 'completion', label: 'Completion', icon: CheckCircle },
            { key: 'performance', label: 'Performance', icon: TrendingUp },
            { key: 'timeline', label: 'Timeline', icon: Clock },
            { key: 'patterns', label: 'Patterns', icon: Brain }
          ].map((metric) => {
            const Icon = metric.icon;
            return (
              <button
                key={metric.key}
                onClick={() => setSelectedMetric(metric.key as any)}
                className={`flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  selectedMetric === metric.key
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {metric.label}
              </button>
            );
          })}
        </div>
      </div>
      
      {/* Charts */}
      <div className="p-6">
        <AnimatePresence mode="wait">
          {selectedMetric === 'completion' && chartData && (
            <motion.div
              key="completion"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h4 className="text-lg font-medium text-gray-900 mb-4">Goal Completion Status</h4>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Pie Chart */}
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData.completion}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {chartData.completion.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                
                {/* Bar Chart */}
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData.completion}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" fill={CHART_COLORS.primary} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </motion.div>
          )}
          
          {selectedMetric === 'performance' && chartData && (
            <motion.div
              key="performance"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h4 className="text-lg font-medium text-gray-900 mb-4">Performance Metrics</h4>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData.performance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip formatter={(value) => `${value}%`} />
                    <Legend />
                    <Bar dataKey="value" fill={CHART_COLORS.primary} name="Actual" />
                    <Bar dataKey="target" fill={CHART_COLORS.success} name="Target" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          )}
          
          {selectedMetric === 'timeline' && chartData && (
            <motion.div
              key="timeline"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h4 className="text-lg font-medium text-gray-900 mb-4">Timeline Performance</h4>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData.timeline}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {chartData.timeline.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                
                <div className="space-y-4">
                  <div className="p-4 bg-green-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-green-800">Timeline Accuracy</span>
                      <span className="text-lg font-bold text-green-900">
                        {formatPercent(analyticsData.avg_timeline_accuracy)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-blue-800">Avg. Completion Time</span>
                      <span className="text-lg font-bold text-blue-900">
                        {analyticsData.avg_completion_time.toFixed(1)} days
                      </span>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-purple-800">Median Time</span>
                      <span className="text-lg font-bold text-purple-900">
                        {analyticsData.median_completion_time.toFixed(1)} days
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          {selectedMetric === 'patterns' && (
            <motion.div
              key="patterns"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h4 className="text-lg font-medium text-gray-900 mb-4">Performance Patterns</h4>
              
              <div className="space-y-6">
                {/* Successful Patterns */}
                {analyticsData.most_successful_patterns.length > 0 && (
                  <div>
                    <h5 className="text-md font-medium text-green-800 mb-3 flex items-center">
                      <TrendingUp className="w-4 h-4 mr-2" />
                      Most Successful Patterns
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {analyticsData.most_successful_patterns.slice(0, 4).map((pattern, index) => (
                        <div key={index} className="p-4 bg-green-50 border border-green-200 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-green-900">{pattern.description}</span>
                            <span className="text-sm text-green-700">
                              {formatPercent(pattern.success_rate)}
                            </span>
                          </div>
                          <p className="text-sm text-green-700">{pattern.recommendation}</p>
                          <div className="mt-2 text-xs text-green-600">
                            Avg. completion: {pattern.avg_completion_time} days
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Unsuccessful Patterns */}
                {analyticsData.least_successful_patterns.length > 0 && (
                  <div>
                    <h5 className="text-md font-medium text-red-800 mb-3 flex items-center">
                      <TrendingDown className="w-4 h-4 mr-2" />
                      Areas for Improvement
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {analyticsData.least_successful_patterns.slice(0, 2).map((pattern, index) => (
                        <div key={index} className="p-4 bg-red-50 border border-red-200 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-red-900">{pattern.description}</span>
                            <span className="text-sm text-red-700">
                              {formatPercent(pattern.success_rate)}
                            </span>
                          </div>
                          <p className="text-sm text-red-700">{pattern.recommendation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Emerging Patterns */}
                {analyticsData.emerging_patterns.length > 0 && (
                  <div>
                    <h5 className="text-md font-medium text-blue-800 mb-3 flex items-center">
                      <Activity className="w-4 h-4 mr-2" />
                      Emerging Trends
                    </h5>
                    <div className="space-y-2">
                      {analyticsData.emerging_patterns.map((pattern, index) => (
                        <div key={index} className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <p className="text-sm text-blue-700">{pattern}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Recommendations */}
      {(analyticsData.optimization_recommendations.length > 0 || analyticsData.risk_warnings.length > 0) && (
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Optimization Recommendations */}
            {analyticsData.optimization_recommendations.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-gray-900 mb-2 flex items-center">
                  <TrendingUp className="w-4 h-4 mr-2 text-green-600" />
                  Optimization Recommendations
                </h5>
                <ul className="space-y-1">
                  {analyticsData.optimization_recommendations.slice(0, 3).map((rec, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start">
                      <span className="w-1 h-1 bg-green-400 rounded-full mt-2 mr-2 flex-shrink-0" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Risk Warnings */}
            {analyticsData.risk_warnings.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-gray-900 mb-2 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2 text-red-600" />
                  Risk Warnings
                </h5>
                <ul className="space-y-1">
                  {analyticsData.risk_warnings.slice(0, 3).map((warning, index) => (
                    <li key={index} className="text-sm text-red-700 flex items-start">
                      <span className="w-1 h-1 bg-red-400 rounded-full mt-2 mr-2 flex-shrink-0" />
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Footer */}
      <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Last updated: {lastUpdated.toLocaleTimeString()}
          </span>
          <span>
            Generated at: {new Date(analyticsData.generated_at).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
};

export default GoalAnalytics;