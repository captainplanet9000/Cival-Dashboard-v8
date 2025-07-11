'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Bot,
  TrendingUp,
  Shield,
  Zap,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Info,
  Sliders,
  Target,
  BarChart3
} from 'lucide-react'
import { paperTradingEngine, TradingAgent, TradingStrategy, RiskLimits } from '@/lib/trading/real-paper-trading-engine'

interface AgentCreationConfig {
  name: string
  description: string
  strategy: {
    name: string
    type: TradingStrategy['type']
    parameters: Record<string, any>
    description: string
  }
  initialCapital: number
  riskLimits: RiskLimits
}

interface RealAgentCreationProps {
  onAgentCreated?: (agent: TradingAgent) => void
  className?: string
}

const STRATEGY_TEMPLATES = {
  momentum: {
    name: 'Momentum Trading',
    description: 'Follows price trends and momentum indicators',
    defaultParams: {
      threshold: 0.02,
      lookbackPeriod: 20,
      confirmationPeriod: 5,
      stopLoss: 0.05,
      takeProfit: 0.1
    },
    riskProfile: 'medium'
  },
  mean_reversion: {
    name: 'Mean Reversion',
    description: 'Trades against extreme price movements expecting reversion',
    defaultParams: {
      threshold: 0.03,
      oversoldLevel: 0.3,
      overboughtLevel: 0.7,
      holdingPeriod: 10,
      stopLoss: 0.04
    },
    riskProfile: 'low'
  },
  arbitrage: {
    name: 'Arbitrage Hunter',
    description: 'Exploits price differences and spreads',
    defaultParams: {
      minSpread: 0.005,
      maxHoldTime: 60,
      maxExposure: 0.1,
      feeThreshold: 0.001
    },
    riskProfile: 'low'
  },
  grid: {
    name: 'Grid Trading',
    description: 'Places buy/sell orders at regular intervals',
    defaultParams: {
      gridSize: 0.01,
      gridLevels: 10,
      baseOrderSize: 0.1,
      profitPercentage: 0.02
    },
    riskProfile: 'medium'
  },
  dca: {
    name: 'Dollar Cost Averaging',
    description: 'Regularly buys assets regardless of price',
    defaultParams: {
      interval: 3600, // 1 hour
      amount: 100,
      maxDeviation: 0.05,
      pauseOnProfit: false
    },
    riskProfile: 'low'
  },
  custom: {
    name: 'Custom Strategy',
    description: 'Define your own trading parameters',
    defaultParams: {},
    riskProfile: 'high'
  }
}

