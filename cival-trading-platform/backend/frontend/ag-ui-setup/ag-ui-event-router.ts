/**
 * AG-UI Advanced Event Router and Filter System
 * Phase 12: Sophisticated event routing, filtering, and transformation
 */

import { AGUIEventBus, AGUIEvent, AllEvents, AGUIEventHandler, SubscriptionOptions } from './ag-ui-protocol-v2';

export interface RouteConfig {
  id: string;
  name: string;
  source: string | RegExp;
  target: string | string[];
  filter?: EventFilter;
  transform?: EventTransform;
  priority: number;
  enabled: boolean;
  conditions?: RouteCondition[];
}

export interface EventFilter {
  type: 'include' | 'exclude';
  criteria: FilterCriteria;
}

export interface FilterCriteria {
  eventTypes?: string[];
  sourcePatterns?: string[];
  dataMatchers?: Array<{
    path: string;
    operator: 'equals' | 'contains' | 'greater' | 'less' | 'regex';
    value: any;
  }>;
  priority?: {
    min?: 'low' | 'medium' | 'high' | 'critical';
    max?: 'low' | 'medium' | 'high' | 'critical';
  };
  timeWindow?: {
    start?: Date;
    end?: Date;
  };
}

export interface EventTransform {
  type: 'enrich' | 'modify' | 'split' | 'aggregate';
  config: TransformConfig;
}

export interface TransformConfig {
  // For enrich transform
  enrichment?: {
    addFields?: Record<string, any>;
    computedFields?: Array<{
      name: string;
      expression: string;
    }>;
  };
  
  // For modify transform
  modifications?: Array<{
    path: string;
    operation: 'set' | 'delete' | 'rename';
    value?: any;
    newPath?: string;
  }>;
  
  // For split transform
  splitConfig?: {
    splitBy: string;
    targetEventType: string;
  };
  
  // For aggregate transform
  aggregateConfig?: {
    windowMs: number;
    aggregateBy: string[];
    operations: Array<{
      field: string;
      operation: 'sum' | 'avg' | 'count' | 'min' | 'max';
      outputField: string;
    }>;
  };
}

export interface RouteCondition {
  type: 'time' | 'rate' | 'data' | 'system';
  condition: any;
}

export interface EventPipeline {
  id: string;
  name: string;
  routes: string[];
  enabled: boolean;
}

export interface RoutingMetrics {
  totalEvents: number;
  routedEvents: number;
  filteredEvents: number;
  transformedEvents: number;
  errorCount: number;
  routeMetrics: Record<string, {
    processed: number;
    successful: number;
    failed: number;
    avgProcessingTime: number;
  }>;
}

export class AGUIEventRouter {
  private eventBus: AGUIEventBus;
  private routes: Map<string, RouteConfig> = new Map();
  private pipelines: Map<string, EventPipeline> = new Map();
  private metrics: RoutingMetrics;
  private aggregationBuffers: Map<string, Array<AGUIEvent>> = new Map();
  private isEnabled: boolean = true;

  constructor(eventBus: AGUIEventBus) {
    this.eventBus = eventBus;
    this.metrics = {
      totalEvents: 0,
      routedEvents: 0,
      filteredEvents: 0,
      transformedEvents: 0,
      errorCount: 0,
      routeMetrics: {}
    };

    this.setupEventHandlers();
    this.setupDefaultRoutes();
  }

  private setupEventHandlers(): void {
    // Intercept all events for routing
    this.eventBus.addMiddleware((event: AGUIEvent) => {
      if (this.isEnabled) {
        return this.processEvent(event);
      }
      return event;
    });

    // Handle route management events
    this.eventBus.subscribe('router.route.add', (event) => {
      this.addRoute(event.data);
    });

    this.eventBus.subscribe('router.route.remove', (event) => {
      this.removeRoute(event.data.routeId);
    });

    this.eventBus.subscribe('router.route.enable', (event) => {
      this.enableRoute(event.data.routeId);
    });

    this.eventBus.subscribe('router.route.disable', (event) => {
      this.disableRoute(event.data.routeId);
    });
  }

