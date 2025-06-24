/**
 * AG-UI Production Configuration and Deployment Setup
 * Phase 12: Production-ready configuration management and deployment utilities
 */

export interface ProductionConfig {
  environment: 'development' | 'staging' | 'production';
  api: APIConfig;
  websocket: WebSocketConfig;
  monitoring: MonitoringConfig;
  security: SecurityConfig;
  performance: PerformanceConfig;
  logging: LoggingConfig;
  features: FeatureFlags;
}

export interface APIConfig {
  baseURL: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
  rateLimit: {
    requests: number;
    windowMs: number;
  };
  compression: boolean;
  caching: {
    enabled: boolean;
    ttl: number;
    maxSize: number;
  };
}

export interface WebSocketConfig {
  url: string;
  reconnectAttempts: number;
  reconnectDelay: number;
  heartbeatInterval: number;
  messageQueueSize: number;
  compression: boolean;
  protocols: string[];
}

export interface MonitoringConfig {
  enabled: boolean;
  healthCheckInterval: number;
  metricsCollection: boolean;
  alerting: {
    enabled: boolean;
    webhookUrl?: string;
    emailNotifications?: string[];
  };
  analytics: {
    enabled: boolean;
    samplingRate: number;
    batchSize: number;
    flushInterval: number;
  };
}

export interface SecurityConfig {
  authentication: {
    required: boolean;
    tokenType: 'jwt' | 'bearer' | 'api-key';
    refreshThreshold: number;
  };
  encryption: {
    enabled: boolean;
    algorithm: string;
  };
  cors: {
    enabled: boolean;
    origins: string[];
    credentials: boolean;
  };
  contentSecurityPolicy: {
    enabled: boolean;
    directives: Record<string, string>;
  };
}

export interface PerformanceConfig {
  optimization: {
    bundleSplitting: boolean;
    lazyLoading: boolean;
    memoryManagement: boolean;
  };
  caching: {
    staticAssets: number;
    apiResponses: number;
    components: boolean;
  };
  concurrency: {
    maxConcurrentRequests: number;
    maxWebSocketConnections: number;
    eventQueueSize: number;
  };
}

export interface LoggingConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
  destinations: Array<{
    type: 'console' | 'file' | 'remote';
    config: any;
  }>;
  formatting: {
    timestamp: boolean;
    structured: boolean;
    includeStack: boolean;
  };
  sampling: {
    enabled: boolean;
    rate: number;
  };
}

export interface FeatureFlags {
  realTimeUpdates: boolean;
  advancedAnalytics: boolean;
  multiExchangeSupport: boolean;
  llmIntegration: boolean;
  autonomousAgents: boolean;
  riskManagement: boolean;
  portfolioOptimization: boolean;
  socialTrading: boolean;
  apiV2: boolean;
  experimentalFeatures: boolean;
}

// Environment-specific configurations
export const DEVELOPMENT_CONFIG: ProductionConfig = {
  environment: 'development',
  api: {
    baseURL: 'http://localhost:8000',
    timeout: 30000,
    retryAttempts: 2,
    retryDelay: 1000,
    rateLimit: {
      requests: 1000,
      windowMs: 60000
    },
    compression: false,
    caching: {
      enabled: true,
      ttl: 300000,
      maxSize: 100
    }
  },
  websocket: {
    url: 'ws://localhost:8000/ws/agui',
    reconnectAttempts: 10,
    reconnectDelay: 1000,
    heartbeatInterval: 30000,
    messageQueueSize: 1000,
    compression: false,
    protocols: []
  },
  monitoring: {
    enabled: true,
    healthCheckInterval: 30000,
    metricsCollection: true,
    alerting: {
      enabled: false
    },
    analytics: {
      enabled: false,
      samplingRate: 1.0,
      batchSize: 100,
      flushInterval: 10000
    }
  },
  security: {
    authentication: {
      required: false,
      tokenType: 'jwt',
      refreshThreshold: 300000
    },
    encryption: {
      enabled: false,
      algorithm: 'AES-256-GCM'
    },
    cors: {
      enabled: true,
      origins: ['*'],
      credentials: false
    },
    contentSecurityPolicy: {
      enabled: false,
      directives: {}
    }
  },
  performance: {
    optimization: {
      bundleSplitting: false,
      lazyLoading: false,
      memoryManagement: true
    },
    caching: {
      staticAssets: 3600000,
      apiResponses: 300000,
      components: false
    },
    concurrency: {
      maxConcurrentRequests: 50,
      maxWebSocketConnections: 10,
      eventQueueSize: 10000
    }
  },
  logging: {
    level: 'debug',
    destinations: [
      { type: 'console', config: {} }
    ],
    formatting: {
      timestamp: true,
      structured: false,
      includeStack: true
    },
    sampling: {
      enabled: false,
      rate: 1.0
    }
  },
  features: {
    realTimeUpdates: true,
    advancedAnalytics: true,
    multiExchangeSupport: true,
    llmIntegration: true,
    autonomousAgents: true,
    riskManagement: true,
    portfolioOptimization: true,
    socialTrading: false,
    apiV2: true,
    experimentalFeatures: true
  }
};

