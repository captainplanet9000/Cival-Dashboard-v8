/**
 * MCP Integration Service
 * Comprehensive Model Context Protocol infrastructure for all agents
 */

import { EventEmitter } from 'events'

// Lazy load all services to prevent circular dependencies
const getAgentPersistenceService = () => import('@/lib/agents/AgentPersistenceService').then(m => m.agentPersistenceService)
const getVaultIntegrationService = () => import('@/lib/vault/VaultIntegrationService').then(m => m.vaultIntegrationService)
const getPersistentTradingEngine = () => import('@/lib/paper-trading/PersistentTradingEngine').then(m => m.persistentTradingEngine)
const getTestnetDeFiService = () => import('@/lib/defi/TestnetDeFiService').then(m => m.testnetDeFiService)
// TEMPORARILY DISABLED: Circular dependency through geminiService
// const getGeminiService = () => import('@/lib/ai/GeminiService').then(m => m.geminiService)
const getAgentTodoService = () => import('@/lib/agents/AgentTodoService').then(m => m.agentTodoService)

export interface MCPTool {
  id: string
  name: string
  description: string
  category: 'trading' | 'defi' | 'analysis' | 'system' | 'communication' | 'data'
  version: string
  permissions: string[]
  parameters: MCPParameter[]
  enabled: boolean
  usage: {
    totalCalls: number
    lastUsed: number
    successRate: number
    avgResponseTime: number
  }
}

export interface MCPParameter {
  name: string
  type: 'string' | 'number' | 'boolean' | 'object' | 'array'
  description: string
  required: boolean
  default?: any
  validation?: {
    min?: number
    max?: number
    pattern?: string
    enum?: string[]
  }
}

export interface MCPServerConfig {
  id: string
  name: string
  url: string
  version: string
  status: 'connected' | 'disconnected' | 'error' | 'initializing'
  capabilities: string[]
  tools: string[]
  lastHeartbeat: number
  metadata: Record<string, any>
}

export interface MCPAgentPermissions {
  agentId: string
  allowedTools: string[]
  allowedCategories: string[]
  restrictions: {
    maxCallsPerMinute: number
    maxCallsPerDay: number
    requireApproval: string[]
    blockedTools: string[]
  }
  audit: {
    enabled: boolean
    logLevel: 'minimal' | 'detailed' | 'verbose'
    retentionDays: number
  }
}

export interface MCPCallLog {
  id: string
  agentId: string
  toolId: string
  parameters: Record<string, any>
  response: any
  success: boolean
  error?: string
  timestamp: number
  duration: number
  context: {
    sessionId: string
    requestId: string
    userContext?: string
  }
}

export interface MCPSession {
  id: string
  agentId: string
  startTime: number
  endTime?: number
  totalCalls: number
  successfulCalls: number
  failedCalls: number
  tools: string[]
  context: Record<string, any>
  status: 'active' | 'completed' | 'error' | 'timeout'
}

class MCPIntegrationService extends EventEmitter {
  private servers: Map<string, MCPServerConfig> = new Map()
  private tools: Map<string, MCPTool> = new Map()
  private agentPermissions: Map<string, MCPAgentPermissions> = new Map()
  private callLogs: MCPCallLog[] = []
  private sessions: Map<string, MCPSession> = new Map()
  private rateLimits: Map<string, { count: number, resetTime: number }> = new Map()
  
  // Lazy loaded services
  private agentPersistenceService: any = null
  private vaultIntegrationService: any = null
  private persistentTradingEngine: any = null
  private testnetDeFiService: any = null
  private geminiService: any = null
  private agentTodoService: any = null
  
  constructor() {
    super()
    this.initializeAsync()
  }
  
  private async initializeAsync() {
    try {
      // Load services lazily to prevent circular dependencies
      this.agentPersistenceService = await getAgentPersistenceService().catch(() => null)
      this.vaultIntegrationService = await getVaultIntegrationService().catch(() => null)
      this.persistentTradingEngine = await getPersistentTradingEngine().catch(() => null)
      this.testnetDeFiService = await getTestnetDeFiService().catch(() => null)
      this.agentTodoService = await getAgentTodoService().catch(() => null)
      
      this.initializeDefaultTools()
      this.setupEventListeners()
      this.startHeartbeat()
      this.loadPersistedData()
    } catch (error) {
      console.error('Failed to initialize MCPIntegrationService:', error)
    }
  }