  private setupDefaultRoutes(): void {
    // Default error routing
    this.addRoute({
      id: 'error_to_log',
      name: 'Route Errors to Logging',
      source: /.*\.error$/,
      target: 'system.log',
      priority: 10,
      enabled: true,
      transform: {
        type: 'enrich',
        config: {
          enrichment: {
            addFields: {
              logLevel: 'error',
              category: 'system_error'
            }
          }
        }
      }
    });

    // Performance monitoring route
    this.addRoute({
      id: 'performance_aggregation',
      name: 'Aggregate Performance Metrics',
      source: /.*\.(completed|processed)$/,
      target: 'system.performance_metrics',
      priority: 5,
      enabled: true,
      transform: {
        type: 'aggregate',
        config: {
          aggregateConfig: {
            windowMs: 60000, // 1 minute
            aggregateBy: ['type', 'source'],
            operations: [
              { field: 'timestamp', operation: 'count', outputField: 'event_count' },
              { field: 'processingTime', operation: 'avg', outputField: 'avg_processing_time' }
            ]
          }
        }
      }
    });

    // Critical alert prioritization
    this.addRoute({
      id: 'critical_alert_priority',
      name: 'Prioritize Critical Alerts',
      source: 'alert.created',
      target: ['dashboard.alert', 'notification.critical'],
      priority: 20,
      enabled: true,
      filter: {
        type: 'include',
        criteria: {
          dataMatchers: [
            {
              path: 'data.severity',
              operator: 'equals',
              value: 'critical'
            }
          ]
        }
      }
    });
  }

  private processEvent(event: AGUIEvent): AGUIEvent | null {
    this.metrics.totalEvents++;

    try {
      // Get applicable routes
      const applicableRoutes = this.getApplicableRoutes(event);
      
      if (applicableRoutes.length === 0) {
        return event; // No routing needed
      }

      // Sort routes by priority (higher priority first)
      applicableRoutes.sort((a, b) => b.priority - a.priority);

      let processedEvent = event;
      let wasRouted = false;

      for (const route of applicableRoutes) {
        const startTime = Date.now();

        try {
          // Apply filter if configured
          if (route.filter && !this.applyFilter(processedEvent, route.filter)) {
            this.metrics.filteredEvents++;
            continue;
          }

          // Check conditions
          if (route.conditions && !this.checkConditions(processedEvent, route.conditions)) {
            continue;
          }

          // Apply transformation if configured
          if (route.transform) {
            const transformedEvents = this.applyTransform(processedEvent, route.transform);
            
            if (transformedEvents.length > 0) {
              this.metrics.transformedEvents++;
              
              // Route transformed events
              for (const transformedEvent of transformedEvents) {
                this.routeEvent(transformedEvent, route);
              }
              
              wasRouted = true;
            }
          } else {
            // Route original event
            this.routeEvent(processedEvent, route);
            wasRouted = true;
          }

          // Update route metrics
          this.updateRouteMetrics(route.id, true, Date.now() - startTime);

        } catch (error) {
          console.error(`Error processing route ${route.id}:`, error);
          this.metrics.errorCount++;
          this.updateRouteMetrics(route.id, false, Date.now() - startTime);
        }
      }

      if (wasRouted) {
        this.metrics.routedEvents++;
      }

      return processedEvent;

    } catch (error) {
      console.error('Error in event router:', error);
      this.metrics.errorCount++;
      return event;
    }
  }

  private getApplicableRoutes(event: AGUIEvent): RouteConfig[] {
    const routes: RouteConfig[] = [];

    for (const route of this.routes.values()) {
      if (!route.enabled) continue;

      if (this.matchesSource(event, route.source)) {
        routes.push(route);
      }
    }

    return routes;
  }

  private matchesSource(event: AGUIEvent, source: string | RegExp): boolean {
    if (typeof source === 'string') {
      return event.type === source || event.source === source;
    } else {
      return source.test(event.type) || source.test(event.source || '');
    }
  }

