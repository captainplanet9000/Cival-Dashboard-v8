/**
 * AG-UI Protocol Event Transport Layer
 * Phase 8: WebSocket/SSE transport for real-time communication
 */

import { io, Socket } from 'socket.io-client';
import { AllEvents } from './ag-ui-protocol-v2';
import { agUIConfig } from './ag-ui-config';

export type EventCallback<T = any> = (data: T) => void;
export type EventType = string;

export interface EventSubscription {
  id: string;
  eventType: EventType;
  callback: EventCallback;
  options?: SubscriptionOptions;
}

export interface SubscriptionOptions {
  priority?: 'high' | 'medium' | 'low';
  once?: boolean;
  filter?: (data: any) => boolean;
  transform?: (data: any) => any;
}

export interface EventTransportMetrics {
  connected: boolean;
  connectionTime?: Date;
  lastHeartbeat?: Date;
  eventsReceived: number;
  eventsSent: number;
  errors: number;
  reconnectCount: number;
  averageLatency: number;
  queueSize: number;
}

export class EventTransportLayer {
  private socket: Socket | null = null;
  private subscriptions = new Map<string, EventSubscription>();
  private eventQueue: Array<{ type: EventType; data: any; timestamp: Date }> = [];
  private metrics: EventTransportMetrics = {
    connected: false,
    eventsReceived: 0,
    eventsSent: 0,
    errors: 0,
    reconnectCount: 0,
    averageLatency: 0,
    queueSize: 0
  };
  
  private reconnectTimer?: NodeJS.Timeout;
  private heartbeatTimer?: NodeJS.Timeout;
  private latencyTracker = new Map<string, number>();
  
  constructor() {
    this.initialize();
  }
  
  /**
   * Initialize the event transport layer
   */
  private initialize(): void {
    try {
      const config = agUIConfig.connection.websocket;
      
      this.socket = io(config.url, {
        transports: ['websocket'],
        reconnection: config.reconnect,
        reconnectionAttempts: config.maxReconnectAttempts,
        reconnectionDelay: config.reconnectInterval,
        timeout: 10000,
        auth: {
          token: this.getAuthToken()
        }
      });
      
      this.setupEventHandlers();
      this.startHeartbeat();
      
      console.log('🚀 Event transport layer initialized');
    } catch (error) {
      console.error('❌ Failed to initialize event transport:', error);
      this.handleError(error as Error);
    }
  }
  
  /**
   * Set up WebSocket event handlers
   */
  private setupEventHandlers(): void {
    if (!this.socket) return;
    
    // Connection events
    this.socket.on('connect', () => {
      this.metrics.connected = true;
      this.metrics.connectionTime = new Date();
      console.log('🟢 WebSocket connected to trading platform');
      
      // Flush queued events
      this.flushEventQueue();
      
      // Notify AG-UI config
      agUIConfig.events.onConnect?.();
    });
    
    this.socket.on('disconnect', (reason) => {
      this.metrics.connected = false;
      console.log('🔴 WebSocket disconnected:', reason);
      
      // Notify AG-UI config
      agUIConfig.events.onDisconnect?.();
      
      // Attempt reconnection if needed
      if (reason === 'io server disconnect') {
        this.scheduleReconnect();
      }
    });
    
    this.socket.on('reconnect', (attemptNumber) => {
      this.metrics.reconnectCount++;
      console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
      
      // Notify AG-UI config
      agUIConfig.events.onReconnect?.();
    });
    
    this.socket.on('connect_error', (error) => {
      this.metrics.errors++;
      console.error('❌ WebSocket connection error:', error);
      this.handleError(error);
    });
    
    // Heartbeat/pong response
    this.socket.on('pong', () => {
      this.metrics.lastHeartbeat = new Date();
    });
    
    // Trading platform events
    this.setupTradingEventHandlers();
  }
  
