'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Bot,
  Play,
  Pause,
  Square,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Settings,
  Eye,
  MoreVertical,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Activity,
  PieChart,
  Target,
  Zap
} from 'lucide-react'
import {
  paperTradingEngine,
  TradingAgent,
  Position,
  Order,
  Transaction
} from '@/lib/trading/real-paper-trading-engine'

interface RealAgentManagementProps {
  className?: string
}

export function RealAgentManagement({ className }: RealAgentManagementProps) {
  const [agents, setAgents] = useState<TradingAgent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<TradingAgent | null>(null)
  const [marketPrices, setMarketPrices] = useState<Record<string, number>>({})
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    // Load agents
    loadAgents()
    
    // Start the trading engine if not already running
    if (!paperTradingEngine.listenerCount('pricesUpdated')) {
      paperTradingEngine.start()
    }

    // Listen for engine events
    const handleAgentCreated = (agent: TradingAgent) => {
      setAgents(prev => [...prev, agent])
    }

    const handlePricesUpdated = (prices: any[]) => {
      const priceMap: Record<string, number> = {}
      prices.forEach(price => {
        priceMap[price.symbol] = price.price
      })
      setMarketPrices(priceMap)
      
      // Update agent portfolios
      loadAgents()
    }

    const handleOrderFilled = () => {
      loadAgents() // Refresh agents when orders are filled
    }

    paperTradingEngine.on('agentCreated', handleAgentCreated)
    paperTradingEngine.on('pricesUpdated', handlePricesUpdated)
    paperTradingEngine.on('orderFilled', handleOrderFilled)

    // Update agents every 5 seconds
    const interval = setInterval(loadAgents, 5000)

    return () => {
      paperTradingEngine.off('agentCreated', handleAgentCreated)
      paperTradingEngine.off('pricesUpdated', handlePricesUpdated)
      paperTradingEngine.off('orderFilled', handleOrderFilled)
      clearInterval(interval)
    }
  }, [])

  const loadAgents = () => {
    const allAgents = paperTradingEngine.getAllAgents()
    setAgents(allAgents)
  }

  const handleAgentAction = (agentId: string, action: 'start' | 'pause' | 'stop') => {
    const agent = paperTradingEngine.getAgent(agentId)
    if (!agent) return

    // Update agent status
    agent.status = action === 'start' ? 'active' : action === 'pause' ? 'paused' : 'stopped'
    agent.lastActive = new Date()
    
    setAgents(prev => prev.map(a => a.id === agentId ? agent : a))
    
    console.log(`🎮 Agent ${agent.name} ${action}ed`)
  }

  const calculatePortfolioChange = (agent: TradingAgent): { value: number; percentage: number } => {
    const initialValue = 10000 // Default initial value
    const currentValue = agent.portfolio.totalValue
    const change = currentValue - initialValue
    const percentage = (change / initialValue) * 100
    
    return { value: change, percentage }
  }

  const getStatusColor = (status: TradingAgent['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-500'
      case 'paused':
        return 'bg-yellow-500'
      case 'stopped':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStrategyIcon = (strategyType: string) => {
    switch (strategyType) {
      case 'momentum':
        return <TrendingUp className="h-4 w-4" />
      case 'mean_reversion':
        return <TrendingDown className="h-4 w-4" />
      case 'arbitrage':
        return <Zap className="h-4 w-4" />
      case 'grid':
        return <BarChart3 className="h-4 w-4" />
      case 'dca':
        return <Clock className="h-4 w-4" />
      default:
        return <Target className="h-4 w-4" />
    }
  }

  return (
    <div className={className}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Agent Management</h2>
            <p className="text-sm text-gray-600">Monitor and control your trading agents</p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-sm">
              {agents.length} Agent{agents.length !== 1 ? 's' : ''}
            </Badge>
            <Badge variant={agents.some(a => a.status === 'active') ? 'default' : 'secondary'}>
              {agents.filter(a => a.status === 'active').length} Active
            </Badge>
          </div>
        </div>

        {/* Agents Grid */}
        {agents.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <Bot className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No agents created yet</h3>
              <p className="text-gray-600 mb-4">Create your first trading agent to get started</p>
              <Button>Create Agent</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => {
              const portfolioChange = calculatePortfolioChange(agent)
              const activePositions = agent.portfolio.positions.length
              const pendingOrders = agent.portfolio.orders.filter(o => o.status === 'pending').length

              return (
                <motion.div
                  key={agent.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <Card className="hover:shadow-lg transition-shadow duration-200">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <div className={`w-3 h-3 rounded-full ${getStatusColor(agent.status)}`} />
                          <h3 className="font-semibold text-lg">{agent.name}</h3>
                        </div>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            {agent.status !== 'active' && (
                              <DropdownMenuItem onClick={() => handleAgentAction(agent.id, 'start')}>
                                <Play className="h-4 w-4 mr-2" />
                                Start
                              </DropdownMenuItem>
                            )}
                            {agent.status === 'active' && (
                              <DropdownMenuItem onClick={() => handleAgentAction(agent.id, 'pause')}>
                                <Pause className="h-4 w-4 mr-2" />
                                Pause
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem onClick={() => handleAgentAction(agent.id, 'stop')}>
                              <Square className="h-4 w-4 mr-2" />
                              Stop
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => setSelectedAgent(agent)}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {getStrategyIcon(agent.strategy.type)}
                        <span className="text-sm text-gray-600">{agent.strategy.name}</span>
                        <Badge variant="outline" className="text-xs">
                          {agent.strategy.type}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-4">
                      {/* Portfolio Value */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Portfolio Value</span>
                          <span className="text-lg font-bold">
                            ${agent.portfolio.totalValue.toLocaleString()}
                          </span>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">P&L</span>
                          <div className="flex items-center space-x-1">
                            {portfolioChange.value >= 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-500" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-red-500" />
                            )}
                            <span className={`text-sm font-medium ${
                              portfolioChange.value >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {portfolioChange.value >= 0 ? '+' : ''}${portfolioChange.value.toFixed(2)}
                              ({portfolioChange.percentage >= 0 ? '+' : ''}{portfolioChange.percentage.toFixed(2)}%)
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Stats */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="text-center">
                          <div className="text-lg font-bold text-blue-600">{activePositions}</div>
                          <div className="text-xs text-gray-600">Positions</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-bold text-orange-600">{pendingOrders}</div>
                          <div className="text-xs text-gray-600">Pending</div>
                        </div>
                      </div>

                      {/* Performance Metrics */}
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Win Rate</span>
                          <span className="font-medium">{(agent.performance.winRate * 100).toFixed(1)}%</span>
                        </div>
                        <Progress value={agent.performance.winRate * 100} className="h-2" />
                      </div>

                      {/* Last Active */}
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>Last active</span>
                        <span>{agent.lastActive.toLocaleTimeString()}</span>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex space-x-2 pt-2">
                        {agent.status !== 'active' ? (
                          <Button
                            size="sm"
                            onClick={() => handleAgentAction(agent.id, 'start')}
                            className="flex-1"
                          >
                            <Play className="h-3 w-3 mr-1" />
                            Start
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleAgentAction(agent.id, 'pause')}
                            className="flex-1"
                          >
                            <Pause className="h-3 w-3 mr-1" />
                            Pause
                          </Button>
                        )}
                        
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setSelectedAgent(agent)}
                        >
                          <Eye className="h-3 w-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        )}

        {/* Agent Details Modal */}
        <Dialog open={selectedAgent !== null} onOpenChange={() => setSelectedAgent(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            {selectedAgent && (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center space-x-2">
                    <Bot className="h-6 w-6 text-blue-600" />
                    <span>{selectedAgent.name}</span>
                    <Badge variant={selectedAgent.status === 'active' ? 'default' : 'secondary'}>
                      {selectedAgent.status}
                    </Badge>
                  </DialogTitle>
                  <DialogDescription>
                    {selectedAgent.strategy.description}
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-6">
                  {/* Portfolio Overview */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Portfolio Overview</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card>
                        <CardContent className="p-4 text-center">
                          <DollarSign className="h-6 w-6 mx-auto text-green-600 mb-2" />
                          <div className="text-sm text-gray-600">Cash</div>
                          <div className="text-lg font-bold">${selectedAgent.portfolio.cash.toFixed(2)}</div>
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardContent className="p-4 text-center">
                          <PieChart className="h-6 w-6 mx-auto text-blue-600 mb-2" />
                          <div className="text-sm text-gray-600">Total Value</div>
                          <div className="text-lg font-bold">${selectedAgent.portfolio.totalValue.toFixed(2)}</div>
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardContent className="p-4 text-center">
                          <BarChart3 className="h-6 w-6 mx-auto text-purple-600 mb-2" />
                          <div className="text-sm text-gray-600">Positions</div>
                          <div className="text-lg font-bold">{selectedAgent.portfolio.positions.length}</div>
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardContent className="p-4 text-center">
                          <Activity className="h-6 w-6 mx-auto text-orange-600 mb-2" />
                          <div className="text-sm text-gray-600">Total Trades</div>
                          <div className="text-lg font-bold">{selectedAgent.performance.totalTrades}</div>
                        </CardContent>
                      </Card>
                    </div>
                  </div>

                  {/* Positions */}
                  {selectedAgent.portfolio.positions.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Open Positions</h3>
                      <div className="space-y-2">
                        {selectedAgent.portfolio.positions.map((position) => (
                          <Card key={position.id}>
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="font-medium">{position.symbol}</div>
                                  <div className="text-sm text-gray-600">
                                    {position.quantity} @ ${position.averagePrice.toFixed(2)}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="font-medium">${position.marketValue.toFixed(2)}</div>
                                  <div className={`text-sm ${
                                    position.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                                  }`}>
                                    {position.unrealizedPnL >= 0 ? '+' : ''}${position.unrealizedPnL.toFixed(2)}
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recent Orders */}
                  {selectedAgent.portfolio.orders.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Recent Orders</h3>
                      <div className="space-y-2">
                        {selectedAgent.portfolio.orders.slice(-5).map((order) => (
                          <Card key={order.id}>
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="font-medium flex items-center space-x-2">
                                    <span>{order.symbol}</span>
                                    <Badge variant={order.side === 'buy' ? 'default' : 'secondary'}>
                                      {order.side}
                                    </Badge>
                                    <Badge variant="outline">
                                      {order.type}
                                    </Badge>
                                  </div>
                                  <div className="text-sm text-gray-600">
                                    {order.quantity} @ ${order.price?.toFixed(2) || 'Market'}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <Badge variant={
                                    order.status === 'filled' ? 'default' :
                                    order.status === 'pending' ? 'secondary' : 'destructive'
                                  }>
                                    {order.status}
                                  </Badge>
                                  <div className="text-sm text-gray-600 mt-1">
                                    {order.createdAt.toLocaleTimeString()}
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

export default RealAgentManagement