  private applyFilter(event: AGUIEvent, filter: EventFilter): boolean {
    const criteria = filter.criteria;
    let matches = true;

    // Check event types
    if (criteria.eventTypes) {
      const typeMatches = criteria.eventTypes.includes(event.type);
      matches = matches && typeMatches;
    }

    // Check source patterns
    if (criteria.sourcePatterns) {
      const sourceMatches = criteria.sourcePatterns.some(pattern => 
        event.source?.includes(pattern)
      );
      matches = matches && sourceMatches;
    }

    // Check data matchers
    if (criteria.dataMatchers) {
      for (const matcher of criteria.dataMatchers) {
        const dataMatches = this.evaluateDataMatcher(event.data, matcher);
        matches = matches && dataMatches;
      }
    }

    // Check priority
    if (criteria.priority) {
      const priorityMatches = this.evaluatePriorityFilter(event.priority, criteria.priority);
      matches = matches && priorityMatches;
    }

    // Check time window
    if (criteria.timeWindow) {
      const timeMatches = this.evaluateTimeWindow(event.timestamp, criteria.timeWindow);
      matches = matches && timeMatches;
    }

    return filter.type === 'include' ? matches : !matches;
  }

  private evaluateDataMatcher(data: any, matcher: any): boolean {
    const value = this.getNestedValue(data, matcher.path);
    
    switch (matcher.operator) {
      case 'equals':
        return value === matcher.value;
      case 'contains':
        return String(value).includes(String(matcher.value));
      case 'greater':
        return Number(value) > Number(matcher.value);
      case 'less':
        return Number(value) < Number(matcher.value);
      case 'regex':
        return new RegExp(matcher.value).test(String(value));
      default:
        return false;
    }
  }

  private evaluatePriorityFilter(eventPriority: string, priorityFilter: any): boolean {
    const priorityOrder = ['low', 'medium', 'high', 'critical'];
    const eventIndex = priorityOrder.indexOf(eventPriority);
    
    let matches = true;
    
    if (priorityFilter.min) {
      const minIndex = priorityOrder.indexOf(priorityFilter.min);
      matches = matches && eventIndex >= minIndex;
    }
    
    if (priorityFilter.max) {
      const maxIndex = priorityOrder.indexOf(priorityFilter.max);
      matches = matches && eventIndex <= maxIndex;
    }
    
    return matches;
  }

  private evaluateTimeWindow(timestamp: number, timeWindow: any): boolean {
    const eventTime = new Date(timestamp);
    
    if (timeWindow.start && eventTime < timeWindow.start) {
      return false;
    }
    
    if (timeWindow.end && eventTime > timeWindow.end) {
      return false;
    }
    
    return true;
  }

  private checkConditions(event: AGUIEvent, conditions: RouteCondition[]): boolean {
    return conditions.every(condition => {
      switch (condition.type) {
        case 'time':
          return this.checkTimeCondition(event, condition.condition);
        case 'rate':
          return this.checkRateCondition(event, condition.condition);
        case 'data':
          return this.checkDataCondition(event, condition.condition);
        case 'system':
          return this.checkSystemCondition(event, condition.condition);
        default:
          return true;
      }
    });
  }

  private checkTimeCondition(event: AGUIEvent, condition: any): boolean {
    // Implement time-based conditions (e.g., business hours, specific times)
    return true; // Placeholder
  }

  private checkRateCondition(event: AGUIEvent, condition: any): boolean {
    // Implement rate limiting conditions
    return true; // Placeholder
  }

  private checkDataCondition(event: AGUIEvent, condition: any): boolean {
    // Implement data-based conditions
    return true; // Placeholder
  }

  private checkSystemCondition(event: AGUIEvent, condition: any): boolean {
    // Implement system-state conditions
    return true; // Placeholder
  }

  private applyTransform(event: AGUIEvent, transform: EventTransform): AGUIEvent[] {
    switch (transform.type) {
      case 'enrich':
        return [this.enrichEvent(event, transform.config)];
      case 'modify':
        return [this.modifyEvent(event, transform.config)];
      case 'split':
        return this.splitEvent(event, transform.config);
      case 'aggregate':
        return this.aggregateEvent(event, transform.config);
      default:
        return [event];
    }
  }