  // Initialize all agents with MCP infrastructure
  async activateForAllAgents(): Promise<void> {
    console.log('🚀 Activating MCP infrastructure for all agents...')
    
    const agents = this.agentPersistenceService?.getAllAgents() || []
    const results = []
    
    for (const agent of agents) {
      try {
        const result = await this.activateForAgent(agent.id)
        results.push({ agentId: agent.id, success: result.success, errors: result.errors })
        
        if (result.success) {
          console.log(`✅ MCP activated for agent: ${agent.config.name}`)
        } else {
          console.error(`❌ MCP activation failed for agent: ${agent.config.name}`, result.errors)
        }
      } catch (error) {
        console.error(`💥 Critical error activating MCP for agent ${agent.id}:`, error)
        results.push({ agentId: agent.id, success: false, errors: [`Critical error: ${error}`] })
      }
    }
    
    const successCount = results.filter(r => r.success).length
    console.log(`🎉 MCP infrastructure activated for ${successCount}/${agents.length} agents`)
    
    this.emit('mcpActivatedForAll', { 
      totalAgents: agents.length, 
      successCount, 
      results 
    })
  }

  // Activate MCP for a specific agent
  async activateForAgent(agentId: string): Promise<{ success: boolean; errors?: string[] }> {
    try {
      const agent = this.agentPersistenceService?.getAgent(agentId)
      if (!agent) {
        return { success: false, errors: ['Agent not found'] }
      }

      // 1. Setup agent permissions based on agent config
      const permissions = this.createAgentPermissions(agent)
      this.agentPermissions.set(agentId, permissions)

      // 2. Create MCP session for agent
      const session = this.createSession(agentId)
      this.sessions.set(session.id, session)

      this.persistData()
      this.emit('mcpActivatedForAgent', { agentId, session, permissions })
      
      return { success: true }
    } catch (error) {
      console.error('MCP activation failed:', error)
      return { success: false, errors: [`Activation failed: ${error}`] }
    }
  }

