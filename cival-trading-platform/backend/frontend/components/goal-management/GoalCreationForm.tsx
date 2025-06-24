/**
 * Goal Creation Form Component
 * Phase 8: Natural language goal input with AG-UI integration
 */

import React, { useState, useRef, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Target, 
  Calendar, 
  DollarSign, 
  TrendingUp, 
  AlertTriangle, 
  Sparkles,
  Clock,
  Send,
  Loader2,
  CheckCircle,
  XCircle,
  Lightbulb
} from 'lucide-react';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';
import { GoalData, RiskAssessment } from '../../ag-ui-setup/ag-ui-config';

// Form validation schema
const goalCreationSchema = z.object({
  goalText: z.string()
    .min(10, 'Goal description must be at least 10 characters')
    .max(500, 'Goal description must be less than 500 characters'),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  deadline: z.string().optional(),
  walletId: z.string().optional(),
  allocationId: z.string().optional(),
  tags: z.array(z.string()).optional()
});

type GoalCreationFormData = z.infer<typeof goalCreationSchema>;

// Suggested goal templates
const GOAL_TEMPLATES = [
  {
    id: 'profit_target',
    label: 'Profit Target',
    icon: DollarSign,
    template: 'Make ${{amount}} profit in {{timeframe}}',
    suggestions: ['$1000 in 30 days', '$5000 in 3 months', '$500 this week']
  },
  {
    id: 'roi_target',
    label: 'ROI Target',
    icon: TrendingUp,
    template: 'Achieve {{percentage}}% ROI in {{timeframe}}',
    suggestions: ['20% ROI in 60 days', '15% ROI this month', '30% ROI in 6 months']
  },
  {
    id: 'risk_limit',
    label: 'Risk Control',
    icon: AlertTriangle,
    template: 'Limit {{risk_type}} to {{percentage}}%',
    suggestions: ['limit risk to 10%', 'keep drawdown under 15%', 'maintain 85% win rate']
  },
  {
    id: 'time_target',
    label: 'Time-based',
    icon: Clock,
    template: 'Complete {{objective}} by {{date}}',
    suggestions: ['reach break-even by month end', 'double account by year end', 'achieve consistency in 90 days']
  }
];

interface GoalCreationFormProps {
  onGoalCreated?: (goal: GoalData) => void;
  onCancel?: () => void;
  defaultWalletId?: string;
  defaultAllocationId?: string;
  className?: string;
}

