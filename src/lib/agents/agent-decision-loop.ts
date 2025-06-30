'use client'

import { unifiedLLMService, type AIDecisionRequest, type AIDecision } from '@/lib/ai/unified-llm-service'
import { backendApi } from '@/lib/api/backend-client'

export interface Agent {
  id: string
  name: string
  type: string
  status: 'active' | 'paused' | 'stopped' | 'error'
  config: {
    decisionInterval: number // milliseconds
    maxRiskPerTrade: number
    symbols: string[]
    strategy: any
  }
  performance: {
    totalPnL: number
    winRate: number
    trades: number
    successfulDecisions: number
    totalDecisions: number
  }
  memory: {
    recentDecisions: any[]
    lessons: string[]
    performance: any
  }
}

export interface MarketData {
  symbol: string
  price: number
  volume: number
  change: number
  timestamp: number
  indicators?: any
}

export interface Portfolio {
  totalValue: number
  cash: number
  positions: Array<{
    symbol: string
    quantity: number
    avgPrice: number
    currentPrice: number
    unrealizedPnL: number
  }>
  pnl: number
}

export class AgentDecisionLoop {
  private activeLoops = new Map<string, NodeJS.Timeout>()
  private agentStates = new Map<string, Agent>()
  
  async startAgent(agentId: string): Promise<void> {
    try {
      console.log(`🚀 Starting agent ${agentId}`)
      
      // Get agent configuration
      const agent = await this.loadAgent(agentId)
      if (!agent) {
        throw new Error(`Agent ${agentId} not found`)
      }
      
      // Stop existing loop if running
      await this.stopAgent(agentId)
      
      // Initialize agent services
      await this.initializeServices(agent)
      
      // Start decision loop
      const interval = setInterval(async () => {
        await this.executeDecisionCycle(agent)
      }, agent.config.decisionInterval || 30000) // Default 30 seconds
      
      this.activeLoops.set(agentId, interval)
      this.agentStates.set(agentId, { ...agent, status: 'active' })
      
      // Update agent status in backend
      await this.updateAgentStatus(agentId, 'active')
      
      console.log(`✅ Agent ${agentId} started with ${agent.config.decisionInterval}ms interval`)
      
    } catch (error) {
      console.error(`❌ Failed to start agent ${agentId}:`, error)
      await this.updateAgentStatus(agentId, 'error')
      throw error
    }
  }
  
  async stopAgent(agentId: string): Promise<void> {
    console.log(`⏹️ Stopping agent ${agentId}`)
    
    const interval = this.activeLoops.get(agentId)
    if (interval) {
      clearInterval(interval)
      this.activeLoops.delete(agentId)
    }
    
    const agent = this.agentStates.get(agentId)
    if (agent) {
      this.agentStates.set(agentId, { ...agent, status: 'stopped' })
    }
    
    await this.updateAgentStatus(agentId, 'stopped')
    console.log(`✅ Agent ${agentId} stopped`)
  }
  
  async pauseAgent(agentId: string): Promise<void> {
    console.log(`⏸️ Pausing agent ${agentId}`)
    
    const interval = this.activeLoops.get(agentId)
    if (interval) {
      clearInterval(interval)
      this.activeLoops.delete(agentId)
    }
    
    const agent = this.agentStates.get(agentId)
    if (agent) {
      this.agentStates.set(agentId, { ...agent, status: 'paused' })
    }
    
    await this.updateAgentStatus(agentId, 'paused')
    console.log(`✅ Agent ${agentId} paused`)
  }
  