  /**
   * Set up handlers for trading platform specific events
   */
  private setupTradingEventHandlers(): void {
    if (!this.socket) return;
    
    // Goal management events
    this.socket.on('goal.created', (data) => this.handleIncomingEvent('goal.created', data));
    this.socket.on('goal.analyzed', (data) => this.handleIncomingEvent('goal.analyzed', data));
    this.socket.on('goal.progress_updated', (data) => this.handleIncomingEvent('goal.progress_updated', data));
    this.socket.on('goal.completed', (data) => this.handleIncomingEvent('goal.completed', data));
    this.socket.on('goal.optimization_suggested', (data) => this.handleIncomingEvent('goal.optimization_suggested', data));
    this.socket.on('goal.decomposed', (data) => this.handleIncomingEvent('goal.decomposed', data));
    this.socket.on('goal.cancelled', (data) => this.handleIncomingEvent('goal.cancelled', data));
    
    // Analytics events
    this.socket.on('analytics.report_generated', (data) => this.handleIncomingEvent('analytics.report_generated', data));
    this.socket.on('prediction.completed', (data) => this.handleIncomingEvent('prediction.completed', data));
    this.socket.on('pattern.identified', (data) => this.handleIncomingEvent('pattern.identified', data));
    this.socket.on('recommendation.created', (data) => this.handleIncomingEvent('recommendation.created', data));
    
    // System events
    this.socket.on('system.health_check', (data) => this.handleIncomingEvent('system.health_check', data));
    this.socket.on('system.error', (data) => this.handleIncomingEvent('system.error', data));
    this.socket.on('system.notification', (data) => this.handleIncomingEvent('system.notification', data));
    
    // Future event types (wallet, agent, trading)
    this.socket.on('wallet.created', (data) => this.handleIncomingEvent('wallet.created', data));
    this.socket.on('wallet.updated', (data) => this.handleIncomingEvent('wallet.updated', data));
    this.socket.on('wallet.balance_changed', (data) => this.handleIncomingEvent('wallet.balance_changed', data));
    this.socket.on('wallet.transaction', (data) => this.handleIncomingEvent('wallet.transaction', data));
    
    this.socket.on('agent.decision', (data) => this.handleIncomingEvent('agent.decision', data));
    this.socket.on('agent.communication', (data) => this.handleIncomingEvent('agent.communication', data));
    this.socket.on('agent.performance_update', (data) => this.handleIncomingEvent('agent.performance_update', data));
    this.socket.on('agent.strategy_change', (data) => this.handleIncomingEvent('agent.strategy_change', data));
    
    this.socket.on('trade.executed', (data) => this.handleIncomingEvent('trade.executed', data));
    this.socket.on('trade.signal_generated', (data) => this.handleIncomingEvent('trade.signal_generated', data));
    this.socket.on('trade.risk_alert', (data) => this.handleIncomingEvent('trade.risk_alert', data));
    this.socket.on('trade.position_update', (data) => this.handleIncomingEvent('trade.position_update', data));
  }
  
  /**
   * Handle incoming events from the trading platform
   */
  private handleIncomingEvent(eventType: EventType, data: any): void {
    try {
      this.metrics.eventsReceived++;
      
      // Calculate latency if timestamp is available
      if (data.timestamp) {
        const latency = Date.now() - new Date(data.timestamp).getTime();
        this.updateLatencyMetrics(latency);
      }
      
      // Find all subscriptions for this event type
      const relevantSubscriptions = Array.from(this.subscriptions.values())
        .filter(sub => sub.eventType === eventType);
      
      for (const subscription of relevantSubscriptions) {
        try {
          // Apply filter if specified
          if (subscription.options?.filter && !subscription.options.filter(data)) {
            continue;
          }
          
          // Apply transformation if specified
          let processedData = data;
          if (subscription.options?.transform) {
            processedData = subscription.options.transform(data);
          }
          
          // Call the subscription callback
          subscription.callback(processedData);
          
          // Remove one-time subscriptions
          if (subscription.options?.once) {
            this.subscriptions.delete(subscription.id);
          }
          
        } catch (error) {
          console.error(`❌ Error in event subscription ${subscription.id}:`, error);
          this.metrics.errors++;
        }
      }
      
      // Log high-priority events
      if (this.getEventPriority(eventType) === 'high') {
        console.log(`🔔 High-priority event received: ${eventType}`, data);
      }
      
    } catch (error) {
      console.error('❌ Error handling incoming event:', error);
      this.metrics.errors++;
    }
  }
  