export const GoalCreationForm: React.FC<GoalCreationFormProps> = ({
  onGoalCreated,
  onCancel,
  defaultWalletId,
  defaultAllocationId,
  className = ''
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<{
    confidence: number;
    suggestions: string[];
    riskAssessment?: RiskAssessment;
  } | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  
  
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isValid }
  } = useForm<GoalCreationFormData>({
    resolver: zodResolver(goalCreationSchema),
    defaultValues: {
      priority: 'medium',
      walletId: defaultWalletId,
      allocationId: defaultAllocationId,
      tags: []
    },
    mode: 'onChange'
  });
  
  const goalText = watch('goalText');
  
  // Subscribe to AG-UI events
  useEffect(() => {
    const subscriptions = [
      subscribe('goal.created', (data) => {
        console.log('🎯 Goal created successfully:', data);
        setIsSubmitting(false);
        
        if (onGoalCreated && data.goal) {
          onGoalCreated(data.goal);
        }
        
        // Reset form
        reset();
        setAnalysisResult(null);
      }),
      
      subscribe('goal.analyzed', (data) => {
        console.log('🧠 Goal analysis received:', data);
        
        if (data.goal && data.risk_assessment) {
          setAnalysisResult({
            confidence: data.parsing_confidence || 0.8,
            suggestions: data.optimization_suggestions || [],
            riskAssessment: data.risk_assessment
          });
        }
      }),
      
      subscribe('system.error', (data) => {
        if (data.service === 'intelligent_goal_service') {
          console.error('❌ Goal service error:', data);
          setIsSubmitting(false);
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
  }, [onGoalCreated, reset]);
  
  // Auto-resize is handled in the textarea onChange event
  
  // Handle form submission
  const onSubmit = async (data: GoalCreationFormData) => {
    setIsSubmitting(true);
    
    try {
      // Emit goal creation event to backend
      emit('goal.create', {
        goalText: data.goalText,
        priority: data.priority,
        deadline: data.deadline,
        walletId: data.walletId,
        allocationId: data.allocationId,
        tags: data.tags || [],
        context: {
          source: 'goal_creation_form',
          timestamp: new Date().toISOString()
        }
      });
      
      console.log('📤 Goal creation request sent');
      
    } catch (error) {
      console.error('❌ Failed to create goal:', error);
      setIsSubmitting(false);
    }
  };
  
  // Handle template selection
  const handleTemplateSelect = (template: typeof GOAL_TEMPLATES[0], suggestion: string) => {
    setValue('goalText', suggestion);
    setSelectedTemplate(template.id);
    setShowTemplates(false);
    
    // Focus will be handled by the form library
  };
  
  // Handle template customization
  const handleTemplateCustomize = (template: typeof GOAL_TEMPLATES[0]) => {
    const placeholderText = template.template
      .replace('{{amount}}', '1000')
      .replace('{{percentage}}', '20')
      .replace('{{timeframe}}', '30 days')
      .replace('{{risk_type}}', 'drawdown')
      .replace('{{objective}}', 'profitability')
      .replace('{{date}}', 'end of month');
    
    setValue('goalText', placeholderText);
    setSelectedTemplate(template.id);
    setShowTemplates(false);
    
    // Focus will be handled by the form library
  };
  
  // Real-time goal analysis (debounced)
  useEffect(() => {
    if (!goalText || goalText.length < 20) {
      setAnalysisResult(null);
      return;
    }
    
    const debounceTimer = setTimeout(() => {
      // Request real-time analysis
      emit('goal.analyze_preview', {
        goalText,
        context: {
          walletId: watch('walletId'),
          allocationId: watch('allocationId')
        }
      });
    }, 1000);
    
    return () => clearTimeout(debounceTimer);
  }, [goalText, watch]);
  
  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Target className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Create New Goal</h3>
              <p className="text-sm text-gray-600">
                Describe your trading goal in natural language
              </p>
            </div>
          </div>
          
          <button
            type="button"
            onClick={() => setShowTemplates(!showTemplates)}
            className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <Sparkles className="w-4 h-4 inline mr-1" />
            Templates
          </button>
        </div>
      </div>
      
      {/* Template Suggestions */}
      <AnimatePresence>
        {showTemplates && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 bg-gray-50 border-b border-gray-200"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {GOAL_TEMPLATES.map((template) => {
                const Icon = template.icon;
                return (
                  <div key={template.id} className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Icon className="w-4 h-4 text-gray-600" />
                      <span className="text-sm font-medium text-gray-900">
                        {template.label}
                      </span>
                    </div>
                    
                    <div className="space-y-1">
                      {template.suggestions.map((suggestion, index) => (
                        <button
                          key={index}
                          type="button"
                          onClick={() => handleTemplateSelect(template, suggestion)}
                          className="block w-full text-left px-3 py-2 text-sm text-gray-700 bg-white rounded border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                        >
                          {suggestion}
                        </button>
                      ))}
                      
                      <button
                        type="button"
                        onClick={() => handleTemplateCustomize(template)}
                        className="block w-full text-left px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded border border-blue-200 hover:bg-blue-100 transition-colors"
                      >
                        <Lightbulb className="w-3 h-3 inline mr-1" />
                        Customize template...
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
        {/* Goal Description */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Goal Description
          </label>
          <div className="relative">
            <textarea
              {...register('goalText', {
                onChange: (e) => {
                  const textarea = e.target;
                  // Auto-resize
                  textarea.style.height = 'auto';
                  textarea.style.height = `${textarea.scrollHeight}px`;
                }
              })}
              placeholder="Describe your trading goal in natural language... (e.g., 'Make $1000 profit in the next 30 days using breakout strategies')"
              className={`w-full px-4 py-3 border rounded-lg resize-none transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.goalText 
                  ? 'border-red-300 focus:border-red-500' 
                  : selectedTemplate 
                  ? 'border-blue-300 focus:border-blue-500'
                  : 'border-gray-300 focus:border-blue-500'
              }`}
              rows={3}
              maxLength={500}
            />
            
            {goalText && (
              <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                {goalText.length}/500
              </div>
            )}
          </div>
          
          {errors.goalText && (
            <p className="text-sm text-red-600 flex items-center">
              <XCircle className="w-4 h-4 mr-1" />
              {errors.goalText.message}
            </p>
          )}
          
          {analysisResult && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-green-50 border border-green-200 rounded-lg"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-green-800">
                  AI Analysis Complete
                </span>
                <div className="flex items-center text-sm text-green-600">
                  <CheckCircle className="w-4 h-4 mr-1" />
                  {Math.round(analysisResult.confidence * 100)}% confidence
                </div>
              </div>
              
              {analysisResult.suggestions.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-green-700 font-medium">Suggestions:</p>
                  {analysisResult.suggestions.slice(0, 2).map((suggestion, index) => (
                    <p key={index} className="text-xs text-green-700">
                      • {suggestion}
                    </p>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </div>
        
        {/* Priority and Deadline */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Priority
            </label>
            <select
              {...register('priority')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="low">Low Priority</option>
              <option value="medium">Medium Priority</option>
              <option value="high">High Priority</option>
              <option value="critical">Critical Priority</option>
            </select>
          </div>
          
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Deadline (Optional)
            </label>
            <input
              type="date"
              {...register('deadline')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min={new Date().toISOString().split('T')[0]}
            />
          </div>
        </div>
        
        {/* Wallet and Allocation */}
        {(defaultWalletId || defaultAllocationId) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Wallet ID
              </label>
              <input
                type="text"
                {...register('walletId')}
                readOnly={!!defaultWalletId}
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  defaultWalletId ? 'bg-gray-50' : ''
                }`}
                placeholder="Optional: Link to specific wallet"
              />
            </div>
            
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Allocation ID
              </label>
              <input
                type="text"
                {...register('allocationId')}
                readOnly={!!defaultAllocationId}
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  defaultAllocationId ? 'bg-gray-50' : ''
                }`}
                placeholder="Optional: Link to specific allocation"
              />
            </div>
          </div>
        )}
        
        {/* Risk Assessment Display */}
        {analysisResult?.riskAssessment && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg"
          >
            <div className="flex items-center mb-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600 mr-2" />
              <span className="text-sm font-medium text-yellow-800">
                Risk Assessment
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-yellow-700 font-medium">Risk Score</p>
                <p className="text-yellow-600">
                  {analysisResult.riskAssessment.overall_risk_score}/10
                </p>
              </div>
              
              <div>
                <p className="text-yellow-700 font-medium">Category</p>
                <p className="text-yellow-600 capitalize">
                  {analysisResult.riskAssessment.risk_category}
                </p>
              </div>
              
              <div>
                <p className="text-yellow-700 font-medium">Loss Probability</p>
                <p className="text-yellow-600">
                  {Math.round(analysisResult.riskAssessment.probability_of_loss * 100)}%
                </p>
              </div>
            </div>
          </motion.div>
        )}
        
        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          )}
          
          <button
            type="submit"
            disabled={!isValid || isSubmitting}
            className={`px-6 py-2 text-sm font-medium text-white rounded-lg transition-colors flex items-center ${
              isValid && !isSubmitting
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-gray-400 cursor-not-allowed'
            }`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating Goal...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Create Goal
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default GoalCreationForm;