  async executeDecisionCycle(agent: Agent): Promise<void> {
    try {
      console.log(`🧠 Decision cycle for agent ${agent.id}`)
      
      // 1. Gather market data
      const marketData = await this.gatherMarketData(agent.config.symbols)
      
      // 2. Get current portfolio state
      const portfolio = await this.getPortfolioState(agent.id)
      
      // 3. Get recent memory and performance
      const memory = await this.getRecentMemory(agent.id)
      
      // 4. Build decision request
      const decisionRequest: AIDecisionRequest = {
        agent: {
          id: agent.id,
          type: agent.type,
          config: agent.config,
          strategy: agent.config.strategy
        },
        marketData,
        portfolio,
        memory,
        context: `Agent ${agent.name} making decision at ${new Date().toISOString()}`
      }
      
      // 5. Make LLM decision
      const decision = await unifiedLLMService.makeDecision(decisionRequest)
      console.log(`💡 Agent ${agent.id} decision:`, decision)
      
      // 6. Validate and execute decision
      if (this.validateDecision(decision, portfolio, agent.config)) {
        await this.executeDecision(agent.id, decision)
        
        // 7. Update memory with successful decision
        await this.updateMemory(agent.id, decision, marketData, 'executed')
        
        // 8. Update performance metrics
        await this.updatePerformance(agent.id, decision, 'success')
        
      } else {
        console.warn(`⚠️ Invalid decision from agent ${agent.id}, skipping execution`)
        await this.updateMemory(agent.id, decision, marketData, 'rejected')
        await this.updatePerformance(agent.id, decision, 'validation_failed')
      }
      
      // 9. Check for learning opportunities
      await this.processLearning(agent.id, decision, marketData)
      
    } catch (error) {
      console.error(`❌ Decision cycle failed for agent ${agent.id}:`, error)
      await this.handleDecisionError(agent.id, error)
    }
  }
  
  private async loadAgent(agentId: string): Promise<Agent | null> {
    try {
      // Try to load from backend first
      const response = await backendApi.get(`/api/v1/agents/${agentId}`)
      if (response.data) {
        return this.transformBackendAgent(response.data)
      }
    } catch (error) {
      console.warn('Backend agent load failed, trying localStorage:', error)
    }
    
    // Fallback to localStorage
    const stored = localStorage.getItem(`agent_${agentId}`)
    return stored ? JSON.parse(stored) : null
  }
  
  private transformBackendAgent(backendAgent: any): Agent {
    return {
      id: backendAgent.agent_id || backendAgent.id,
      name: backendAgent.name || backendAgent.agent_name,
      type: backendAgent.type || backendAgent.agent_type,
      status: backendAgent.status || 'stopped',
      config: {
        decisionInterval: backendAgent.decision_interval || 30000,
        maxRiskPerTrade: backendAgent.max_risk_per_trade || 0.05,
        symbols: backendAgent.symbols || ['BTC/USD', 'ETH/USD'],
        strategy: backendAgent.strategy || {}
      },
      performance: {
        totalPnL: backendAgent.total_pnl || 0,
        winRate: backendAgent.win_rate || 0,
        trades: backendAgent.trade_count || 0,
        successfulDecisions: backendAgent.successful_decisions || 0,
        totalDecisions: backendAgent.total_decisions || 0
      },
      memory: {
        recentDecisions: backendAgent.recent_decisions || [],
        lessons: backendAgent.lessons || [],
        performance: backendAgent.performance_data || {}
      }
    }
  }
  
  private async initializeServices(agent: Agent): Promise<void> {
    // Initialize any required services for the agent
    console.log(`🔧 Initializing services for agent ${agent.id}`)
    
    // Could include:
    // - Market data subscriptions
    // - Risk management setup
    // - Portfolio tracking
    // - Memory system initialization
  }
  
  private async gatherMarketData(symbols: string[]): Promise<MarketData[]> {
    try {
      // Try to get real market data from backend
      const response = await backendApi.get('/api/v1/market/live-data', {
        params: { symbols: symbols.join(',') }
      })
      
      if (response.data) {
        return response.data.map((item: any) => ({
          symbol: item.symbol,
          price: item.price,
          volume: item.volume,
          change: item.change_24h,
          timestamp: Date.now(),
          indicators: item.indicators
        }))
      }
    } catch (error) {
      console.warn('Backend market data failed, using mock data:', error)
    }
    
    // Fallback to mock data
    return this.generateMockMarketData(symbols)
  }
  
