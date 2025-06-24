/**
 * Fund Distribution Form Component
 * Phase 9: Performance-based capital allocation with AI recommendations
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  Brain,
  AlertTriangle,
  CheckCircle,
  Info,
  Zap,
  BarChart3,
  PieChart,
  RefreshCw,
  Save,
  X,
  Plus,
  Minus,
  Calculator,
  Shield,
  Clock
} from 'lucide-react';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';

interface AllocationTarget {
  target_id: string;
  target_name: string;
  target_type: 'wallet' | 'agent' | 'farm' | 'goal';
  current_allocation: number;
  recommended_allocation: number;
  performance_score: number;
  risk_score: number;
  reason: string;
  confidence: number;
}

interface AllocationRecommendation {
  wallet_id: string;
  recommendations: AllocationTarget[];
  market_analysis: {
    market_sentiment: string;
    volatility_level: string;
    recommended_total_allocation: number;
    cash_reserve_percentage: number;
  };
  current_allocation_efficiency: number;
  generated_at: string;
}

interface FundDistributionData {
  allocations: Array<{
    target_id: string;
    target_name: string;
    target_type: string;
    amount: number;
    percentage: number;
  }>;
  total_amount: number;
  available_balance: number;
  allocation_efficiency: number;
}

interface FundDistributionFormProps {
  walletId: string;
  availableBalance: number;
  currentAllocations?: FundDistributionData;
  onSubmit?: (allocations: FundDistributionData) => void;
  onCancel?: () => void;
  className?: string;
}

const ALLOCATION_PRESETS = [
  {
    id: 'conservative',
    name: 'Conservative',
    description: 'Low risk, stable returns',
    icon: Shield,
    color: 'bg-green-100 text-green-600',
    allocation_percentage: 60,
    cash_reserve: 40
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Moderate risk and return',
    icon: BarChart3,
    color: 'bg-blue-100 text-blue-600',
    allocation_percentage: 75,
    cash_reserve: 25
  },
  {
    id: 'aggressive',
    name: 'Aggressive',
    description: 'Higher risk, higher potential',
    icon: TrendingUp,
    color: 'bg-red-100 text-red-600',
    allocation_percentage: 90,
    cash_reserve: 10
  },
  {
    id: 'ai_optimized',
    name: 'AI Optimized',
    description: 'ML-powered allocation',
    icon: Brain,
    color: 'bg-purple-100 text-purple-600',
    allocation_percentage: 85,
    cash_reserve: 15
  }
];

export const FundDistributionForm: React.FC<FundDistributionFormProps> = ({
  walletId,
  availableBalance,
  currentAllocations,
  onSubmit,
  onCancel,
  className = ''
}) => {
  const [recommendations, setRecommendations] = useState<AllocationRecommendation | null>(null);
  const [customAllocations, setCustomAllocations] = useState<Array<{
    target_id: string;
    target_name: string;
    target_type: string;
    amount: number;
    percentage: number;
    performance_score: number;
    risk_score: number;
  }>>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('balanced');
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  const [totalAllocation, setTotalAllocation] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [riskTolerance, setRiskTolerance] = useState(5); // 1-10 scale
  const [rebalanceFrequency, setRebalanceFrequency] = useState('weekly');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Subscribe to allocation events
  useEffect(() => {
    const subscriptions = [
      subscribe('allocation.recommendations_generated', (data) => {
        if (data.wallet_id === walletId) {
          console.log('🎯 Allocation recommendations received:', data);
          setRecommendations(data);
          setIsLoadingRecommendations(false);
        }
      }),

      subscribe('allocation.rebalance_completed', (data) => {
        if (data.wallet_id === walletId) {
          console.log('⚖️ Rebalance completed:', data);
          loadRecommendations();
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
  }, [walletId]);

  // Load recommendations on mount
  useEffect(() => {
    loadRecommendations();
  }, [walletId]);

  // Load allocation recommendations
  const loadRecommendations = async () => {
    setIsLoadingRecommendations(true);
    
    emit('allocation.get_recommendations', {
      wallet_id: walletId,
      risk_tolerance: riskTolerance,
      include_market_analysis: true
    });
  };

  // Initialize custom allocations from recommendations
  useEffect(() => {
    if (recommendations && customAllocations.length === 0) {
      const initialAllocations = recommendations.recommendations.map(rec => ({
        target_id: rec.target_id,
        target_name: rec.target_name,
        target_type: rec.target_type,
        amount: rec.recommended_allocation,
        percentage: (rec.recommended_allocation / availableBalance) * 100,
        performance_score: rec.performance_score,
        risk_score: rec.risk_score
      }));
      
      setCustomAllocations(initialAllocations);
    }
  }, [recommendations, availableBalance]);

  // Calculate total allocation
  useEffect(() => {
    const total = customAllocations.reduce((sum, alloc) => sum + alloc.amount, 0);
    setTotalAllocation(total);
  }, [customAllocations]);

  // Handle preset selection
  const handlePresetSelect = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = ALLOCATION_PRESETS.find(p => p.id === presetId);
    
    if (preset && recommendations) {
      const targetAllocation = availableBalance * (preset.allocation_percentage / 100);
      const allocations = recommendations.recommendations.map(rec => {
        const weight = rec.performance_score / 100; // Normalize performance score
        const amount = targetAllocation * weight * (rec.confidence || 0.8);
        
        return {
          target_id: rec.target_id,
          target_name: rec.target_name,
          target_type: rec.target_type,
          amount: Math.min(amount, rec.recommended_allocation * 1.2), // Cap at 120% of recommendation
          percentage: (amount / availableBalance) * 100,
          performance_score: rec.performance_score,
          risk_score: rec.risk_score
        };
      });
      
      setCustomAllocations(allocations);
    }
  };

  // Handle allocation amount change
  const handleAllocationChange = (index: number, amount: number) => {
    const newAllocations = [...customAllocations];
    newAllocations[index].amount = amount;
    newAllocations[index].percentage = (amount / availableBalance) * 100;
    setCustomAllocations(newAllocations);
    
    // Clear any errors for this allocation
    const newErrors = { ...errors };
    delete newErrors[`allocation_${index}`];
    setErrors(newErrors);
  };

  // Add custom allocation
  const addCustomAllocation = () => {
    setCustomAllocations([
      ...customAllocations,
      {
        target_id: '',
        target_name: '',
        target_type: 'wallet',
        amount: 0,
        percentage: 0,
        performance_score: 50,
        risk_score: 50
      }
    ]);
  };

  // Remove allocation
  const removeAllocation = (index: number) => {
    const newAllocations = customAllocations.filter((_, i) => i !== index);
    setCustomAllocations(newAllocations);
  };

  // Validate allocations
  const validateAllocations = () => {
    const newErrors: Record<string, string> = {};
    
    // Check total allocation doesn't exceed available balance
    if (totalAllocation > availableBalance) {
      newErrors.total = 'Total allocation exceeds available balance';
    }
    
    // Check individual allocations
    customAllocations.forEach((alloc, index) => {
      if (alloc.amount <= 0) {
        newErrors[`allocation_${index}`] = 'Amount must be greater than 0';
      }
      
      if (!alloc.target_name.trim()) {
        newErrors[`allocation_${index}_name`] = 'Target name is required';
      }
      
      if (alloc.amount > availableBalance * 0.5) {
        newErrors[`allocation_${index}_max`] = 'Single allocation cannot exceed 50% of balance';
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = () => {
    if (!validateAllocations()) {
      return;
    }
    
    const distributionData: FundDistributionData = {
      allocations: customAllocations.map(alloc => ({
        target_id: alloc.target_id || `custom_${Date.now()}`,
        target_name: alloc.target_name,
        target_type: alloc.target_type,
        amount: alloc.amount,
        percentage: alloc.percentage
      })),
      total_amount: totalAllocation,
      available_balance: availableBalance,
      allocation_efficiency: (totalAllocation / availableBalance) * 100
    };
    
    if (onSubmit) {
      onSubmit(distributionData);
    }
    
    // Emit allocation event
    emit('allocation.update_distribution', {
      wallet_id: walletId,
      allocations: distributionData.allocations,
      rebalance_frequency: rebalanceFrequency,
      risk_tolerance: riskTolerance
    });
  };

  // Get allocation efficiency color
  const getEfficiencyColor = (efficiency: number) => {
    if (efficiency >= 80) return 'text-green-600 bg-green-100';
    if (efficiency >= 60) return 'text-blue-600 bg-blue-100';
    if (efficiency >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const allocationEfficiency = (totalAllocation / availableBalance) * 100;

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <PieChart className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Fund Distribution</h3>
              <p className="text-sm text-gray-600">
                Allocate ${availableBalance.toLocaleString()} across targets
              </p>
            </div>
          </div>

          <button
            onClick={loadRecommendations}
            disabled={isLoadingRecommendations}
            className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
          >
            <Brain className={`w-4 h-4 mr-1 inline ${isLoadingRecommendations ? 'animate-pulse' : ''}`} />
            AI Recommendations
          </button>
        </div>
      </div>

      {/* Allocation Summary */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="grid grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              ${totalAllocation.toLocaleString()}
            </div>
            <p className="text-sm text-gray-600">Total Allocated</p>
          </div>

          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              ${(availableBalance - totalAllocation).toLocaleString()}
            </div>
            <p className="text-sm text-gray-600">Cash Reserve</p>
          </div>

          <div className="text-center">
            <div className={`text-2xl font-bold px-3 py-1 rounded-lg ${getEfficiencyColor(allocationEfficiency)}`}>
              {allocationEfficiency.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-600">Efficiency</p>
          </div>
        </div>

        {errors.total && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <AlertTriangle className="w-4 h-4 text-red-600 mr-2" />
              <span className="text-sm text-red-700">{errors.total}</span>
            </div>
          </div>
        )}
      </div>

      {/* Preset Strategies */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h4 className="text-md font-medium text-gray-900 mb-3">Allocation Strategies</h4>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {ALLOCATION_PRESETS.map((preset) => {
            const Icon = preset.icon;
            return (
              <button
                key={preset.id}
                onClick={() => handlePresetSelect(preset.id)}
                className={`p-3 border-2 rounded-lg transition-all ${
                  selectedPreset === preset.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className={`w-8 h-8 ${preset.color} rounded-lg flex items-center justify-center mx-auto mb-2`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="text-sm font-medium text-gray-900">{preset.name}</div>
                <div className="text-xs text-gray-600">{preset.allocation_percentage}% allocated</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Market Analysis */}
      {recommendations?.market_analysis && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h4 className="text-md font-medium text-gray-900 mb-3">Market Analysis</h4>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">Sentiment</div>
              <div className={`text-md font-medium capitalize ${
                recommendations.market_analysis.market_sentiment === 'bullish' ? 'text-green-600' :
                recommendations.market_analysis.market_sentiment === 'bearish' ? 'text-red-600' : 'text-gray-600'
              }`}>
                {recommendations.market_analysis.market_sentiment}
              </div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">Volatility</div>
              <div className="text-md font-medium capitalize">{recommendations.market_analysis.volatility_level}</div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">Recommended</div>
              <div className="text-md font-medium">{recommendations.market_analysis.recommended_total_allocation}%</div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">Cash Reserve</div>
              <div className="text-md font-medium">{recommendations.market_analysis.cash_reserve_percentage}%</div>
            </div>
          </div>
        </div>
      )}

      {/* Custom Allocations */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-md font-medium text-gray-900">Allocation Details</h4>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="px-3 py-1 text-sm text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
            >
              Advanced
            </button>
            
            <button
              onClick={addCustomAllocation}
              className="px-3 py-1 text-sm text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
            >
              <Plus className="w-3 h-3 mr-1 inline" />
              Add Target
            </button>
          </div>
        </div>

        <div className="space-y-4">
          {customAllocations.map((allocation, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-4 border border-gray-200 rounded-lg"
            >
              <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Target Name
                  </label>
                  <input
                    type="text"
                    value={allocation.target_name}
                    onChange={(e) => {
                      const newAllocations = [...customAllocations];
                      newAllocations[index].target_name = e.target.value;
                      setCustomAllocations(newAllocations);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., High Performance Wallet"
                  />
                  {errors[`allocation_${index}_name`] && (
                    <p className="text-xs text-red-600 mt-1">{errors[`allocation_${index}_name`]}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type
                  </label>
                  <select
                    value={allocation.target_type}
                    onChange={(e) => {
                      const newAllocations = [...customAllocations];
                      newAllocations[index].target_type = e.target.value;
                      setCustomAllocations(newAllocations);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="wallet">Wallet</option>
                    <option value="agent">Agent</option>
                    <option value="farm">Farm</option>
                    <option value="goal">Goal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Amount ($)
                  </label>
                  <input
                    type="number"
                    value={allocation.amount}
                    onChange={(e) => handleAllocationChange(index, Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="0"
                    max={availableBalance}
                  />
                  {errors[`allocation_${index}`] && (
                    <p className="text-xs text-red-600 mt-1">{errors[`allocation_${index}`]}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Percentage
                  </label>
                  <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-sm text-gray-700">
                    {allocation.percentage.toFixed(2)}%
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {showAdvanced && (
                    <div className="flex items-center space-x-1 text-xs text-gray-600">
                      <span>P:{allocation.performance_score.toFixed(0)}</span>
                      <span>R:{allocation.risk_score.toFixed(0)}</span>
                    </div>
                  )}
                  
                  <button
                    onClick={() => removeAllocation(index)}
                    className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {customAllocations.length === 0 && (
          <div className="text-center py-8">
            <PieChart className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">No allocations configured</p>
            <button
              onClick={addCustomAllocation}
              className="mt-3 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            >
              Add First Allocation
            </button>
          </div>
        )}
      </div>

      {/* Advanced Settings */}
      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 border-t border-gray-200 bg-gray-50"
          >
            <h4 className="text-md font-medium text-gray-900 mb-3">Advanced Settings</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Risk Tolerance (1-10)
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={riskTolerance}
                  onChange={(e) => setRiskTolerance(Number(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                  <span>Conservative</span>
                  <span className="font-medium">{riskTolerance}</span>
                  <span>Aggressive</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Rebalance Frequency
                </label>
                <select
                  value={rebalanceFrequency}
                  onChange={(e) => setRebalanceFrequency(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="manual">Manual Only</option>
                </select>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Actions */}
      <div className="px-6 py-4 border-t border-gray-200">
        <div className="flex items-center justify-end space-x-3">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          )}
          
          <button
            onClick={handleSubmit}
            disabled={customAllocations.length === 0 || Object.keys(errors).length > 0}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4 mr-2 inline" />
            Apply Distribution
          </button>
        </div>
      </div>
    </div>
  );
};

export default FundDistributionForm;