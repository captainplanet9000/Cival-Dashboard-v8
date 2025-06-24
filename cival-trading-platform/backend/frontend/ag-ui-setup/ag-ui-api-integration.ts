/**
 * AG-UI API Integration Layer
 * Phase 12: Comprehensive API integration for seamless backend communication
 */

import { AGUIEventBus, AGUIEvent, AllEvents } from './ag-ui-protocol-v2';

export interface APIConfig {
  baseURL: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
  authToken?: string;
  enableCaching: boolean;
  cacheTimeout: number;
}

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: number;
  requestId: string;
}

export interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

export interface APIRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  timeout?: number;
  retries?: number;
  cache?: boolean;
  cacheTimeout?: number;
}

export class AGUIAPIIntegration {
  private eventBus: AGUIEventBus;
  private config: APIConfig;
  private cache: Map<string, CacheEntry> = new Map();
  private activeRequests: Map<string, AbortController> = new Map();

  constructor(eventBus: AGUIEventBus, config: Partial<APIConfig> = {}) {
    this.eventBus = eventBus;
    this.config = {
      baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000,
      enableCaching: true,
      cacheTimeout: 300000, // 5 minutes
      ...config
    };

    this.setupEventHandlers();
    this.startCacheCleanup();
  }

  private setupEventHandlers(): void {
    // Handle API request events
    this.eventBus.subscribe('api.request', async (event) => {
      await this.handleAPIRequest(event.data);
    });

    // Handle batch requests
    this.eventBus.subscribe('api.batch_request', async (event) => {
      await this.handleBatchRequest(event.data);
    });

    // Handle cache invalidation
    this.eventBus.subscribe('api.cache_invalidate', (event) => {
      this.invalidateCache(event.data.pattern);
    });
  }

  private startCacheCleanup(): void {
    setInterval(() => {
      this.cleanExpiredCache();
    }, 60000); // Clean every minute
  }