export function RealAgentCreation({ onAgentCreated, className }: RealAgentCreationProps) {
  const [step, setStep] = useState(1)
  const [isCreating, setIsCreating] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  
  const [config, setConfig] = useState<AgentCreationConfig>({
    name: '',
    description: '',
    strategy: {
      name: '',
      type: 'momentum',
      parameters: STRATEGY_TEMPLATES.momentum.defaultParams,
      description: STRATEGY_TEMPLATES.momentum.description
    },
    initialCapital: 10000,
    riskLimits: {
      maxPositionSize: 10, // 10% of portfolio per position
      maxDailyLoss: 500,   // $500 max daily loss
      maxDrawdown: 20,     // 20% max drawdown
      maxLeverage: 1,      // No leverage
      allowedSymbols: ['BTC/USD', 'ETH/USD', 'SOL/USD'],
      stopLossEnabled: true,
      takeProfitEnabled: true
    }
  })

  const validateStep = (stepNumber: number): boolean => {
    const newErrors: Record<string, string> = {}

    switch (stepNumber) {
      case 1:
        if (!config.name.trim()) {
          newErrors.name = 'Agent name is required'
        } else if (config.name.length < 3) {
          newErrors.name = 'Agent name must be at least 3 characters'
        }
        if (config.initialCapital < 1000) {
          newErrors.initialCapital = 'Minimum initial capital is $1,000'
        }
        break

      case 2:
        if (!config.strategy.name.trim()) {
          newErrors.strategyName = 'Strategy name is required'
        }
        if (config.strategy.type === 'custom' && Object.keys(config.strategy.parameters).length === 0) {
          newErrors.parameters = 'Custom strategy requires parameters'
        }
        break

      case 3:
        if (config.riskLimits.maxPositionSize < 1 || config.riskLimits.maxPositionSize > 50) {
          newErrors.maxPositionSize = 'Position size must be between 1% and 50%'
        }
        if (config.riskLimits.maxDailyLoss < 100) {
          newErrors.maxDailyLoss = 'Minimum daily loss limit is $100'
        }
        if (config.riskLimits.allowedSymbols.length === 0) {
          newErrors.allowedSymbols = 'At least one trading symbol must be selected'
        }
        break
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (validateStep(step)) {
      setStep(step + 1)
    }
  }

  const handleBack = () => {
    setStep(step - 1)
    setErrors({})
  }

  const handleStrategyChange = (strategyType: TradingStrategy['type']) => {
    const template = STRATEGY_TEMPLATES[strategyType]
    setConfig(prev => ({
      ...prev,
      strategy: {
        ...prev.strategy,
        type: strategyType,
        name: template.name,
        description: template.description,
        parameters: template.defaultParams
      }
    }))
  }

  const handleParameterChange = (key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      strategy: {
        ...prev.strategy,
        parameters: {
          ...prev.strategy.parameters,
          [key]: value
        }
      }
    }))
  }

  const handleSymbolToggle = (symbol: string) => {
    setConfig(prev => ({
      ...prev,
      riskLimits: {
        ...prev.riskLimits,
        allowedSymbols: prev.riskLimits.allowedSymbols.includes(symbol)
          ? prev.riskLimits.allowedSymbols.filter(s => s !== symbol)
          : [...prev.riskLimits.allowedSymbols, symbol]
      }
    }))
  }

  const createAgent = async () => {
    if (!validateStep(3)) return

    setIsCreating(true)
    try {
      // Start the trading engine if not already running
      if (!paperTradingEngine.listenerCount('pricesUpdated')) {
        paperTradingEngine.start()
      }

      const agent = paperTradingEngine.createAgent(config)
      
      onAgentCreated?.(agent)
      
      // Reset form
      setConfig({
        name: '',
        description: '',
        strategy: {
          name: '',
          type: 'momentum',
          parameters: STRATEGY_TEMPLATES.momentum.defaultParams,
          description: STRATEGY_TEMPLATES.momentum.description
        },
        initialCapital: 10000,
        riskLimits: {
          maxPositionSize: 10,
          maxDailyLoss: 500,
          maxDrawdown: 20,
          maxLeverage: 1,
          allowedSymbols: ['BTC/USD', 'ETH/USD', 'SOL/USD'],
          stopLossEnabled: true,
          takeProfitEnabled: true
        }
      })
      setStep(1)
      
      console.log('✅ Agent created successfully:', agent)
    } catch (error) {
      console.error('❌ Failed to create agent:', error)
      setErrors({ general: 'Failed to create agent. Please try again.' })
    } finally {
      setIsCreating(false)
    }
  }

  const availableSymbols = [
    'BTC/USD', 'ETH/USD', 'SOL/USD', 'ADA/USD', 'DOT/USD',
    'LINK/USD', 'UNI/USD', 'AAVE/USD', 'MATIC/USD', 'AVAX/USD'
  ]

  return (
    <div className={className}>
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <div className="flex items-center space-x-3">
            <Bot className="h-8 w-8 text-blue-600" />
            <div>
              <CardTitle className="text-2xl">Create Trading Agent</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Set up an AI agent to trade automatically with your strategy
              </p>
            </div>
          </div>
          
          {/* Progress Steps */}
          <div className="flex items-center space-x-4 mt-6">
            {[1, 2, 3].map((stepNum) => (
              <div key={stepNum} className="flex items-center">
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                  ${step >= stepNum 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-600'
                  }
                `}>
                  {stepNum}
                </div>
                {stepNum < 3 && (
                  <div className={`w-12 h-1 ${step > stepNum ? 'bg-blue-600' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </CardHeader>

        <CardContent>
          {/* Step 1: Basic Configuration */}
          {step === 1 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Bot className="h-5 w-5 mr-2 text-blue-600" />
                  Agent Configuration
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="name">Agent Name *</Label>
                    <Input
                      id="name"
                      value={config.name}
                      onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g., Momentum Master"
                      className={errors.name ? 'border-red-500' : ''}
                    />
                    {errors.name && (
                      <p className="text-sm text-red-500 mt-1">{errors.name}</p>
                    )}
                  </div>
                  
                  <div>
                    <Label htmlFor="initialCapital">Initial Capital *</Label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
                      <Input
                        id="initialCapital"
                        type="number"
                        value={config.initialCapital}
                        onChange={(e) => setConfig(prev => ({ ...prev, initialCapital: Number(e.target.value) }))}
                        className={`pl-9 ${errors.initialCapital ? 'border-red-500' : ''}`}
                        min="1000"
                        step="1000"
                      />
                    </div>
                    {errors.initialCapital && (
                      <p className="text-sm text-red-500 mt-1">{errors.initialCapital}</p>
                    )}
                  </div>
                </div>
                
                <div className="mt-4">
                  <Label htmlFor="description">Description (Optional)</Label>
                  <Textarea
                    id="description"
                    value={config.description}
                    onChange={(e) => setConfig(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Describe what this agent should do..."
                    rows={3}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 2: Strategy Configuration */}
          {step === 2 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
                  Trading Strategy
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="strategyType">Strategy Type *</Label>
                    <Select
                      value={config.strategy.type}
                      onValueChange={handleStrategyChange}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select strategy" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(STRATEGY_TEMPLATES).map(([key, template]) => (
                          <SelectItem key={key} value={key}>
                            <div className="flex items-center space-x-2">
                              <span>{template.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {template.riskProfile}
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="strategyName">Strategy Name *</Label>
                    <Input
                      id="strategyName"
                      value={config.strategy.name}
                      onChange={(e) => setConfig(prev => ({
                        ...prev,
                        strategy: { ...prev.strategy, name: e.target.value }
                      }))}
                      className={errors.strategyName ? 'border-red-500' : ''}
                    />
                    {errors.strategyName && (
                      <p className="text-sm text-red-500 mt-1">{errors.strategyName}</p>
                    )}
                  </div>
                </div>
                
                <div className="mt-4">
                  <Label>Strategy Description</Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    {config.strategy.description}
                  </p>
                </div>
                
                {/* Strategy Parameters */}
                <div className="mt-6">
                  <h4 className="font-medium mb-3 flex items-center">
                    <Sliders className="h-4 w-4 mr-2" />
                    Strategy Parameters
                  </h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(config.strategy.parameters).map(([key, value]) => (
                      <div key={key}>
                        <Label className="capitalize">
                          {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                        </Label>
                        <Input
                          type="number"
                          value={value}
                          onChange={(e) => handleParameterChange(key, Number(e.target.value))}
                          step="0.001"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 3: Risk Management */}
          {step === 3 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Shield className="h-5 w-5 mr-2 text-red-600" />
                  Risk Management
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <Label htmlFor="maxPositionSize">Max Position Size (%)</Label>
                    <Input
                      id="maxPositionSize"
                      type="number"
                      value={config.riskLimits.maxPositionSize}
                      onChange={(e) => setConfig(prev => ({
                        ...prev,
                        riskLimits: { ...prev.riskLimits, maxPositionSize: Number(e.target.value) }
                      }))}
                      min="1"
                      max="50"
                      className={errors.maxPositionSize ? 'border-red-500' : ''}
                    />
                    {errors.maxPositionSize && (
                      <p className="text-sm text-red-500 mt-1">{errors.maxPositionSize}</p>
                    )}
                  </div>
                  
                  <div>
                    <Label htmlFor="maxDailyLoss">Max Daily Loss ($)</Label>
                    <Input
                      id="maxDailyLoss"
                      type="number"
                      value={config.riskLimits.maxDailyLoss}
                      onChange={(e) => setConfig(prev => ({
                        ...prev,
                        riskLimits: { ...prev.riskLimits, maxDailyLoss: Number(e.target.value) }
                      }))}
                      min="100"
                      className={errors.maxDailyLoss ? 'border-red-500' : ''}
                    />
                    {errors.maxDailyLoss && (
                      <p className="text-sm text-red-500 mt-1">{errors.maxDailyLoss}</p>
                    )}
                  </div>
                  
                  <div>
                    <Label htmlFor="maxDrawdown">Max Drawdown (%)</Label>
                    <Input
                      id="maxDrawdown"
                      type="number"
                      value={config.riskLimits.maxDrawdown}
                      onChange={(e) => setConfig(prev => ({
                        ...prev,
                        riskLimits: { ...prev.riskLimits, maxDrawdown: Number(e.target.value) }
                      }))}
                      min="5"
                      max="50"
                    />
                  </div>
                </div>
                
                <div className="mt-6">
                  <Label>Trading Symbols</Label>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-2">
                    {availableSymbols.map(symbol => (
                      <div
                        key={symbol}
                        className={`
                          p-2 border rounded cursor-pointer text-center text-sm font-medium
                          ${config.riskLimits.allowedSymbols.includes(symbol)
                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                            : 'border-gray-200 hover:border-gray-300'
                          }
                        `}
                        onClick={() => handleSymbolToggle(symbol)}
                      >
                        {symbol}
                      </div>
                    ))}
                  </div>
                  {errors.allowedSymbols && (
                    <p className="text-sm text-red-500 mt-1">{errors.allowedSymbols}</p>
                  )}
                </div>
                
                <div className="flex items-center space-x-6 mt-6">
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={config.riskLimits.stopLossEnabled}
                      onCheckedChange={(checked) => setConfig(prev => ({
                        ...prev,
                        riskLimits: { ...prev.riskLimits, stopLossEnabled: checked }
                      }))}
                    />
                    <Label>Stop Loss</Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={config.riskLimits.takeProfitEnabled}
                      onCheckedChange={(checked) => setConfig(prev => ({
                        ...prev,
                        riskLimits: { ...prev.riskLimits, takeProfitEnabled: checked }
                      }))}
                    />
                    <Label>Take Profit</Label>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Error Display */}
          {errors.general && (
            <div className="flex items-center space-x-2 text-red-600 bg-red-50 p-3 rounded-lg mt-6">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm">{errors.general}</span>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={step === 1}
            >
              Back
            </Button>
            
            <div className="text-sm text-muted-foreground">
              Step {step} of 3
            </div>
            
            {step < 3 ? (
              <Button onClick={handleNext}>
                Next
              </Button>
            ) : (
              <Button
                onClick={createAgent}
                disabled={isCreating}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isCreating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                    Creating Agent...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Create Agent
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default RealAgentCreation