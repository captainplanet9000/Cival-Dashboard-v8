/**
 * AG-UI Monitoring and Health Check System
 * Phase 12: Production monitoring, alerting, and performance tracking
 */

import { EventEmitter } from 'events';
import { AGUIEvent, AGUIEventBus, PerformanceMetrics } from './ag-ui-protocol-v2';

export interface MonitoringConfig {
  enableHealthChecks: boolean;
  healthCheckInterval: number;
  enablePerformanceTracking: boolean;
  enableAlerts: boolean;
  alertThresholds: AlertThresholds;
  enableMetricsCollection: boolean;
  metricsRetentionDays: number;
}

export interface AlertThresholds {
  errorRate: number;
  latencyMs: number;
  connectionUptime: number;
  memoryUsageMB: number;
  queueSize: number;
  failedEventRate: number;
}

export interface Alert {
  id: string;
  type: 'performance' | 'error' | 'connection' | 'resource' | 'security';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  timestamp: number;
  resolved: boolean;
  resolvedAt?: number;
  metadata: Record<string, any>;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical';
  components: {
    eventBus: 'healthy' | 'degraded' | 'critical';
    transport: 'healthy' | 'degraded' | 'critical';
    subscribers: 'healthy' | 'degraded' | 'critical';
    performance: 'healthy' | 'degraded' | 'critical';
  };
  metrics: PerformanceMetrics;
  alerts: Alert[];
  uptime: number;
  lastHealthCheck: number;
}

export interface MetricsSnapshot {
  timestamp: number;
  eventThroughput: number;
  activeSubscriptions: number;
  connectionStatus: string;
  memoryUsage: number;
  errorRate: number;
  averageLatency: number;
  queueSize: number;
}

export class AGUIMonitor extends EventEmitter {
  private eventBus: AGUIEventBus;
  private config: MonitoringConfig;
  private alerts: Map<string, Alert> = new Map();
  private metricsHistory: MetricsSnapshot[] = [];
  private startTime: number = Date.now();
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private metricsTimer: NodeJS.Timeout | null = null;

  constructor(eventBus: AGUIEventBus, config: Partial<MonitoringConfig> = {}) {
    super();
    this.eventBus = eventBus;
    this.config = {
      enableHealthChecks: true,
      healthCheckInterval: 30000, // 30 seconds
      enablePerformanceTracking: true,
      enableAlerts: true,
      alertThresholds: {
        errorRate: 0.05, // 5%
        latencyMs: 5000, // 5 seconds
        connectionUptime: 0.95, // 95%
        memoryUsageMB: 500, // 500MB
        queueSize: 1000,
        failedEventRate: 0.1 // 10%
      },
      enableMetricsCollection: true,
      metricsRetentionDays: 7,
      ...config
    };

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    // Monitor event processing
    this.eventBus.addMiddleware((event: AGUIEvent) => {
      if (this.config.enablePerformanceTracking) {
        this.trackEventProcessing(event);
      }
      return event;
    });

    // Monitor connection events
    this.eventBus.subscribe('connection.established', (event) => {
      this.handleConnectionEvent('established', event.data);
    });

    this.eventBus.subscribe('connection.lost', (event) => {
      this.handleConnectionEvent('lost', event.data);
      this.createAlert('connection', 'medium', 'Connection Lost', 
        'AG-UI transport connection has been lost', event.data);
    });

    this.eventBus.subscribe('connection.reconnected', (event) => {
      this.handleConnectionEvent('reconnected', event.data);
      this.resolveAlertsOfType('connection');
    });

    // Monitor system events
    this.eventBus.subscribe('system.error', (event) => {
      this.handleSystemError(event.data);
    });
  }

  public start(): void {
    if (this.config.enableHealthChecks) {
      this.startHealthChecks();
    }

    if (this.config.enableMetricsCollection) {
      this.startMetricsCollection();
    }

    this.emit('monitor.started', { timestamp: Date.now() });
  }

  public stop(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }

    if (this.metricsTimer) {
      clearInterval(this.metricsTimer);
      this.metricsTimer = null;
    }