  private generateMockMarketData(symbols: string[]): MarketData[] {
    return symbols.map(symbol => {
      const basePrice = this.getBasePrice(symbol)
      const change = (Math.random() - 0.5) * 10 // -5% to +5%
      const price = basePrice * (1 + change / 100)
      
      return {
        symbol,
        price,
        volume: Math.random() * 1000000,
        change,
        timestamp: Date.now(),
        indicators: {
          rsi: 30 + Math.random() * 40,
          macd: Math.random() - 0.5,
          ema: price * (0.95 + Math.random() * 0.1)
        }
      }
    })
  }
  
  private getBasePrice(symbol: string): number {
    const prices: Record<string, number> = {
      'BTC/USD': 45000,
      'ETH/USD': 2500,
      'SOL/USD': 100,
      'ADA/USD': 0.5,
      'DOT/USD': 8,
      'MATIC/USD': 1.2
    }
    return prices[symbol] || 100
  }
  
  private async getPortfolioState(agentId: string): Promise<Portfolio> {
    try {
      // Try backend first
      const response = await backendApi.get(`/api/v1/agents/${agentId}/portfolio`)
      if (response.data) {
        return response.data
      }
    } catch (error) {
      console.warn('Backend portfolio data failed, using mock:', error)
    }
    
    // Mock portfolio data
    return {
      totalValue: 10000 + Math.random() * 5000,
      cash: 5000 + Math.random() * 2000,
      positions: [
        {
          symbol: 'BTC/USD',
          quantity: 0.1,
          avgPrice: 44000,
          currentPrice: 45000,
          unrealizedPnL: 100
        }
      ],
      pnl: Math.random() * 1000 - 500
    }
  }
  
  private async getRecentMemory(agentId: string): Promise<any> {
    try {
      const response = await backendApi.get(`/api/v1/agents/${agentId}/memory`)
      if (response.data) {
        return response.data
      }
    } catch (error) {
      console.warn('Backend memory data failed, using empty:', error)
    }
    
    return {
      recentDecisions: [],
      performance: { winRate: 0.6, avgReturn: 0.02 },
      lessons: ['Be cautious during high volatility', 'Take profits gradually']
    }
  }
  
  private validateDecision(decision: AIDecision, portfolio: Portfolio, config: any): boolean {
    // Basic decision validation
    if (!decision.action || !decision.reasoning) {
      return false
    }
    
    // Risk validation
    if (decision.action === 'buy' && decision.quantity) {
      const cost = (decision.quantity * (decision.price || 0))
      const maxRisk = portfolio.cash * (config.maxRiskPerTrade || 0.05)
      if (cost > maxRisk) {
        console.warn(`Decision rejected: Risk too high (${cost} > ${maxRisk})`)
        return false
      }
    }
    
    // Symbol validation
    if (decision.symbol && !config.symbols.includes(decision.symbol)) {
      console.warn(`Decision rejected: Symbol ${decision.symbol} not in allowed list`)
      return false
    }
    
    return true
  }
  
  private async executeDecision(agentId: string, decision: AIDecision): Promise<void> {
    try {
      console.log(`📈 Executing decision for agent ${agentId}:`, decision)
      
      // Try backend execution first
      try {
        await backendApi.post(`/api/v1/agents/${agentId}/execute-decision`, {
          decision,
          timestamp: Date.now()
        })
        console.log(`✅ Decision executed via backend`)
        return
      } catch (error) {
        console.warn('Backend execution failed, using mock:', error)
      }
      
      // Mock execution
      const executionResult = {
        orderId: `order_${Date.now()}`,
        status: 'filled',
        fillPrice: decision.price || 0,
        fillQuantity: decision.quantity || 0,
        timestamp: Date.now()
      }
      
      // Store execution in localStorage
      const executions = JSON.parse(localStorage.getItem(`executions_${agentId}`) || '[]')
      executions.push({
        decision,
        execution: executionResult,
        timestamp: Date.now()
      })
      localStorage.setItem(`executions_${agentId}`, JSON.stringify(executions))
      
      console.log(`✅ Mock execution completed:`, executionResult)
      
    } catch (error) {
      console.error(`❌ Execution failed:`, error)
      throw error
    }
  }
  