  private enrichEvent(event: AGUIEvent, config: TransformConfig): AGUIEvent {
    const enrichedEvent = { ...event };
    
    if (config.enrichment?.addFields) {
      enrichedEvent.data = {
        ...enrichedEvent.data,
        ...config.enrichment.addFields
      };
    }
    
    if (config.enrichment?.computedFields) {
      for (const field of config.enrichment.computedFields) {
        try {
          // Simple expression evaluation (in production, use a proper expression engine)
          const value = this.evaluateExpression(field.expression, event);
          enrichedEvent.data[field.name] = value;
        } catch (error) {
          console.error(`Error computing field ${field.name}:`, error);
        }
      }
    }
    
    return enrichedEvent;
  }

  private modifyEvent(event: AGUIEvent, config: TransformConfig): AGUIEvent {
    const modifiedEvent = { ...event };
    
    if (config.modifications) {
      for (const mod of config.modifications) {
        switch (mod.operation) {
          case 'set':
            this.setNestedValue(modifiedEvent, mod.path, mod.value);
            break;
          case 'delete':
            this.deleteNestedValue(modifiedEvent, mod.path);
            break;
          case 'rename':
            if (mod.newPath) {
              const value = this.getNestedValue(modifiedEvent, mod.path);
              this.setNestedValue(modifiedEvent, mod.newPath, value);
              this.deleteNestedValue(modifiedEvent, mod.path);
            }
            break;
        }
      }
    }
    
    return modifiedEvent;
  }

  private splitEvent(event: AGUIEvent, config: TransformConfig): AGUIEvent[] {
    if (!config.splitConfig) return [event];
    
    const splitBy = config.splitConfig.splitBy;
    const targetType = config.splitConfig.targetEventType;
    const splitValue = this.getNestedValue(event.data, splitBy);
    
    if (Array.isArray(splitValue)) {
      return splitValue.map((item, index) => ({
        ...event,
        id: `${event.id}_split_${index}`,
        type: targetType,
        data: {
          ...event.data,
          [splitBy]: item,
          splitIndex: index
        }
      }));
    }
    
    return [event];
  }

  private aggregateEvent(event: AGUIEvent, config: TransformConfig): AGUIEvent[] {
    if (!config.aggregateConfig) return [event];
    
    const aggregateConfig = config.aggregateConfig;
    const bufferKey = this.generateAggregateKey(event, aggregateConfig.aggregateBy);
    
    // Add to buffer
    if (!this.aggregationBuffers.has(bufferKey)) {
      this.aggregationBuffers.set(bufferKey, []);
    }
    
    const buffer = this.aggregationBuffers.get(bufferKey)!;
    buffer.push(event);
    
    // Check if window is complete
    const windowStart = Date.now() - aggregateConfig.windowMs;
    const eventsInWindow = buffer.filter(e => e.timestamp >= windowStart);
    
    if (eventsInWindow.length > 0 && Date.now() % aggregateConfig.windowMs < 1000) {
      // Generate aggregated event
      const aggregatedEvent = this.generateAggregatedEvent(eventsInWindow, aggregateConfig);
      
      // Clear buffer
      this.aggregationBuffers.set(bufferKey, []);
      
      return [aggregatedEvent];
    }
    
    return []; // No event to emit yet
  }

