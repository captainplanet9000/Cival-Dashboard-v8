/**
 * Goal Completion Modal Component
 * Phase 8: Completion validation with celebration and insights
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle,
  Target,
  TrendingUp,
  Clock,
  DollarSign,
  Star,
  Trophy,
  Sparkles,
  Share2,
  Download,
  X,
  Brain,
  Lightbulb,
  Calendar,
  Award
} from 'lucide-react';
import { format, differenceInDays } from 'date-fns';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';
import { GoalData, CompletionPrediction } from '../../ag-ui-setup/ag-ui-config';

interface GoalCompletionModalProps {
  goal: GoalData;
  isOpen: boolean;
  onClose: () => void;
  onCreateNewGoal?: () => void;
  onShareCompletion?: (goal: GoalData) => void;
}

interface CompletionInsights {
  efficiency_score: number;
  performance_rating: 'excellent' | 'good' | 'average' | 'below_average';
  timeline_performance: 'early' | 'on_time' | 'late';
  key_success_factors: string[];
  lessons_learned: string[];
  next_goal_suggestions: string[];
}

const PERFORMANCE_COLORS = {
  excellent: 'text-green-600 bg-green-100',
  good: 'text-blue-600 bg-blue-100',
  average: 'text-yellow-600 bg-yellow-100',
  below_average: 'text-red-600 bg-red-100'
};

const ACHIEVEMENT_BADGES = [
  { 
    id: 'first_goal', 
    name: 'First Goal', 
    icon: Target, 
    description: 'Completed your first goal',
    color: 'text-blue-600 bg-blue-100'
  },
  { 
    id: 'speed_demon', 
    name: 'Speed Demon', 
    icon: Clock, 
    description: 'Completed ahead of schedule',
    color: 'text-purple-600 bg-purple-100'
  },
  { 
    id: 'overachiever', 
    name: 'Overachiever', 
    icon: TrendingUp, 
    description: 'Exceeded target value',
    color: 'text-green-600 bg-green-100'
  },
  { 
    id: 'consistent', 
    name: 'Consistent', 
    icon: Award, 
    description: 'Completed 5 goals in a row',
    color: 'text-orange-600 bg-orange-100'
  },
  { 
    id: 'high_value', 
    name: 'High Value', 
    icon: DollarSign, 
    description: 'Completed a $10k+ goal',
    color: 'text-yellow-600 bg-yellow-100'
  }
];

export const GoalCompletionModal: React.FC<GoalCompletionModalProps> = ({
  goal,
  isOpen,
  onClose,
  onCreateNewGoal,
  onShareCompletion
}) => {
  const [completionInsights, setCompletionInsights] = useState<CompletionInsights | null>(null);
  const [achievedBadges, setAchievedBadges] = useState<string[]>([]);
  const [showCelebration, setShowCelebration] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  
  // Calculate completion metrics
  const completionMetrics = React.useMemo(() => {
    const createdAt = new Date(goal.created_at);
    const completedAt = goal.actual_completion ? new Date(goal.actual_completion) : new Date();
    const estimatedCompletion = goal.estimated_completion ? new Date(goal.estimated_completion) : null;
    
    const actualDuration = differenceInDays(completedAt, createdAt);
    const estimatedDuration = estimatedCompletion ? differenceInDays(estimatedCompletion, createdAt) : actualDuration;
    
    const timelinePerformance = estimatedCompletion 
      ? completedAt <= estimatedCompletion 
        ? completedAt < estimatedCompletion ? 'early' : 'on_time'
        : 'late'
      : 'on_time';
    
    const valueAchievement = goal.target_value > 0 ? (goal.current_value / goal.target_value) * 100 : 100;
    const timelineEfficiency = estimatedDuration > 0 ? (estimatedDuration / actualDuration) * 100 : 100;
    
    return {
      actualDuration,
      estimatedDuration,
      timelinePerformance,
      valueAchievement,
      timelineEfficiency,
      completedAt,
      createdAt
    };
  }, [goal]);
  
  // Subscribe to completion insights
  useEffect(() => {
    if (isOpen && goal.status === 'completed') {
      const subscriptions = [
        subscribe('goal.completion_insights', (data) => {
          if (data.goal_id === goal.goal_id) {
            console.log('🎯 Completion insights received:', data);
            setCompletionInsights(data.insights);
          }
        }),
        
        subscribe('goal.achievement_badges', (data) => {
          if (data.goal_id === goal.goal_id) {
            console.log('🏆 Achievement badges received:', data);
            setAchievedBadges(data.badges);
          }
        })
      ];
      
      // Request completion insights
      emit('goal.request_completion_insights', {
        goal_id: goal.goal_id,
        include_badges: true,
        include_suggestions: true
      });
      
      return () => {
        subscriptions.forEach(subscriptionId => {
          if (subscriptionId) {
            unsubscribe(subscriptionId);
          }
        });
      };
    }
  }, [isOpen, goal.goal_id, goal.status]);
  
  // Handle celebration animation
  useEffect(() => {
    if (isOpen) {
      setShowCelebration(true);
      const timer = setTimeout(() => setShowCelebration(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);
  
  // Generate completion report
  const handleGenerateReport = async () => {
    setIsGeneratingReport(true);
    
    try {
      emit('goal.generate_completion_report', {
        goal_id: goal.goal_id,
        format: 'pdf',
        include_insights: true,
        include_charts: true
      });
      
      // In a real implementation, this would trigger a download
      setTimeout(() => {
        setIsGeneratingReport(false);
        alert('Completion report generated! Check your downloads folder.');
      }, 2000);
      
    } catch (error) {
      console.error('Failed to generate report:', error);
      setIsGeneratingReport(false);
    }
  };
  
  // Handle share completion
  const handleShare = () => {
    if (onShareCompletion) {
      onShareCompletion(goal);
    } else {
      // Default share behavior
      const shareText = `🎯 Just completed my trading goal: "${goal.parsed_objective}"!\n\n` +
        `💰 Target: $${goal.target_value.toLocaleString()}\n` +
        `✅ Achieved: $${goal.current_value.toLocaleString()}\n` +
        `📈 Progress: ${goal.progress_percentage.toFixed(1)}%\n` +
        `⏱️ Duration: ${completionMetrics.actualDuration} days\n\n` +
        `#TradingGoals #Success #Achievement`;
      
      if (navigator.share) {
        navigator.share({
          title: 'Goal Completed!',
          text: shareText
        });
      } else {
        navigator.clipboard.writeText(shareText);
        alert('Achievement details copied to clipboard!');
      }
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        >
          {/* Celebration Overlay */}
          <AnimatePresence>
            {showCelebration && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-gradient-to-r from-yellow-400 via-pink-500 to-purple-600 opacity-10 pointer-events-none z-10"
              >
                <div className="absolute inset-0 overflow-hidden">
                  {[...Array(20)].map((_, i) => (
                    <motion.div
                      key={i}
                      initial={{ y: -20, opacity: 0, rotate: 0 }}
                      animate={{ 
                        y: window.innerHeight + 100, 
                        opacity: [0, 1, 0], 
                        rotate: 360 
                      }}
                      transition={{ 
                        duration: 3, 
                        delay: i * 0.1,
                        ease: "easeOut"
                      }}
                      className="absolute"
                      style={{
                        left: `${Math.random() * 100}%`,
                        fontSize: '24px'
                      }}
                    >
                      {['🎉', '✨', '🎊', '🏆', '⭐'][i % 5]}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          {/* Header */}
          <div className="relative p-6 border-b border-gray-200 bg-gradient-to-r from-green-50 to-blue-50">
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 transition-colors z-20"
            >
              <X className="w-5 h-5" />
            </button>
            
            <div className="text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: "spring" }}
                className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4"
              >
                <Trophy className="w-8 h-8 text-green-600" />
              </motion.div>
              
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-2xl font-bold text-gray-900 mb-2"
              >
                🎉 Goal Completed!
              </motion.h2>
              
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-gray-600"
              >
                Congratulations on achieving your trading goal!
              </motion.p>
            </div>
          </div>
          
          {/* Goal Details */}
          <div className="p-6 border-b border-gray-200">
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <p className="text-lg font-medium text-gray-900 mb-2">
                {goal.parsed_objective}
              </p>
              {goal.original_text !== goal.parsed_objective && (
                <p className="text-sm text-gray-600 italic">
                  Original: "{goal.original_text}"
                </p>
              )}
            </div>
            
            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <DollarSign className="w-6 h-6 text-green-600 mx-auto mb-1" />
                <div className="text-lg font-bold text-green-900">
                  ${goal.current_value.toLocaleString()}
                </div>
                <div className="text-xs text-green-700">Achieved</div>
                <div className="text-xs text-gray-500">
                  Target: ${goal.target_value.toLocaleString()}
                </div>
              </div>
              
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <TrendingUp className="w-6 h-6 text-blue-600 mx-auto mb-1" />
                <div className="text-lg font-bold text-blue-900">
                  {completionMetrics.valueAchievement.toFixed(1)}%
                </div>
                <div className="text-xs text-blue-700">Achievement</div>
              </div>
              
              <div className="text-center p-3 bg-purple-50 rounded-lg">
                <Clock className="w-6 h-6 text-purple-600 mx-auto mb-1" />
                <div className="text-lg font-bold text-purple-900">
                  {completionMetrics.actualDuration}
                </div>
                <div className="text-xs text-purple-700">Days</div>
                <div className="text-xs text-gray-500">
                  Est: {completionMetrics.estimatedDuration}
                </div>
              </div>
              
              <div className="text-center p-3 bg-yellow-50 rounded-lg">
                <Star className="w-6 h-6 text-yellow-600 mx-auto mb-1" />
                <div className="text-lg font-bold text-yellow-900">
                  {completionMetrics.timelineEfficiency.toFixed(0)}%
                </div>
                <div className="text-xs text-yellow-700">Efficiency</div>
              </div>
            </div>
          </div>
          
          {/* Achievement Badges */}
          {achievedBadges.length > 0 && (
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <Award className="w-5 h-5 mr-2 text-yellow-600" />
                Achievement Badges
              </h3>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {ACHIEVEMENT_BADGES
                  .filter(badge => achievedBadges.includes(badge.id))
                  .map((badge) => {
                    const Icon = badge.icon;
                    return (
                      <motion.div
                        key={badge.id}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.1 }}
                        className={`p-3 rounded-lg border-2 ${badge.color} border-current`}
                      >
                        <Icon className="w-6 h-6 mx-auto mb-1" />
                        <div className="text-sm font-medium text-center">
                          {badge.name}
                        </div>
                        <div className="text-xs text-center opacity-75">
                          {badge.description}
                        </div>
                      </motion.div>
                    );
                  })}
              </div>
            </div>
          )}
          
          {/* Completion Insights */}
          {completionInsights && (
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <Brain className="w-5 h-5 mr-2 text-blue-600" />
                AI Insights
              </h3>
              
              <div className="space-y-4">
                {/* Performance Rating */}
                <div className={`p-3 rounded-lg ${PERFORMANCE_COLORS[completionInsights.performance_rating]}`}>
                  <div className="font-medium capitalize">
                    {completionInsights.performance_rating.replace('_', ' ')} Performance
                  </div>
                  <div className="text-sm">
                    Efficiency Score: {completionInsights.efficiency_score.toFixed(1)}/10
                  </div>
                </div>
                
                {/* Key Success Factors */}
                {completionInsights.key_success_factors.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center">
                      <CheckCircle className="w-4 h-4 mr-1 text-green-600" />
                      Key Success Factors
                    </h4>
                    <ul className="space-y-1">
                      {completionInsights.key_success_factors.map((factor, index) => (
                        <li key={index} className="text-sm text-gray-700 flex items-start">
                          <span className="w-1 h-1 bg-green-400 rounded-full mt-2 mr-2 flex-shrink-0" />
                          {factor}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Lessons Learned */}
                {completionInsights.lessons_learned.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center">
                      <Lightbulb className="w-4 h-4 mr-1 text-yellow-600" />
                      Lessons Learned
                    </h4>
                    <ul className="space-y-1">
                      {completionInsights.lessons_learned.map((lesson, index) => (
                        <li key={index} className="text-sm text-gray-700 flex items-start">
                          <span className="w-1 h-1 bg-yellow-400 rounded-full mt-2 mr-2 flex-shrink-0" />
                          {lesson}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Next Goal Suggestions */}
                {completionInsights.next_goal_suggestions.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center">
                      <Target className="w-4 h-4 mr-1 text-blue-600" />
                      Suggested Next Goals
                    </h4>
                    <ul className="space-y-1">
                      {completionInsights.next_goal_suggestions.map((suggestion, index) => (
                        <li key={index} className="text-sm text-gray-700 flex items-start">
                          <span className="w-1 h-1 bg-blue-400 rounded-full mt-2 mr-2 flex-shrink-0" />
                          {suggestion}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Timeline */}
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <Calendar className="w-5 h-5 mr-2 text-gray-600" />
              Goal Timeline
            </h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-600">Created</span>
                <span className="text-sm font-medium">
                  {format(completionMetrics.createdAt, 'MMM dd, yyyy')}
                </span>
              </div>
              
              {goal.actual_start && (
                <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                  <span className="text-sm text-blue-600">Started</span>
                  <span className="text-sm font-medium text-blue-900">
                    {format(new Date(goal.actual_start), 'MMM dd, yyyy')}
                  </span>
                </div>
              )}
              
              <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                <span className="text-sm text-green-600">Completed</span>
                <span className="text-sm font-medium text-green-900">
                  {format(completionMetrics.completedAt, 'MMM dd, yyyy')}
                </span>
              </div>
              
              <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-600">Duration</span>
                <span className="text-sm font-medium">
                  {completionMetrics.actualDuration} days
                  <span className={`ml-2 text-xs px-2 py-1 rounded-full ${
                    completionMetrics.timelinePerformance === 'early' ? 'bg-green-100 text-green-800' :
                    completionMetrics.timelinePerformance === 'on_time' ? 'bg-blue-100 text-blue-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {completionMetrics.timelinePerformance === 'early' ? 'Early' :
                     completionMetrics.timelinePerformance === 'on_time' ? 'On Time' : 'Late'}
                  </span>
                </span>
              </div>
            </div>
          </div>
          
          {/* Actions */}
          <div className="p-6">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleShare}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share Achievement
              </button>
              
              <button
                onClick={handleGenerateReport}
                disabled={isGeneratingReport}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                {isGeneratingReport ? (
                  <>
                    <div className="w-4 h-4 mr-2 animate-spin border-2 border-white border-t-transparent rounded-full" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Download Report
                  </>
                )}
              </button>
              
              {onCreateNewGoal && (
                <button
                  onClick={onCreateNewGoal}
                  className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                  <Target className="w-4 h-4 mr-2" />
                  Create New Goal
                </button>
              )}
              
              <button
                onClick={onClose}
                className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default GoalCompletionModal;