    this.emit('monitor.stopped', { timestamp: Date.now() });
  }

  private startHealthChecks(): void {
    this.healthCheckTimer = setInterval(() => {
      this.performHealthCheck();
    }, this.config.healthCheckInterval);
  }

  private startMetricsCollection(): void {
    this.metricsTimer = setInterval(() => {
      this.collectMetrics();
    }, 10000); // Collect metrics every 10 seconds
  }

  private async performHealthCheck(): Promise<SystemHealth> {
    const metrics = this.eventBus.getTransportMetrics();
    const subscriptionStats = this.eventBus.getSubscriptionStats();
    
    const health: SystemHealth = {
      overall: 'healthy',
      components: {
        eventBus: this.checkEventBusHealth(metrics),
        transport: this.checkTransportHealth(metrics),
        subscribers: this.checkSubscribersHealth(subscriptionStats),
        performance: this.checkPerformanceHealth(metrics)
      },
      metrics,
      alerts: Array.from(this.alerts.values()).filter(alert => !alert.resolved),
      uptime: Date.now() - this.startTime,
      lastHealthCheck: Date.now()
    };

    // Determine overall health
    const componentStates = Object.values(health.components);
    if (componentStates.includes('critical')) {
      health.overall = 'critical';
    } else if (componentStates.includes('degraded')) {
      health.overall = 'degraded';
    }

    // Check thresholds and create alerts
    this.checkThresholds(metrics);

    // Emit health check event
    this.eventBus.emit('system.health_check', { 
      status: health.overall, 
      metrics: health.metrics 
    });
    this.emit('health.check', health);

    return health;
  }

  private checkEventBusHealth(metrics: PerformanceMetrics): 'healthy' | 'degraded' | 'critical' {
    if (metrics.errorRate > this.config.alertThresholds.errorRate * 2) {
      return 'critical';
    }
    if (metrics.errorRate > this.config.alertThresholds.errorRate) {
      return 'degraded';
    }
    return 'healthy';
  }

  private checkTransportHealth(metrics: PerformanceMetrics): 'healthy' | 'degraded' | 'critical' {
    if (metrics.connectionUptime < this.config.alertThresholds.connectionUptime * 0.8) {
      return 'critical';
    }
    if (metrics.connectionUptime < this.config.alertThresholds.connectionUptime) {
      return 'degraded';
    }
    return 'healthy';
  }

  private checkSubscribersHealth(stats: { total: number; byEventType: Record<string, number> }): 'healthy' | 'degraded' | 'critical' {
    if (stats.total === 0) {
      return 'critical';
    }
    if (stats.total < 5) {
      return 'degraded';
    }
    return 'healthy';
  }

  private checkPerformanceHealth(metrics: PerformanceMetrics): 'healthy' | 'degraded' | 'critical' {
    if (metrics.averageLatency > this.config.alertThresholds.latencyMs * 2) {
      return 'critical';
    }
    if (metrics.averageLatency > this.config.alertThresholds.latencyMs) {
      return 'degraded';
    }
    return 'healthy';
  }

  private checkThresholds(metrics: PerformanceMetrics): void {
    const thresholds = this.config.alertThresholds;

    // Error rate threshold
    if (metrics.errorRate > thresholds.errorRate) {
      this.createAlert('error', 'high', 'High Error Rate', 
        `Error rate ${(metrics.errorRate * 100).toFixed(2)}% exceeds threshold ${(thresholds.errorRate * 100).toFixed(2)}%`,
        { errorRate: metrics.errorRate, threshold: thresholds.errorRate });
    }

    // Latency threshold
    if (metrics.averageLatency > thresholds.latencyMs) {
      this.createAlert('performance', 'medium', 'High Latency', 
        `Average latency ${metrics.averageLatency}ms exceeds threshold ${thresholds.latencyMs}ms`,
        { latency: metrics.averageLatency, threshold: thresholds.latencyMs });
    }

    // Memory usage threshold
    if (metrics.memoryUsage > thresholds.memoryUsageMB) {
      this.createAlert('resource', 'medium', 'High Memory Usage', 
        `Memory usage ${metrics.memoryUsage}MB exceeds threshold ${thresholds.memoryUsageMB}MB`,
        { memoryUsage: metrics.memoryUsage, threshold: thresholds.memoryUsageMB });
    }

    // Connection uptime threshold
    if (metrics.connectionUptime < thresholds.connectionUptime) {
      this.createAlert('connection', 'high', 'Low Connection Uptime', 
        `Connection uptime ${(metrics.connectionUptime * 100).toFixed(2)}% below threshold ${(thresholds.connectionUptime * 100).toFixed(2)}%`,
        { uptime: metrics.connectionUptime, threshold: thresholds.connectionUptime });
    }
  }

  private collectMetrics(): void {
    const transportMetrics = this.eventBus.getTransportMetrics();
    const subscriptionStats = this.eventBus.getSubscriptionStats();

    const snapshot: MetricsSnapshot = {
      timestamp: Date.now(),
      eventThroughput: transportMetrics.throughput,
      activeSubscriptions: subscriptionStats.total,
      connectionStatus: 'connected', // Would be determined by transport
      memoryUsage: transportMetrics.memoryUsage,
      errorRate: transportMetrics.errorRate,
      averageLatency: transportMetrics.averageLatency,
      queueSize: 0 // Would be determined by transport queue
    };

    this.metricsHistory.push(snapshot);

    // Cleanup old metrics
    const retentionMs = this.config.metricsRetentionDays * 24 * 60 * 60 * 1000;
    const cutoffTime = Date.now() - retentionMs;
    this.metricsHistory = this.metricsHistory.filter(m => m.timestamp > cutoffTime);

    this.emit('metrics.collected', snapshot);
  }

  private trackEventProcessing(event: AGUIEvent): void {
    // Track event processing metrics
    this.emit('event.tracked', {
      eventId: event.id,
      eventType: event.type,
      timestamp: event.timestamp,
      processingTime: Date.now() - event.timestamp
    });
  }

  private handleConnectionEvent(type: string, data: any): void {
    this.emit('connection.event', { type, data, timestamp: Date.now() });
  }

  private handleSystemError(errorData: any): void {
    this.createAlert('error', 'high', 'System Error', 
      `System error occurred: ${errorData.error?.message || 'Unknown error'}`,
      errorData);
  }

  private createAlert(
    type: Alert['type'], 
    severity: Alert['severity'], 
    title: string, 
    description: string, 
    metadata: Record<string, any> = {}
  ): Alert {
    const alert: Alert = {
      id: `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      severity,
      title,
      description,
      timestamp: Date.now(),
      resolved: false,
      metadata
    };

    this.alerts.set(alert.id, alert);
    this.emit('alert.created', alert);

    // Emit to event bus
    this.eventBus.emit('alert.created', {
      alert_id: alert.id,
      alert_type: type,
      severity,
      title,
      message: description,
      timestamp: Date.now()
    });

    return alert;
  }

  private resolveAlert(alertId: string): void {
    const alert = this.alerts.get(alertId);
    if (alert && !alert.resolved) {
      alert.resolved = true;
      alert.resolvedAt = Date.now();
      this.emit('alert.resolved', alert);

      // Emit to event bus
      this.eventBus.emit('alert.resolved', {
        alert_id: alertId,
        timestamp: Date.now()
      });
    }
  }

  private resolveAlertsOfType(type: Alert['type']): void {
    for (const [alertId, alert] of this.alerts.entries()) {
      if (alert.type === type && !alert.resolved) {
        this.resolveAlert(alertId);
      }
    }
  }

  // Public API methods
  public getSystemHealth(): SystemHealth | null {
    if (!this.config.enableHealthChecks) {
      return null;
    }
    return this.performHealthCheck() as any; // Will be resolved in real usage
  }

  public getActiveAlerts(): Alert[] {
    return Array.from(this.alerts.values()).filter(alert => !alert.resolved);
  }

  public getMetricsHistory(hours: number = 24): MetricsSnapshot[] {
    const cutoffTime = Date.now() - (hours * 60 * 60 * 1000);
    return this.metricsHistory.filter(m => m.timestamp > cutoffTime);
  }

  public resolveAlertById(alertId: string): boolean {
    const alert = this.alerts.get(alertId);
    if (alert && !alert.resolved) {
      this.resolveAlert(alertId);
      return true;
    }
    return false;
  }

  public updateConfig(newConfig: Partial<MonitoringConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    // Restart timers if intervals changed
    if (newConfig.healthCheckInterval && this.healthCheckTimer) {
      this.stop();
      this.start();
    }
  }

  public exportMetrics(): {
    config: MonitoringConfig;
    alerts: Alert[];
    metricsHistory: MetricsSnapshot[];
    uptime: number;
  } {
    return {
      config: this.config,
      alerts: Array.from(this.alerts.values()),
      metricsHistory: this.metricsHistory,
      uptime: Date.now() - this.startTime
    };
  }
}

// Factory function
export function createAGUIMonitor(eventBus: AGUIEventBus, config?: Partial<MonitoringConfig>): AGUIMonitor {
  return new AGUIMonitor(eventBus, config);
}

// Default monitoring configuration
export const DEFAULT_MONITORING_CONFIG: MonitoringConfig = {
  enableHealthChecks: true,
  healthCheckInterval: 30000,
  enablePerformanceTracking: true,
  enableAlerts: true,
  alertThresholds: {
    errorRate: 0.05,
    latencyMs: 5000,
    connectionUptime: 0.95,
    memoryUsageMB: 500,
    queueSize: 1000,
    failedEventRate: 0.1
  },
  enableMetricsCollection: true,
  metricsRetentionDays: 7
};