  private async updateMemory(
    agentId: string, 
    decision: AIDecision, 
    marketData: MarketData[], 
    status: 'executed' | 'rejected'
  ): Promise<void> {
    const memoryEntry = {
      timestamp: Date.now(),
      decision,
      marketData,
      status,
      confidence: decision.confidence,
      reasoning: decision.reasoning
    }
    
    try {
      await backendApi.post(`/api/v1/agents/${agentId}/memory`, memoryEntry)
    } catch (error) {
      // Store in localStorage as fallback
      const memories = JSON.parse(localStorage.getItem(`memory_${agentId}`) || '[]')
      memories.push(memoryEntry)
      // Keep only last 100 memories
      if (memories.length > 100) {
        memories.splice(0, memories.length - 100)
      }
      localStorage.setItem(`memory_${agentId}`, JSON.stringify(memories))
    }
  }
  
  private async updatePerformance(
    agentId: string, 
    decision: AIDecision, 
    result: 'success' | 'validation_failed' | 'execution_failed'
  ): Promise<void> {
    const agent = this.agentStates.get(agentId)
    if (!agent) return
    
    // Update local performance metrics
    agent.performance.totalDecisions++
    if (result === 'success') {
      agent.performance.successfulDecisions++
    }
    
    this.agentStates.set(agentId, agent)
    
    try {
      await backendApi.post(`/api/v1/agents/${agentId}/performance`, {
        decision,
        result,
        timestamp: Date.now(),
        performance: agent.performance
      })
    } catch (error) {
      console.warn('Backend performance update failed:', error)
    }
  }
  
  private async processLearning(agentId: string, decision: AIDecision, marketData: MarketData[]): Promise<void> {
    // Simple learning: if decision confidence was low but market moved in predicted direction, increase confidence
    // This is a placeholder for more sophisticated learning algorithms
    
    console.log(`🧠 Processing learning for agent ${agentId}`)
    
    // In a real implementation, this would:
    // 1. Analyze decision outcomes after some time
    // 2. Update strategy parameters based on results
    // 3. Learn from successful/failed decisions
    // 4. Adjust risk parameters
    // 5. Update neural network weights if using ML
  }
  
  private async handleDecisionError(agentId: string, error: any): Promise<void> {
    console.error(`🚨 Decision error for agent ${agentId}:`, error)
    
    const agent = this.agentStates.get(agentId)
    if (agent) {
      // Mark agent as error state
      this.agentStates.set(agentId, { ...agent, status: 'error' })
      await this.updateAgentStatus(agentId, 'error')
      
      // Stop the agent if too many errors
      const errorCount = agent.performance.totalDecisions - agent.performance.successfulDecisions
      if (errorCount > 10) {
        console.error(`🛑 Stopping agent ${agentId} due to too many errors`)
        await this.stopAgent(agentId)
      }
    }
  }
  
  private async updateAgentStatus(agentId: string, status: string): Promise<void> {
    try {
      await backendApi.post(`/api/v1/agents/${agentId}/status`, {
        status,
        timestamp: Date.now()
      })
    } catch (error) {
      // Store status in localStorage as fallback
      localStorage.setItem(`agent_status_${agentId}`, JSON.stringify({
        status,
        timestamp: Date.now()
      }))
    }
  }
  
  // Public methods for agent management
  getActiveAgents(): string[] {
    return Array.from(this.activeLoops.keys())
  }
  
  getAgentStatus(agentId: string): string {
    const agent = this.agentStates.get(agentId)
    return agent?.status || 'unknown'
  }
  
  getAllAgentStates(): Map<string, Agent> {
    return new Map(this.agentStates)
  }
  
  async startAllAgents(): Promise<void> {
    // Load all agents and start them
    try {
      const response = await backendApi.get('/api/v1/agents')
      const agents = response.data || []
      
      for (const agent of agents) {
        if (agent.status === 'active' || agent.auto_start) {
          await this.startAgent(agent.id)
        }
      }
    } catch (error) {
      console.warn('Failed to load agents from backend:', error)
    }
  }
  
  async stopAllAgents(): Promise<void> {
    const activeAgents = this.getActiveAgents()
    for (const agentId of activeAgents) {
      await this.stopAgent(agentId)
    }
  }
}

// Export singleton instance
export const agentDecisionLoop = new AgentDecisionLoop()