export const STAGING_CONFIG: ProductionConfig = {
  environment: 'staging',
  api: {
    baseURL: process.env.REACT_APP_API_BASE_URL || 'https://api-staging.cival.ai',
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1500,
    rateLimit: {
      requests: 500,
      windowMs: 60000
    },
    compression: true,
    caching: {
      enabled: true,
      ttl: 300000,
      maxSize: 200
    }
  },
  websocket: {
    url: process.env.REACT_APP_WS_URL || 'wss://ws-staging.cival.ai/agui',
    reconnectAttempts: 5,
    reconnectDelay: 2000,
    heartbeatInterval: 30000,
    messageQueueSize: 5000,
    compression: true,
    protocols: ['agui-v2']
  },
  monitoring: {
    enabled: true,
    healthCheckInterval: 30000,
    metricsCollection: true,
    alerting: {
      enabled: true,
      webhookUrl: process.env.REACT_APP_ALERT_WEBHOOK
    },
    analytics: {
      enabled: true,
      samplingRate: 1.0,
      batchSize: 50,
      flushInterval: 30000
    }
  },
  security: {
    authentication: {
      required: true,
      tokenType: 'jwt',
      refreshThreshold: 300000
    },
    encryption: {
      enabled: true,
      algorithm: 'AES-256-GCM'
    },
    cors: {
      enabled: true,
      origins: ['https://staging.cival.ai'],
      credentials: true
    },
    contentSecurityPolicy: {
      enabled: true,
      directives: {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'connect-src': "'self' wss://ws-staging.cival.ai"
      }
    }
  },
  performance: {
    optimization: {
      bundleSplitting: true,
      lazyLoading: true,
      memoryManagement: true
    },
    caching: {
      staticAssets: 3600000,
      apiResponses: 300000,
      components: true
    },
    concurrency: {
      maxConcurrentRequests: 30,
      maxWebSocketConnections: 5,
      eventQueueSize: 5000
    }
  },
  logging: {
    level: 'info',
    destinations: [
      { type: 'console', config: {} },
      { type: 'remote', config: { endpoint: '/api/logs' } }
    ],
    formatting: {
      timestamp: true,
      structured: true,
      includeStack: false
    },
    sampling: {
      enabled: true,
      rate: 0.8
    }
  },
  features: {
    realTimeUpdates: true,
    advancedAnalytics: true,
    multiExchangeSupport: true,
    llmIntegration: true,
    autonomousAgents: true,
    riskManagement: true,
    portfolioOptimization: true,
    socialTrading: false,
    apiV2: true,
    experimentalFeatures: false
  }
};

