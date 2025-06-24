/**
 * Goal Progress Card Component
 * Phase 8: Real-time progress display with AG-UI integration
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  DollarSign,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Pause,
  MoreVertical,
  Activity,
  Brain,
  Zap,
  Calendar,
  BarChart3
} from 'lucide-react';
import { format, formatDistanceToNow, differenceInDays } from 'date-fns';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';
import { GoalData, RiskAssessment } from '../../ag-ui-setup/ag-ui-config';

interface GoalProgressCardProps {
  goal: GoalData;
  onGoalUpdate?: (goal: GoalData) => void;
  onGoalCancel?: (goalId: string) => void;
  className?: string;
  compact?: boolean;
}

const PRIORITY_COLORS = {
  low: 'bg-gray-100 text-gray-800 border-gray-200',
  medium: 'bg-blue-100 text-blue-800 border-blue-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  critical: 'bg-red-100 text-red-800 border-red-200'
};

const STATUS_COLORS = {
  pending: 'bg-gray-100 text-gray-800',
  analyzing: 'bg-purple-100 text-purple-800',
  in_progress: 'bg-blue-100 text-blue-800',
  paused: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
  optimizing: 'bg-indigo-100 text-indigo-800'
};

const STATUS_ICONS = {
  pending: Clock,
  analyzing: Brain,
  in_progress: Activity,
  paused: Pause,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: XCircle,
  optimizing: Zap
};

export const GoalProgressCard: React.FC<GoalProgressCardProps> = ({
  goal: initialGoal,
  onGoalUpdate,
  onGoalCancel,
  className = '',
  compact = false
}) => {
  const [goal, setGoal] = useState<GoalData>(initialGoal);
  const [showDetails, setShowDetails] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const [recentUpdates, setRecentUpdates] = useState<Array<{
    type: string;
    message: string;
    timestamp: string;
  }>>([]);
  
  // Subscribe to goal updates via AG-UI
  useEffect(() => {
    const subscriptions = [
      subscribe('goal.progress_updated', (data) => {
        if (data.goal && data.goal.goal_id === goal.goal_id) {
          console.log('📈 Goal progress updated:', data);
          
          const updatedGoal = data.goal;
          setGoal(updatedGoal);
          
          // Add update to recent updates
          setRecentUpdates(prev => [
            {
              type: 'progress',
              message: `Progress updated to ${updatedGoal.progress_percentage.toFixed(1)}%`,
              timestamp: new Date().toISOString()
            },
            ...prev.slice(0, 4) // Keep only last 5 updates
          ]);
          
          // Notify parent
          if (onGoalUpdate) {
            onGoalUpdate(updatedGoal);
          }
        }
      }),
      
      subscribe('goal.completed', (data) => {
        if (data.goal && data.goal.goal_id === goal.goal_id) {
          console.log('🎉 Goal completed:', data);
          
          const completedGoal = data.goal;
          setGoal(completedGoal);
          
          setRecentUpdates(prev => [
            {
              type: 'completion',
              message: `Goal completed! ${data.completion_insights?.join(', ') || ''}`,
              timestamp: new Date().toISOString()
            },
            ...prev.slice(0, 4)
          ]);
          
          if (onGoalUpdate) {
            onGoalUpdate(completedGoal);
          }
        }
      }),
      
      subscribe('goal.optimization_suggested', (data) => {
        if (data.goal && data.goal.goal_id === goal.goal_id) {
          console.log('🔧 Goal optimization suggested:', data);
          
          const optimizedGoal = data.goal;
          setGoal(optimizedGoal);
          
          setRecentUpdates(prev => [
            {
              type: 'optimization',
              message: `Optimization suggested: ${data.optimization_result?.recommended_actions?.[0] || 'Check details'}`,
              timestamp: new Date().toISOString()
            },
            ...prev.slice(0, 4)
          ]);
          
          if (onGoalUpdate) {
            onGoalUpdate(optimizedGoal);
          }
        }
      }),
      
      subscribe('goal.cancelled', (data) => {
        if (data.goal && data.goal.goal_id === goal.goal_id) {
          console.log('❌ Goal cancelled:', data);
          
          const cancelledGoal = data.goal;
          setGoal(cancelledGoal);
          
          setRecentUpdates(prev => [
            {
              type: 'cancellation',
              message: `Goal cancelled: ${data.reason || 'No reason provided'}`,
              timestamp: new Date().toISOString()
            },
            ...prev.slice(0, 4)
          ]);
          
          if (onGoalUpdate) {
            onGoalUpdate(cancelledGoal);
          }
        }
      })
    ];
    
    return () => {
      subscriptions.forEach(subscriptionId => {
        if (subscriptionId) {
          unsubscribe(subscriptionId);
        }
      });
    };
  }, [goal.goal_id, onGoalUpdate]);
  
  // Calculate time-related metrics
  const timeMetrics = React.useMemo(() => {
    const now = new Date();
    const createdAt = new Date(goal.created_at);
    const startedAt = goal.actual_start ? new Date(goal.actual_start) : null;
    const estimatedCompletion = goal.estimated_completion ? new Date(goal.estimated_completion) : null;
    const deadline = goal.deadline ? new Date(goal.deadline) : null;
    
    return {
      ageInDays: differenceInDays(now, createdAt),
      timeFromStart: startedAt ? formatDistanceToNow(startedAt, { addSuffix: true }) : null,
      timeToDeadline: deadline ? formatDistanceToNow(deadline, { addSuffix: true }) : null,
      timeToEstimated: estimatedCompletion ? formatDistanceToNow(estimatedCompletion, { addSuffix: true }) : null,
      isOverdue: deadline ? now > deadline : false,
      isAtRisk: estimatedCompletion && deadline ? estimatedCompletion > deadline : false
    };
  }, [goal]);
  
  // Calculate progress metrics
  const progressMetrics = React.useMemo(() => {
    const progressPercent = Math.min(100, Math.max(0, goal.progress_percentage));
    const isCompleted = goal.status === 'completed';
    const valueAchieved = goal.current_value;
    const valueTarget = goal.target_value;
    const valueRatio = valueTarget > 0 ? (valueAchieved / valueTarget) * 100 : 0;
    
    return {
      progressPercent,
      isCompleted,
      valueAchieved,
      valueTarget,
      valueRatio,
      progressColor: isCompleted 
        ? 'bg-green-500' 
        : progressPercent > 75 
        ? 'bg-blue-500' 
        : progressPercent > 50 
        ? 'bg-yellow-500' 
        : 'bg-gray-400'
    };
  }, [goal]);
  
  // Handle goal cancellation
  const handleCancelGoal = () => {
    if (window.confirm('Are you sure you want to cancel this goal?')) {
      emit('goal.cancel', {
        goal_id: goal.goal_id,
        reason: 'User requested cancellation'
      });
      
      if (onGoalCancel) {
        onGoalCancel(goal.goal_id);
      }
    }
  };
  
  // Get status icon
  const StatusIcon = STATUS_ICONS[goal.status as keyof typeof STATUS_ICONS] || Activity;
  
  if (compact) {
    return (
      <motion.div
        layout
        className={`bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow ${className}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${PRIORITY_COLORS[goal.priority as keyof typeof PRIORITY_COLORS]}`}>
              <Target className="w-4 h-4" />
            </div>
            
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">
                {goal.parsed_objective}
              </p>
              <div className="flex items-center space-x-2 mt-1">
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[goal.status as keyof typeof STATUS_COLORS]}`}>
                  <StatusIcon className="w-3 h-3 mr-1" />
                  {goal.status.replace('_', ' ')}
                </span>
                <span className="text-xs text-gray-500">
                  {progressMetrics.progressPercent.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className="w-16 bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${progressMetrics.progressColor}`}
                style={{ width: `${progressMetrics.progressPercent}%` }}
              />
            </div>
            
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>
    );
  }
  
  return (
    <motion.div
      layout
      className={`bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="p-6 pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className={`p-3 rounded-lg ${PRIORITY_COLORS[goal.priority as keyof typeof PRIORITY_COLORS]}`}>
              <Target className="w-6 h-6" />
            </div>
            
            <div className="min-w-0 flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {goal.parsed_objective}
              </h3>
              
              <div className="flex items-center flex-wrap gap-2 mb-3">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[goal.status as keyof typeof STATUS_COLORS]}`}>
                  <StatusIcon className="w-4 h-4 mr-1.5" />
                  {goal.status.replace('_', ' ')}
                </span>
                
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${PRIORITY_COLORS[goal.priority as keyof typeof PRIORITY_COLORS]}`}>
                  {goal.priority} priority
                </span>
                
                {timeMetrics.isOverdue && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                    <AlertTriangle className="w-4 h-4 mr-1.5" />
                    Overdue
                  </span>
                )}
              </div>
              
              {goal.original_text !== goal.parsed_objective && (
                <p className="text-sm text-gray-600 italic">
                  "{goal.original_text}"
                </p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowInsights(!showInsights)}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Show AI insights"
            >
              <Brain className="w-5 h-5" />
            </button>
            
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Progress Section */}
      <div className="px-6 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-4">
            <div className="flex items-center text-lg font-semibold text-gray-900">
              <DollarSign className="w-5 h-5 mr-1 text-green-600" />
              ${progressMetrics.valueAchieved.toLocaleString()}
              <span className="text-sm text-gray-500 ml-2">
                / ${progressMetrics.valueTarget.toLocaleString()}
              </span>
            </div>
            
            <div className="flex items-center text-sm text-gray-600">
              {progressMetrics.valueAchieved >= progressMetrics.valueTarget ? (
                <TrendingUp className="w-4 h-4 mr-1 text-green-500" />
              ) : (
                <TrendingUp className="w-4 h-4 mr-1 text-gray-400" />
              )}
              {progressMetrics.valueRatio.toFixed(1)}% achieved
            </div>
          </div>
          
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">
              {progressMetrics.progressPercent.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">
              progress
            </div>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
          <motion.div
            className={`h-3 rounded-full transition-all duration-500 ${progressMetrics.progressColor}`}
            initial={{ width: 0 }}
            animate={{ width: `${progressMetrics.progressPercent}%` }}
          />
        </div>
        
        {/* Time Information */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {timeMetrics.timeFromStart && (
            <div>
              <p className="text-gray-500">Started</p>
              <p className="font-medium text-gray-900">{timeMetrics.timeFromStart}</p>
            </div>
          )}
          
          {timeMetrics.timeToEstimated && (
            <div>
              <p className="text-gray-500">Est. completion</p>
              <p className="font-medium text-gray-900">{timeMetrics.timeToEstimated}</p>
            </div>
          )}
          
          {timeMetrics.timeToDeadline && (
            <div>
              <p className="text-gray-500">Deadline</p>
              <p className={`font-medium ${timeMetrics.isOverdue ? 'text-red-600' : 'text-gray-900'}`}>
                {timeMetrics.timeToDeadline}
              </p>
            </div>
          )}
          
          <div>
            <p className="text-gray-500">Age</p>
            <p className="font-medium text-gray-900">{timeMetrics.ageInDays} days</p>
          </div>
        </div>
      </div>
      
      {/* AI Insights */}
      <AnimatePresence>
        {showInsights && (goal.learning_insights.length > 0 || goal.optimization_suggestions.length > 0) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 bg-blue-50 border-t border-blue-100"
          >
            <div className="flex items-center mb-3">
              <Brain className="w-5 h-5 text-blue-600 mr-2" />
              <h4 className="text-sm font-medium text-blue-900">AI Insights</h4>
            </div>
            
            {goal.learning_insights.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium text-blue-800 mb-2">Learning Insights:</p>
                <ul className="space-y-1">
                  {goal.learning_insights.slice(0, 3).map((insight, index) => (
                    <li key={index} className="text-sm text-blue-700 flex items-start">
                      <span className="w-1 h-1 bg-blue-400 rounded-full mt-2 mr-2 flex-shrink-0" />
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {goal.optimization_suggestions.length > 0 && (
              <div>
                <p className="text-xs font-medium text-blue-800 mb-2">Optimization Suggestions:</p>
                <ul className="space-y-1">
                  {goal.optimization_suggestions.slice(0, 2).map((suggestion, index) => (
                    <li key={index} className="text-sm text-blue-700 flex items-start">
                      <Zap className="w-3 h-3 text-blue-500 mt-0.5 mr-2 flex-shrink-0" />
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Recent Updates */}
      <AnimatePresence>
        {showDetails && recentUpdates.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 bg-gray-50 border-t border-gray-100"
          >
            <div className="flex items-center mb-3">
              <Activity className="w-5 h-5 text-gray-600 mr-2" />
              <h4 className="text-sm font-medium text-gray-900">Recent Updates</h4>
            </div>
            
            <div className="space-y-2">
              {recentUpdates.map((update, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    update.type === 'completion' ? 'bg-green-400' :
                    update.type === 'optimization' ? 'bg-blue-400' :
                    update.type === 'progress' ? 'bg-yellow-400' :
                    'bg-gray-400'
                  }`} />
                  
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-700">{update.message}</p>
                    <p className="text-xs text-gray-500">
                      {formatDistanceToNow(new Date(update.timestamp), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Actions */}
      <AnimatePresence>
        {showDetails && goal.status === 'in_progress' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 bg-white border-t border-gray-100"
          >
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Goal ID: <code className="bg-gray-100 px-1 rounded">{goal.goal_id}</code>
              </div>
              
              <button
                onClick={handleCancelGoal}
                className="px-3 py-1 text-sm font-medium text-red-600 bg-red-50 rounded hover:bg-red-100 transition-colors"
              >
                Cancel Goal
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default GoalProgressCard;