  /**
   * Subscribe to events
   */
  public subscribe<T = any>(
    eventType: EventType,
    callback: EventCallback<T>,
    options?: SubscriptionOptions
  ): string {
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const subscription: EventSubscription = {
      id: subscriptionId,
      eventType,
      callback: callback as EventCallback,
      options
    };
    
    this.subscriptions.set(subscriptionId, subscription);
    
    console.log(`📡 Subscribed to ${eventType} with ID: ${subscriptionId}`);
    
    return subscriptionId;
  }
  
  /**
   * Unsubscribe from events
   */
  public unsubscribe(subscriptionId: string): boolean {
    const removed = this.subscriptions.delete(subscriptionId);
    
    if (removed) {
      console.log(`📡 Unsubscribed from event with ID: ${subscriptionId}`);
    }
    
    return removed;
  }
  
  /**
   * Emit events to the trading platform
   */
  public emit(eventType: EventType, data: any): void {
    try {
      if (!this.socket || !this.metrics.connected) {
        // Queue event if not connected
        this.queueEvent(eventType, data);
        return;
      }
      
      // Add timestamp for latency tracking
      const eventData = {
        ...data,
        timestamp: new Date().toISOString(),
        clientId: this.getClientId()
      };
      
      this.socket.emit(eventType, eventData);
      this.metrics.eventsSent++;
      
      console.log(`📤 Emitted event: ${eventType}`);
      
    } catch (error) {
      console.error('❌ Error emitting event:', error);
      this.metrics.errors++;
      
      // Queue event for retry
      this.queueEvent(eventType, data);
    }
  }
  
  /**
   * Queue events when disconnected
   */
  private queueEvent(eventType: EventType, data: any): void {
    const queuedEvent = {
      type: eventType,
      data,
      timestamp: new Date()
    };
    
    this.eventQueue.push(queuedEvent);
    this.metrics.queueSize = this.eventQueue.length;
    
    // Limit queue size
    const maxQueueSize = agUIConfig.transport.buffer.maxSize || 1000;
    if (this.eventQueue.length > maxQueueSize) {
      this.eventQueue.shift(); // Remove oldest event
    }
    
    console.log(`📦 Queued event: ${eventType} (queue size: ${this.eventQueue.length})`);
  }
  