export const PRODUCTION_CONFIG: ProductionConfig = {
  environment: 'production',
  api: {
    baseURL: process.env.REACT_APP_API_BASE_URL || 'https://api.cival.ai',
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 2000,
    rateLimit: {
      requests: 300,
      windowMs: 60000
    },
    compression: true,
    caching: {
      enabled: true,
      ttl: 600000,
      maxSize: 500
    }
  },
  websocket: {
    url: process.env.REACT_APP_WS_URL || 'wss://ws.cival.ai/agui',
    reconnectAttempts: 5,
    reconnectDelay: 5000,
    heartbeatInterval: 30000,
    messageQueueSize: 10000,
    compression: true,
    protocols: ['agui-v2']
  },
  monitoring: {
    enabled: true,
    healthCheckInterval: 60000,
    metricsCollection: true,
    alerting: {
      enabled: true,
      webhookUrl: process.env.REACT_APP_ALERT_WEBHOOK,
      emailNotifications: process.env.REACT_APP_ALERT_EMAILS?.split(',')
    },
    analytics: {
      enabled: true,
      samplingRate: 0.1,
      batchSize: 100,
      flushInterval: 60000
    }
  },
  security: {
    authentication: {
      required: true,
      tokenType: 'jwt',
      refreshThreshold: 600000
    },
    encryption: {
      enabled: true,
      algorithm: 'AES-256-GCM'
    },
    cors: {
      enabled: true,
      origins: ['https://app.cival.ai', 'https://dashboard.cival.ai'],
      credentials: true
    },
    contentSecurityPolicy: {
      enabled: true,
      directives: {
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': "'self' 'unsafe-inline'",
        'connect-src': "'self' wss://ws.cival.ai",
        'img-src': "'self' data: https:",
        'font-src': "'self' https://fonts.gstatic.com"
      }
    }
  },
  performance: {
    optimization: {
      bundleSplitting: true,
      lazyLoading: true,
      memoryManagement: true
    },
    caching: {
      staticAssets: 86400000, // 24 hours
      apiResponses: 300000, // 5 minutes
      components: true
    },
    concurrency: {
      maxConcurrentRequests: 20,
      maxWebSocketConnections: 3,
      eventQueueSize: 5000
    }
  },
  logging: {
    level: 'warn',
    destinations: [
      { type: 'remote', config: { endpoint: '/api/logs', batchSize: 100 } }
    ],
    formatting: {
      timestamp: true,
      structured: true,
      includeStack: false
    },
    sampling: {
      enabled: true,
      rate: 0.1
    }
  },
  features: {
    realTimeUpdates: true,
    advancedAnalytics: true,
    multiExchangeSupport: true,
    llmIntegration: true,
    autonomousAgents: true,
    riskManagement: true,
    portfolioOptimization: true,
    socialTrading: true,
    apiV2: true,
    experimentalFeatures: false
  }
};

// Configuration manager
export class AGUIConfigManager {
  private static instance: AGUIConfigManager;
  private config: ProductionConfig;
  private overrides: any = {};

  private constructor() {
    this.config = this.determineConfig();
    this.applyEnvironmentOverrides();
  }

  public static getInstance(): AGUIConfigManager {
    if (!AGUIConfigManager.instance) {
      AGUIConfigManager.instance = new AGUIConfigManager();
    }
    return AGUIConfigManager.instance;
  }

  private determineConfig(): ProductionConfig {
    const env = process.env.NODE_ENV || 'development';
    const forcedEnv = process.env.REACT_APP_FORCE_ENV;

    switch (forcedEnv || env) {
      case 'production':
        return PRODUCTION_CONFIG;
      case 'staging':
        return STAGING_CONFIG;
      default:
        return DEVELOPMENT_CONFIG;
    }
  }

  private applyEnvironmentOverrides(): void {
    // Apply any environment variable overrides
    if (process.env.REACT_APP_API_TIMEOUT) {
      this.overrides.api = {
        ...(this.overrides.api || {}),
        timeout: parseInt(process.env.REACT_APP_API_TIMEOUT)
      };
    }

    if (process.env.REACT_APP_LOG_LEVEL) {
      this.overrides.logging = {
        ...(this.overrides.logging || {}),
        level: process.env.REACT_APP_LOG_LEVEL as any
      };
    }

    if (process.env.REACT_APP_FEATURE_FLAGS) {
      try {
        const featureFlags = JSON.parse(process.env.REACT_APP_FEATURE_FLAGS);
        this.overrides.features = {
          ...this.overrides.features,
          ...featureFlags
        };
      } catch (error) {
        console.warn('Invalid feature flags JSON:', error);
      }
    }
  }