  // Execute MCP tool call for agent
  async callTool(
    agentId: string, 
    toolId: string, 
    parameters: Record<string, any>,
    context?: Record<string, any>
  ): Promise<any> {
    const startTime = Date.now()
    const callId = `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    try {
      // 1. Validate agent permissions
      const permissions = this.agentPermissions.get(agentId)
      if (!permissions) {
        throw new Error('Agent not registered for MCP')
      }

      // 2. Get tool definition
      const tool = this.tools.get(toolId)
      if (!tool || !tool.enabled) {
        throw new Error(`Tool not found or disabled: ${toolId}`)
      }

      // 3. Execute tool
      const response = await this.executeTool(tool, parameters, { agentId, ...context })

      // 4. Log successful call
      const callLog: MCPCallLog = {
        id: callId,
        agentId,
        toolId,
        parameters,
        response,
        success: true,
        timestamp: startTime,
        duration: Date.now() - startTime,
        context: {
          sessionId: this.getActiveSessionId(agentId),
          requestId: callId,
          userContext: context?.userContext
        }
      }

      this.logCall(callLog)
      this.updateToolUsage(toolId, true, Date.now() - startTime)
      
      return response
    } catch (error) {
      // Log failed call
      const callLog: MCPCallLog = {
        id: callId,
        agentId,
        toolId,
        parameters,
        response: null,
        success: false,
        error: error.toString(),
        timestamp: startTime,
        duration: Date.now() - startTime,
        context: {
          sessionId: this.getActiveSessionId(agentId),
          requestId: callId,
          userContext: context?.userContext
        }
      }

      this.logCall(callLog)
      this.updateToolUsage(toolId, false, Date.now() - startTime)
      
      throw error
    }
  }

  // Get available tools for agent
  getAvailableTools(agentId: string): MCPTool[] {
    const permissions = this.agentPermissions.get(agentId)
    if (!permissions) return []

    return Array.from(this.tools.values()).filter(tool => 
      tool.enabled && 
      (permissions.allowedTools.includes(tool.id) || 
       permissions.allowedCategories.includes(tool.category)) &&
      !permissions.restrictions.blockedTools.includes(tool.id)
    )
  }

  // Get agent session statistics
  getAgentStats(agentId: string) {
    const calls = this.callLogs.filter(log => log.agentId === agentId)
    const sessions = Array.from(this.sessions.values()).filter(s => s.agentId === agentId)
    const permissions = this.agentPermissions.get(agentId)

    return {
      totalCalls: calls.length,
      successfulCalls: calls.filter(c => c.success).length,
      failedCalls: calls.filter(c => !c.success).length,
      successRate: calls.length > 0 ? calls.filter(c => c.success).length / calls.length : 0,
      avgResponseTime: calls.length > 0 ? calls.reduce((sum, c) => sum + c.duration, 0) / calls.length : 0,
      totalSessions: sessions.length,
      activeSessions: sessions.filter(s => s.status === 'active').length,
      availableTools: this.getAvailableTools(agentId).length,
      permissions,
      recentCalls: calls.slice(-10)
    }
  }

  // Private helper methods
  private initializeDefaultTools(): void {
    // Trading Tools
    this.tools.set('trading.place_order', {
      id: 'trading.place_order',
      name: 'Place Trading Order',
      description: 'Execute a trading order through the paper trading engine',
      category: 'trading',
      version: '1.0.0',
      permissions: ['trading.execute'],
      parameters: [
        { name: 'symbol', type: 'string', description: 'Trading pair symbol', required: true },
        { name: 'side', type: 'string', description: 'Order side (buy/sell)', required: true, validation: { enum: ['buy', 'sell'] } },
        { name: 'amount', type: 'number', description: 'Order amount', required: true, validation: { min: 0 } },
        { name: 'type', type: 'string', description: 'Order type', required: false, validation: { enum: ['market', 'limit'] } },
        { name: 'price', type: 'number', description: 'Limit price (for limit orders)', required: false }
      ],
      enabled: true,
      usage: { totalCalls: 0, lastUsed: 0, successRate: 0, avgResponseTime: 0 }
    })

    this.tools.set('analysis.market_sentiment', {
      id: 'analysis.market_sentiment',
      name: 'Analyze Market Sentiment',
      description: 'Get market sentiment analysis using AI',
      category: 'analysis',
      version: '1.0.0',
      permissions: ['analysis.read'],
      parameters: [
        { name: 'symbol', type: 'string', description: 'Asset symbol to analyze', required: true },
        { name: 'timeframe', type: 'string', description: 'Analysis timeframe', required: false, validation: { enum: ['1h', '4h', '1d', '1w'] } }
      ],
      enabled: true,
      usage: { totalCalls: 0, lastUsed: 0, successRate: 0, avgResponseTime: 0 }
    })

    this.tools.set('system.create_todo', {
      id: 'system.create_todo',
      name: 'Create Todo Item',
      description: 'Create a new todo item for the agent',
      category: 'system',
      version: '1.0.0',
      permissions: ['system.write'],
      parameters: [
        { name: 'title', type: 'string', description: 'Todo title', required: true },
        { name: 'description', type: 'string', description: 'Todo description', required: false },
        { name: 'priority', type: 'string', description: 'Todo priority', required: false, validation: { enum: ['low', 'medium', 'high'] } }
      ],
      enabled: true,
      usage: { totalCalls: 0, lastUsed: 0, successRate: 0, avgResponseTime: 0 }
    })
  }

  private createAgentPermissions(agent: any): MCPAgentPermissions {
    const basePermissions = ['trading.read', 'analysis.read', 'system.write', 'data.write']
    const allowedTools = this.getToolsForPermissions(basePermissions)

    return {
      agentId: agent.id,
      allowedTools,
      allowedCategories: ['trading', 'analysis', 'system', 'data'],
      restrictions: {
        maxCallsPerMinute: 60,
        maxCallsPerDay: 5000,
        requireApproval: ['trading.place_order'],
        blockedTools: []
      },
      audit: {
        enabled: true,
        logLevel: 'detailed',
        retentionDays: 30
      }
    }
  }

  private getToolsForPermissions(permissions: string[]): string[] {
    return Array.from(this.tools.values())
      .filter(tool => tool.permissions.some(perm => permissions.includes(perm)))
      .map(tool => tool.id)
  }

  private createSession(agentId: string): MCPSession {
    return {
      id: `session_${agentId}_${Date.now()}`,
      agentId,
      startTime: Date.now(),
      totalCalls: 0,
      successfulCalls: 0,
      failedCalls: 0,
      tools: [],
      context: {},
      status: 'active'
    }
  }

  private async executeTool(tool: MCPTool, parameters: Record<string, any>, context: any): Promise<any> {
    switch (tool.id) {
      case 'trading.place_order':
        return await this.executeTradeOrder(parameters, context)
      
      case 'analysis.market_sentiment':
        return await this.analyzeMarketSentiment(parameters, context)
      
      case 'system.create_todo':
        return await this.createTodo(parameters, context)
      
      default:
        throw new Error(`Tool not implemented: ${tool.id}`)
    }
  }

  // Tool implementations
  private async executeTradeOrder(params: any, context: any): Promise<any> {
    const order = await this.persistentTradingEngine?.placeOrder(
      context.agentId,
      params.symbol,
      params.side,
      params.amount,
      params.type || 'market',
      params.price
    )
    return { success: true, orderId: order?.id, order }
  }

  private async analyzeMarketSentiment(params: any, context: any): Promise<any> {
    // Fallback mock sentiment
    return { 
      symbol: params.symbol, 
      sentiment: 'Neutral market sentiment (mock data)', 
      score: 0.1,
      timestamp: Date.now() 
    }
  }

  private async createTodo(params: any, context: any): Promise<any> {
    const todo = await this.agentTodoService?.createTodo(context.agentId, {
      title: params.title,
      description: params.description || '',
      priority: params.priority || 'medium',
      category: 'agent-generated',
      estimatedDuration: 1800000, // 30 minutes default
      tags: ['mcp-generated']
    })
    return { success: true, todoId: todo?.id, todo }
  }

  private getActiveSessionId(agentId: string): string {
    const sessions = Array.from(this.sessions.values()).filter(s => 
      s.agentId === agentId && s.status === 'active'
    )
    return sessions.length > 0 ? sessions[0].id : 'no-session'
  }

  private logCall(callLog: MCPCallLog): void {
    this.callLogs.push(callLog)
    
    // Keep only last 1000 logs to prevent memory issues
    if (this.callLogs.length > 1000) {
      this.callLogs = this.callLogs.slice(-1000)
    }
    
    this.emit('toolCalled', callLog)
  }

  private updateToolUsage(toolId: string, success: boolean, duration: number): void {
    const tool = this.tools.get(toolId)
    if (tool) {
      tool.usage.totalCalls++
      tool.usage.lastUsed = Date.now()
      
      const successCount = tool.usage.totalCalls * tool.usage.successRate + (success ? 1 : 0)
      tool.usage.successRate = successCount / tool.usage.totalCalls
      
      const totalTime = tool.usage.avgResponseTime * (tool.usage.totalCalls - 1) + duration
      tool.usage.avgResponseTime = totalTime / tool.usage.totalCalls
    }
  }

  private setupEventListeners(): void {
    // Listen to agent events
    this.agentPersistenceService?.on?.('agentCreated', async (data: any) => {
      await this.activateForAgent(data.agentId)
    })

    this.agentPersistenceService?.on?.('agentDeleted', (data: any) => {
      this.deactivateForAgent(data.agentId)
    })
  }

  private deactivateForAgent(agentId: string): void {
    // Close active sessions
    const sessions = Array.from(this.sessions.values()).filter(s => s.agentId === agentId)
    sessions.forEach(session => {
      session.status = 'completed'
      session.endTime = Date.now()
    })

    // Remove permissions
    this.agentPermissions.delete(agentId)
    
    // Clean up rate limits
    for (const [key] of this.rateLimits.entries()) {
      if (key.startsWith(`${agentId}:`)) {
        this.rateLimits.delete(key)
      }
    }

    this.persistData()
    this.emit('mcpDeactivatedForAgent', { agentId })
  }

  private startHeartbeat(): void {
    setInterval(() => {
      this.performHealthCheck()
    }, 30000) // Every 30 seconds
  }

  private performHealthCheck(): void {
    // Update server status and emit health events
    for (const [serverId, server] of this.servers.entries()) {
      server.lastHeartbeat = Date.now()
      // In real implementation, this would ping the actual MCP server
    }

    this.emit('healthCheck', {
      timestamp: Date.now(),
      servers: Array.from(this.servers.values()),
      tools: Array.from(this.tools.values()).filter(t => t.enabled).length,
      activeAgents: this.agentPermissions.size
    })
  }

  private persistData(): void {
    try {
      const data = {
        servers: Object.fromEntries(this.servers),
        tools: Object.fromEntries(this.tools),
        agentPermissions: Object.fromEntries(this.agentPermissions),
        sessions: Object.fromEntries(this.sessions),
        callLogs: this.callLogs.slice(-100), // Keep last 100 logs
        version: '1.0.0',
        lastUpdate: Date.now()
      }
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem('mcp_integration_service', JSON.stringify(data))
      }
    } catch (error) {
      console.error('Failed to persist MCP data:', error)
    }
  }

  private loadPersistedData(): void {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return
      
      const stored = localStorage.getItem('mcp_integration_service')
      if (stored) {
        const data = JSON.parse(stored)
        
        if (data.servers) {
          this.servers = new Map(Object.entries(data.servers))
        }
        
        if (data.agentPermissions) {
          this.agentPermissions = new Map(Object.entries(data.agentPermissions))
        }
        
        if (data.sessions) {
          this.sessions = new Map(Object.entries(data.sessions))
        }
        
        if (data.callLogs) {
          this.callLogs = data.callLogs
        }
        
        console.log('Loaded MCP integration data')
      }
    } catch (error) {
      console.error('Failed to load MCP integration data:', error)
    }
  }

  // Public API methods
  getAllTools(): MCPTool[] {
    return Array.from(this.tools.values())
  }

  getAgentPermissions(agentId: string): MCPAgentPermissions | null {
    return this.agentPermissions.get(agentId) || null
  }

  getCallLogs(agentId?: string): MCPCallLog[] {
    return agentId ? this.callLogs.filter(log => log.agentId === agentId) : this.callLogs
  }

  getDashboardStats() {
    const agents = Array.from(this.agentPermissions.keys())
    const tools = Array.from(this.tools.values())
    const sessions = Array.from(this.sessions.values())
    
    return {
      totalAgents: agents.length,
      totalTools: tools.length,
      enabledTools: tools.filter(t => t.enabled).length,
      totalCalls: this.callLogs.length,
      successfulCalls: this.callLogs.filter(l => l.success).length,
      activeSessions: sessions.filter(s => s.status === 'active').length,
      totalSessions: sessions.length,
      avgResponseTime: this.callLogs.length > 0 ? 
        this.callLogs.reduce((sum, log) => sum + log.duration, 0) / this.callLogs.length : 0,
      toolUsage: tools.map(t => ({
        toolId: t.id,
        name: t.name,
        category: t.category,
        usage: t.usage
      })).sort((a, b) => b.usage.totalCalls - a.usage.totalCalls)
    }
  }
}

// Export lazy singleton to prevent circular dependencies
let _mcpIntegrationService: MCPIntegrationService | null = null

export function getMcpIntegrationService(): MCPIntegrationService {
  if (!_mcpIntegrationService) {
    _mcpIntegrationService = new MCPIntegrationService()
  }
  return _mcpIntegrationService
}

// Keep the old export for backward compatibility but make it lazy
// Using a function instead of Proxy to prevent circular dependency issues
export const mcpIntegrationService = {
  get: () => getMcpIntegrationService()
}

export default MCPIntegrationService