  /**
   * Flush queued events when reconnected
   */
  private flushEventQueue(): void {
    if (!agUIConfig.transport.buffer.flushOnReconnect) {
      return;
    }
    
    console.log(`📤 Flushing ${this.eventQueue.length} queued events`);
    
    const eventsToFlush = [...this.eventQueue];
    this.eventQueue = [];
    this.metrics.queueSize = 0;
    
    for (const event of eventsToFlush) {
      // Add age information
      const age = Date.now() - event.timestamp.getTime();
      const eventData = {
        ...event.data,
        _queued: true,
        _age: age
      };
      
      this.emit(event.type, eventData);
    }
  }
  
  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    const heartbeatInterval = agUIConfig.connection.websocket.heartbeat?.interval || 30000;
    
    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.metrics.connected) {
        this.socket.emit('ping');
      }
    }, heartbeatInterval);
  }
  
  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    const reconnectInterval = agUIConfig.connection.websocket.reconnectInterval || 5000;
    
    this.reconnectTimer = setTimeout(() => {
      console.log('🔄 Attempting to reconnect...');
      this.socket?.connect();
    }, reconnectInterval);
  }
  
  /**
   * Handle transport errors
   */
  private handleError(error: Error): void {
    this.metrics.errors++;
    
    console.error('❌ Event transport error:', error);
    
    // Notify AG-UI config
    agUIConfig.events.onError?.(error);
    
    // Emit system error event for UI notification
    if (this.metrics.connected) {
      this.emit('system.error', {
        service: 'event_transport',
        error_type: error.name,
        message: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  /**
   * Update latency metrics
   */
  private updateLatencyMetrics(latency: number): void {
    const trackingId = Date.now().toString();
    this.latencyTracker.set(trackingId, latency);
    
    // Keep only last 100 latency measurements
    if (this.latencyTracker.size > 100) {
      const oldestKey = Array.from(this.latencyTracker.keys())[0];
      this.latencyTracker.delete(oldestKey);
    }
    
    // Calculate average latency
    const latencies = Array.from(this.latencyTracker.values());
    this.metrics.averageLatency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length;
  }
  
  /**
   * Get event priority
   */
  private getEventPriority(eventType: EventType): 'high' | 'medium' | 'low' {
    const highPriorityEvents = [
      'goal.completed',
      'trade.executed',
      'system.error',
      'agent.decision',
      'trade.risk_alert'
    ];
    
    const mediumPriorityEvents = [
      'goal.created',
      'goal.progress_updated',
      'wallet.transaction',
      'prediction.completed',
      'agent.performance_update'
    ];
    
    if (highPriorityEvents.includes(eventType as any)) {
      return 'high';
    } else if (mediumPriorityEvents.includes(eventType as any)) {
      return 'medium';
    } else {
      return 'low';
    }
  }
  
  /**
   * Get authentication token
   */
  private getAuthToken(): string | undefined {
    try {
      return localStorage.getItem(agUIConfig.connection.auth?.tokenKey || 'authToken') || undefined;
    } catch (error) {
      console.warn('⚠️ Could not retrieve auth token:', error);
      return undefined;
    }
  }
  
  /**
   * Get client ID for event tracking
   */
  private getClientId(): string {
    try {
      let clientId = localStorage.getItem('clientId');
      if (!clientId) {
        clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('clientId', clientId);
      }
      return clientId;
    } catch (error) {
      return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
  }
  
  /**
   * Get transport metrics
   */
  public getMetrics(): EventTransportMetrics {
    return { ...this.metrics };
  }
  
  /**
   * Get connection status
   */
  public isConnected(): boolean {
    return this.metrics.connected;
  }
  
  /**
   * Get subscription count
   */
  public getSubscriptionCount(): number {
    return this.subscriptions.size;
  }
  
  /**
   * Force reconnection
   */
  public reconnect(): void {
    console.log('🔄 Forcing reconnection...');
    this.socket?.disconnect();
    this.socket?.connect();
  }
  
  /**
   * Cleanup resources
   */
  public destroy(): void {
    console.log('🗑️ Destroying event transport layer');
    
    // Clear timers
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }
    
    // Clear subscriptions
    this.subscriptions.clear();
    
    // Clear queue
    this.eventQueue = [];
    
    // Disconnect socket
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    
    // Reset metrics
    this.metrics = {
      connected: false,
      eventsReceived: 0,
      eventsSent: 0,
      errors: 0,
      reconnectCount: 0,
      averageLatency: 0,
      queueSize: 0
    };
  }
}

// Create singleton instance
export const eventTransport = new EventTransportLayer();

// Export convenience functions
export const subscribe = eventTransport.subscribe.bind(eventTransport);
export const unsubscribe = eventTransport.unsubscribe.bind(eventTransport);
export const emit = eventTransport.emit.bind(eventTransport);
export const getMetrics = eventTransport.getMetrics.bind(eventTransport);
export const isConnected = eventTransport.isConnected.bind(eventTransport);

export default eventTransport;