  public getConfig(): ProductionConfig {
    return this.mergeConfig(this.config, this.overrides);
  }

  public getAPIConfig(): APIConfig {
    return this.getConfig().api;
  }

  public getWebSocketConfig(): WebSocketConfig {
    return this.getConfig().websocket;
  }

  public getMonitoringConfig(): MonitoringConfig {
    return this.getConfig().monitoring;
  }

  public getSecurityConfig(): SecurityConfig {
    return this.getConfig().security;
  }

  public getPerformanceConfig(): PerformanceConfig {
    return this.getConfig().performance;
  }

  public getLoggingConfig(): LoggingConfig {
    return this.getConfig().logging;
  }

  public getFeatureFlags(): FeatureFlags {
    return this.getConfig().features;
  }

  public isFeatureEnabled(feature: keyof FeatureFlags): boolean {
    return this.getFeatureFlags()[feature];
  }

  public override(overrides: Partial<ProductionConfig>): void {
    this.overrides = this.mergeConfig(this.overrides, overrides);
  }

  public resetOverrides(): void {
    this.overrides = {};
  }

  public getEnvironment(): string {
    return this.config.environment;
  }

  public isDevelopment(): boolean {
    return this.config.environment === 'development';
  }

  public isStaging(): boolean {
    return this.config.environment === 'staging';
  }

  public isProduction(): boolean {
    return this.config.environment === 'production';
  }

  private mergeConfig<T>(base: T, override: Partial<T>): T {
    return {
      ...base,
      ...Object.fromEntries(
        Object.entries(override).map(([key, value]) => [
          key,
          typeof value === 'object' && value !== null && !Array.isArray(value)
            ? this.mergeConfig((base as any)[key] || {}, value)
            : value
        ])
      )
    };
  }

  // Validation methods
  public validateConfig(): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    const config = this.getConfig();

    // Validate API configuration
    if (!config.api.baseURL) {
      errors.push('API base URL is required');
    }

    if (config.api.timeout < 1000) {
      errors.push('API timeout must be at least 1000ms');
    }

    // Validate WebSocket configuration
    if (!config.websocket.url) {
      errors.push('WebSocket URL is required');
    }

    // Validate security in production
    if (config.environment === 'production') {
      if (!config.security.authentication.required) {
        errors.push('Authentication is required in production');
      }

      if (!config.security.encryption.enabled) {
        errors.push('Encryption is required in production');
      }

      if (config.security.cors.origins.includes('*')) {
        errors.push('Wildcard CORS origins not allowed in production');
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  // Runtime configuration updates
  public updateFeatureFlag(feature: keyof FeatureFlags, enabled: boolean): void {
    this.overrides.features = {
      ...this.overrides.features,
      [feature]: enabled
    };
  }

  public updateLogLevel(level: LoggingConfig['level']): void {
    this.overrides.logging = {
      ...this.overrides.logging,
      level
    };
  }

  // Export configuration for debugging
  public exportConfig(): string {
    return JSON.stringify(this.getConfig(), null, 2);
  }
}

// Convenience functions
export function getConfig(): ProductionConfig {
  return AGUIConfigManager.getInstance().getConfig();
}

export function getAPIConfig(): APIConfig {
  return AGUIConfigManager.getInstance().getAPIConfig();
}

export function getWebSocketConfig(): WebSocketConfig {
  return AGUIConfigManager.getInstance().getWebSocketConfig();
}

export function isFeatureEnabled(feature: keyof FeatureFlags): boolean {
  return AGUIConfigManager.getInstance().isFeatureEnabled(feature);
}

export function isDevelopment(): boolean {
  return AGUIConfigManager.getInstance().isDevelopment();
}

export function isProduction(): boolean {
  return AGUIConfigManager.getInstance().isProduction();
}

// Initialize configuration on module load
export const configManager = AGUIConfigManager.getInstance();