  private generateAggregatedEvent(events: AGUIEvent[], config: any): AGUIEvent {
    const result: any = {
      aggregatedFrom: events.length,
      windowStart: Math.min(...events.map(e => e.timestamp)),
      windowEnd: Math.max(...events.map(e => e.timestamp))
    };
    
    for (const operation of config.operations) {
      const values = events.map(e => this.getNestedValue(e.data, operation.field))
        .filter(v => v !== undefined && v !== null);
      
      switch (operation.operation) {
        case 'sum':
          result[operation.outputField] = values.reduce((sum, val) => sum + Number(val), 0);
          break;
        case 'avg':
          result[operation.outputField] = values.reduce((sum, val) => sum + Number(val), 0) / values.length;
          break;
        case 'count':
          result[operation.outputField] = values.length;
          break;
        case 'min':
          result[operation.outputField] = Math.min(...values.map(Number));
          break;
        case 'max':
          result[operation.outputField] = Math.max(...values.map(Number));
          break;
      }
    }
    
    return {
      id: `aggregated_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'system.aggregated_metrics',
      data: result,
      timestamp: Date.now(),
      source: 'event_router',
      priority: 'medium'
    };
  }

  private generateAggregateKey(event: AGUIEvent, aggregateBy: string[]): string {
    const keyParts = aggregateBy.map(field => this.getNestedValue(event, field));
    return keyParts.join('|');
  }

  private routeEvent(event: AGUIEvent, route: RouteConfig): void {
    const targets = Array.isArray(route.target) ? route.target : [route.target];
    
    for (const target of targets) {
      // Create a routed event
      const routedEvent = {
        ...event,
        metadata: {
          ...event.metadata,
          routedBy: route.id,
          routedAt: Date.now()
        }
      };
      
      // Emit to target
      this.eventBus.emit(target as keyof AllEvents, routedEvent.data);
    }
  }

  private updateRouteMetrics(routeId: string, success: boolean, processingTime: number): void {
    if (!this.metrics.routeMetrics[routeId]) {
      this.metrics.routeMetrics[routeId] = {
        processed: 0,
        successful: 0,
        failed: 0,
        avgProcessingTime: 0
      };
    }
    
    const metrics = this.metrics.routeMetrics[routeId];
    metrics.processed++;
    
    if (success) {
      metrics.successful++;
    } else {
      metrics.failed++;
    }
    
    // Update average processing time
    metrics.avgProcessingTime = (metrics.avgProcessingTime * (metrics.processed - 1) + processingTime) / metrics.processed;
  }

  // Utility methods
  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  private setNestedValue(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    const target = keys.reduce((current, key) => {
      if (!current[key]) current[key] = {};
      return current[key];
    }, obj);
    target[lastKey] = value;
  }

  private deleteNestedValue(obj: any, path: string): void {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    const target = keys.reduce((current, key) => current?.[key], obj);
    if (target) {
      delete target[lastKey];
    }
  }

  private evaluateExpression(expression: string, event: AGUIEvent): any {
    // Simple expression evaluation - in production, use a proper expression engine
    try {
      // Replace event references with actual values
      const processedExpression = expression
        .replace(/event\.(\w+)/g, (match, prop) => JSON.stringify(event[prop as keyof AGUIEvent]))
        .replace(/data\.(\w+)/g, (match, prop) => JSON.stringify(event.data[prop]));
      
      // Use Function constructor for safe evaluation (in production, use a sandboxed evaluator)
      return new Function(`return ${processedExpression}`)();
    } catch (error) {
      console.error('Expression evaluation error:', error);
      return undefined;
    }
  }

  // Public API
  public addRoute(routeConfig: RouteConfig): void {
    this.routes.set(routeConfig.id, routeConfig);
    
    // Initialize metrics
    this.metrics.routeMetrics[routeConfig.id] = {
      processed: 0,
      successful: 0,
      failed: 0,
      avgProcessingTime: 0
    };
  }

  public removeRoute(routeId: string): boolean {
    const removed = this.routes.delete(routeId);
    if (removed) {
      delete this.metrics.routeMetrics[routeId];
    }
    return removed;
  }

  public enableRoute(routeId: string): boolean {
    const route = this.routes.get(routeId);
    if (route) {
      route.enabled = true;
      return true;
    }
    return false;
  }

  public disableRoute(routeId: string): boolean {
    const route = this.routes.get(routeId);
    if (route) {
      route.enabled = false;
      return true;
    }
    return false;
  }

  public getRoutes(): RouteConfig[] {
    return Array.from(this.routes.values());
  }

  public getRoute(routeId: string): RouteConfig | undefined {
    return this.routes.get(routeId);
  }

  public getMetrics(): RoutingMetrics {
    return { ...this.metrics };
  }

  public clearMetrics(): void {
    this.metrics = {
      totalEvents: 0,
      routedEvents: 0,
      filteredEvents: 0,
      transformedEvents: 0,
      errorCount: 0,
      routeMetrics: {}
    };
  }

  public enable(): void {
    this.isEnabled = true;
  }

  public disable(): void {
    this.isEnabled = false;
  }

  public isRouterEnabled(): boolean {
    return this.isEnabled;
  }
}

// Factory function
export function createEventRouter(eventBus: AGUIEventBus): AGUIEventRouter {
  return new AGUIEventRouter(eventBus);
}