  private cleanExpiredCache(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (entry.expiresAt < now) {
        this.cache.delete(key);
      }
    }
  }

  // Core API Methods
  public async request<T = any>(
    endpoint: string,
    data?: any,
    options: APIRequestOptions = {}
  ): Promise<APIResponse<T>> {
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const cacheKey = this.generateCacheKey(endpoint, data, options);

    try {
      // Check cache first
      if (options.cache !== false && this.config.enableCaching) {
        const cached = this.getFromCache<T>(cacheKey);
        if (cached) {
          this.eventBus.emit('api.cache_hit', {
            key: cacheKey,
            data: cached
          });
          return {
            success: true,
            data: cached,
            timestamp: Date.now(),
            requestId
          };
        }
      }

      // Emit request start event
      this.eventBus.emit('api.request_started', {
        requestId,
        endpoint,
        method: options.method || 'GET',
        timestamp: Date.now()
      });

      const response = await this.makeRequest<T>(endpoint, data, options, requestId);

      // Cache successful responses
      if (response.success && response.data && options.cache !== false && this.config.enableCaching) {
        this.setCache(cacheKey, response.data, options.cacheTimeout);
      }

      // Emit success event
      this.eventBus.emit('api.request_completed', {
        requestId,
        endpoint,
        success: true,
        timestamp: Date.now()
      });

      return response;

    } catch (error) {
      // Emit error event
      this.eventBus.emit('api.request_failed', {
        requestId,
        endpoint,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      });

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now(),
        requestId
      };
    }
  }

  private async makeRequest<T>(
    endpoint: string,
    data: any,
    options: APIRequestOptions,
    requestId: string
  ): Promise<APIResponse<T>> {
    const controller = new AbortController();
    this.activeRequests.set(requestId, controller);

    const url = `${this.config.baseURL}${endpoint}`;
    const method = options.method || (data ? 'POST' : 'GET');
    const timeout = options.timeout || this.config.timeout;
    const retries = options.retries || this.config.retryAttempts;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Request-ID': requestId,
      ...options.headers
    };

    if (this.config.authToken) {
      headers['Authorization'] = `Bearer ${this.config.authToken}`;
    }

    const fetchOptions: RequestInit = {
      method,
      headers,
      signal: controller.signal
    };

    if (data && method !== 'GET') {
      fetchOptions.body = JSON.stringify(data);
    }

    let lastError: Error;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const timeoutId = setTimeout(() => {
          controller.abort();
        }, timeout);

        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const responseData = await response.json();

        this.activeRequests.delete(requestId);

        return {
          success: true,
          data: responseData,
          timestamp: Date.now(),
          requestId
        };

      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');

        if (attempt < retries) {
          await this.delay(this.config.retryDelay * Math.pow(2, attempt));
        }
      }
    }

    this.activeRequests.delete(requestId);
    throw lastError!;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Specialized API Methods for Trading System

  // Agent Management
  public async getAgents(): Promise<APIResponse<any[]>> {
    return this.request('/api/agents');
  }

  public async createAgent(agentConfig: any): Promise<APIResponse<any>> {
    return this.request('/api/agents', agentConfig, { method: 'POST' });
  }

  public async updateAgent(agentId: string, updates: any): Promise<APIResponse<any>> {
    return this.request(`/api/agents/${agentId}`, updates, { method: 'PUT' });
  }

  public async deleteAgent(agentId: string): Promise<APIResponse<any>> {
    return this.request(`/api/agents/${agentId}`, null, { method: 'DELETE' });
  }

  public async getAgentStatus(agentId: string): Promise<APIResponse<any>> {
    return this.request(`/api/agents/${agentId}/status`, null, { cache: false });
  }

  // Portfolio Management
  public async getPortfolio(): Promise<APIResponse<any>> {
    return this.request('/api/portfolio', null, { cacheTimeout: 30000 });
  }

  public async getPositions(): Promise<APIResponse<any[]>> {
    return this.request('/api/portfolio/positions', null, { cacheTimeout: 10000 });
  }

  public async getTransactionHistory(params?: any): Promise<APIResponse<any[]>> {
    const queryString = params ? '?' + new URLSearchParams(params).toString() : '';
    return this.request(`/api/portfolio/transactions${queryString}`);
  }

  // Market Data
  public async getMarketData(symbol: string): Promise<APIResponse<any>> {
    return this.request(`/api/market-data/${symbol}`, null, { 
      cache: false // Real-time data shouldn't be cached
    });
  }

  public async getPriceHistory(symbol: string, timeframe: string): Promise<APIResponse<any[]>> {
    return this.request(`/api/market-data/${symbol}/history`, { timeframe }, {
      cacheTimeout: 60000 // Cache for 1 minute
    });
  }

  // Goal Management
  public async getGoals(): Promise<APIResponse<any[]>> {
    return this.request('/api/goals');
  }

  public async createGoal(goalData: any): Promise<APIResponse<any>> {
    return this.request('/api/goals', goalData, { method: 'POST' });
  }

  public async updateGoal(goalId: string, updates: any): Promise<APIResponse<any>> {
    return this.request(`/api/goals/${goalId}`, updates, { method: 'PUT' });
  }

  // LLM Integration
  public async sendLLMRequest(requestData: any): Promise<APIResponse<any>> {
    return this.request('/api/llm/request', requestData, { 
      method: 'POST',
      timeout: 60000 // Longer timeout for LLM requests
    });
  }

  public async getLLMAnalytics(): Promise<APIResponse<any>> {
    return this.request('/api/llm/analytics');
  }

  // Risk Management
  public async getRiskMetrics(): Promise<APIResponse<any>> {
    return this.request('/api/risk/metrics', null, { cacheTimeout: 30000 });
  }

  public async updateRiskLimits(limits: any): Promise<APIResponse<any>> {
    return this.request('/api/risk/limits', limits, { method: 'PUT' });
  }

  // Trading Operations
  public async placeOrder(orderData: any): Promise<APIResponse<any>> {
    return this.request('/api/trading/orders', orderData, { 
      method: 'POST',
      cache: false
    });
  }

  public async getOrders(status?: string): Promise<APIResponse<any[]>> {
    const params: Record<string, string> = {};
    if (status) {
      params.status = status;
    }
    const queryString = Object.keys(params).length ? '?' + new URLSearchParams(params).toString() : '';
    return this.request(`/api/trading/orders${queryString}`, null, { cache: false });
  }

  public async cancelOrder(orderId: string): Promise<APIResponse<any>> {
    return this.request(`/api/trading/orders/${orderId}/cancel`, null, { 
      method: 'POST',
      cache: false
    });
  }

  // Batch Operations
  public async batchRequest(requests: Array<{
    id: string;
    endpoint: string;
    data?: any;
    options?: APIRequestOptions;
  }>): Promise<Record<string, APIResponse>> {
    const results: Record<string, APIResponse> = {};

    await Promise.allSettled(
      requests.map(async (req) => {
        try {
          results[req.id] = await this.request(req.endpoint, req.data, req.options);
        } catch (error) {
          results[req.id] = {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
            timestamp: Date.now(),
            requestId: req.id
          };
        }
      })
    );

    return results;
  }

  // Cache Management
  private generateCacheKey(endpoint: string, data: any, options: APIRequestOptions): string {
    const keyData = {
      endpoint,
      data: data || {},
      method: options.method || 'GET'
    };
    return btoa(JSON.stringify(keyData));
  }

  private getFromCache<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (entry && entry.expiresAt > Date.now()) {
      return entry.data;
    }
    if (entry) {
      this.cache.delete(key);
    }
    return null;
  }

  private setCache<T>(key: string, data: T, timeout?: number): void {
    const cacheTimeout = timeout || this.config.cacheTimeout;
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + cacheTimeout
    };
    this.cache.set(key, entry);
  }

  private invalidateCache(pattern?: string): void {
    if (!pattern) {
      this.cache.clear();
      return;
    }

    const regex = new RegExp(pattern);
    for (const [key] of this.cache.entries()) {
      if (regex.test(key)) {
        this.cache.delete(key);
      }
    }
  }

  // Event Handlers
  private async handleAPIRequest(requestData: any): Promise<void> {
    const { endpoint, data, options, responseEventType } = requestData;
    
    const response = await this.request(endpoint, data, options);
    
    if (responseEventType) {
      this.eventBus.emit(responseEventType as keyof AllEvents, response as any);
    }
  }

  private async handleBatchRequest(batchData: any): Promise<void> {
    const { requests, responseEventType } = batchData;
    
    const results = await this.batchRequest(requests);
    
    if (responseEventType) {
      this.eventBus.emit(responseEventType as keyof AllEvents, results as any);
    }
  }

  // Configuration
  public updateConfig(newConfig: Partial<APIConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  public setAuthToken(token: string): void {
    this.config.authToken = token;
  }

  public clearAuthToken(): void {
    delete this.config.authToken;
  }

  // Utilities
  public abortRequest(requestId: string): boolean {
    const controller = this.activeRequests.get(requestId);
    if (controller) {
      controller.abort();
      this.activeRequests.delete(requestId);
      return true;
    }
    return false;
  }

  public abortAllRequests(): void {
    for (const [requestId, controller] of this.activeRequests.entries()) {
      controller.abort();
    }
    this.activeRequests.clear();
  }

  public getCacheStats(): {
    size: number;
    hitRate: number;
    memoryUsage: number;
  } {
    return {
      size: this.cache.size,
      hitRate: 0, // Would need to track hits vs misses
      memoryUsage: JSON.stringify(Array.from(this.cache.entries())).length
    };
  }

  public clearCache(): void {
    this.cache.clear();
  }
}

// Factory function
export function createAPIIntegration(eventBus: AGUIEventBus, config?: Partial<APIConfig>): AGUIAPIIntegration {
  return new AGUIAPIIntegration(eventBus, config);
}

// Default API configuration
export const DEFAULT_API_CONFIG: APIConfig = {
  baseURL: 'http://localhost:8000',
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  enableCaching: true,
  cacheTimeout: 300000
};