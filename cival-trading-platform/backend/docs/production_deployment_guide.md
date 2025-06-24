# MCP Trading Platform - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the MCP Trading Platform to production environments, including infrastructure requirements, security considerations, monitoring setup, and operational procedures.

## Prerequisites

### System Requirements

**Minimum Production Environment:**
- CPU: 16+ cores (Intel Xeon or AMD EPYC)
- RAM: 64GB+ DDR4
- Storage: 1TB+ NVMe SSD for OS/Apps + 10TB+ for data storage
- Network: 10Gbps+ bandwidth with low latency
- Operating System: Ubuntu 20.04 LTS or CentOS 8+

**Recommended Production Environment:**
- CPU: 32+ cores across multiple nodes
- RAM: 128GB+ per node
- Storage: NVMe SSD arrays with RAID configuration
- Network: Dedicated high-speed connections to exchanges
- Load Balancer: Hardware or software load balancer

### Software Dependencies

```bash
# Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# System dependencies
sudo apt install -y \
    build-essential \
    git \
    nginx \
    redis-server \
    postgresql-14 \
    mongodb \
    docker.io \
    docker-compose

# Install Python packages
pip install -r requirements.txt
```

## Infrastructure Setup

### 1. Database Configuration

#### PostgreSQL Setup
```sql
-- Create trading database
CREATE DATABASE trading_platform;
CREATE USER trading_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE trading_platform TO trading_user;

-- Performance tuning for trading workloads
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

#### MongoDB Setup
```javascript
// Create trading database and user
use trading_platform
db.createUser({
  user: "trading_user",
  pwd: "secure_password_here",
  roles: [
    { role: "readWrite", db: "trading_platform" },
    { role: "dbAdmin", db: "trading_platform" }
  ]
})

// Configure replica set for high availability
rs.initiate({
  _id: "trading_rs",
  members: [
    { _id: 0, host: "mongo1:27017" },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" }
  ]
})
```

#### Redis Configuration
```conf
# /etc/redis/redis.conf
bind 0.0.0.0
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### 2. Network Configuration

#### Firewall Rules
```bash
# UFW firewall configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow application ports
sudo ufw allow 8001:8100/tcp

# Allow database ports (restrict to internal network)
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 10.0.0.0/8 to any port 27017
sudo ufw allow from 10.0.0.0/8 to any port 6379

sudo ufw enable
```

#### Load Balancer Configuration (Nginx)
```nginx
# /etc/nginx/sites-available/trading-platform
upstream trading_backend {
    least_conn;
    server 127.0.0.1:8001 weight=1;
    server 127.0.0.1:8010 weight=2;
    server 127.0.0.1:8011 weight=2;
    server 127.0.0.1:8012 weight=3;
}

server {
    listen 443 ssl http2;
    server_name trading.example.com;
    
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=trading:10m rate=100r/s;
    limit_req zone=trading burst=200 nodelay;
    
    location / {
        proxy_pass http://trading_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

## Security Configuration

### 1. SSL/TLS Setup

```bash
# Generate SSL certificates using Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d trading.example.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Environment Variables

Create production environment file:
```bash
# /opt/trading-platform/.env
DATABASE_URL=postgresql://trading_user:secure_password@localhost:5432/trading_platform
MONGODB_URL=mongodb://trading_user:secure_password@localhost:27017/trading_platform
REDIS_URL=redis://localhost:6379/0

# API Keys (use secure key management system)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_news_api_key
FRED_API_KEY=your_fred_api_key

# JWT Configuration
JWT_SECRET_KEY=your_very_secure_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_PER_MINUTE=1000
RATE_LIMIT_PER_HOUR=50000

# Performance Settings
CACHE_TTL_SECONDS=300
MAX_CONNECTIONS=1000
WORKER_PROCESSES=8

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

### 3. Access Control

```python
# Security configuration
SECURITY_CONFIG = {
    "authentication": {
        "enabled": True,
        "jwt_secret": os.getenv("JWT_SECRET_KEY"),
        "token_expiry": 86400,  # 24 hours
        "refresh_token_expiry": 604800,  # 7 days
    },
    "authorization": {
        "rbac_enabled": True,
        "roles": ["admin", "trader", "analyst", "readonly"],
        "permissions": {
            "admin": ["*"],
            "trader": ["trading.*", "portfolio.*", "market_data.*"],
            "analyst": ["analytics.*", "market_data.*", "portfolio.read"],
            "readonly": ["*.read"]
        }
    },
    "encryption": {
        "data_at_rest": True,
        "data_in_transit": True,
        "key_rotation_days": 90
    }
}
```

## Deployment Process

### 1. Automated Deployment Script

```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

DEPLOY_DIR="/opt/trading-platform"
BACKUP_DIR="/opt/backups"
SERVICE_USER="trading"

echo "🚀 Starting MCP Trading Platform deployment..."

# Create backup
echo "📦 Creating backup..."
sudo -u $SERVICE_USER pg_dump trading_platform > $BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql
sudo cp -r $DEPLOY_DIR $BACKUP_DIR/app_backup_$(date +%Y%m%d_%H%M%S)

# Stop services
echo "🛑 Stopping services..."
sudo systemctl stop trading-platform

# Update code
echo "📥 Updating code..."
cd $DEPLOY_DIR
sudo -u $SERVICE_USER git pull origin main

# Update dependencies
echo "📦 Updating dependencies..."
sudo -u $SERVICE_USER pip install -r requirements.txt

# Run database migrations
echo "🗄️ Running database migrations..."
sudo -u $SERVICE_USER python manage.py migrate

# Run tests
echo "🧪 Running tests..."
sudo -u $SERVICE_USER python -m pytest tests/ -v

# Start services
echo "🚀 Starting services..."
sudo systemctl start trading-platform

# Health check
echo "🏥 Running health checks..."
sleep 30
curl -f http://localhost:8100/health || exit 1

echo "✅ Deployment completed successfully!"
```

### 2. Systemd Service Configuration

```ini
# /etc/systemd/system/trading-platform.service
[Unit]
Description=MCP Trading Platform
After=network.target postgresql.service mongodb.service redis.service
Requires=postgresql.service mongodb.service redis.service

[Service]
Type=exec
User=trading
Group=trading
WorkingDirectory=/opt/trading-platform
Environment=PYTHONPATH=/opt/trading-platform
ExecStart=/opt/trading-platform/venv/bin/python start_platform.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
```

### 3. Docker Deployment (Alternative)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  trading-platform:
    build: .
    ports:
      - "8001-8100:8001-8100"
    environment:
      - ENV=production
    env_file:
      - .env.prod
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - postgres
      - mongodb
      - redis
    restart: unless-stopped
    
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: trading_platform
      POSTGRES_USER: trading_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  mongodb:
    image: mongo:5
    environment:
      MONGO_INITDB_ROOT_USERNAME: trading_user
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  mongodb_data:
  redis_data:
```

## Monitoring and Observability

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "trading_platform_rules.yml"

scrape_configs:
  - job_name: 'trading-platform'
    static_configs:
      - targets: ['localhost:8001', 'localhost:8010', 'localhost:8011', 'localhost:8012']
    scrape_interval: 5s
    metrics_path: /metrics
    
  - job_name: 'system-health'
    static_configs:
      - targets: ['localhost:8100']
    scrape_interval: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. Grafana Dashboard

```json
{
  "dashboard": {
    "title": "MCP Trading Platform - Production Metrics",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"trading-platform\"}",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "Response Time P95",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      }
    ]
  }
}
```

### 3. Log Aggregation

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    
  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      - ./logs:/logs:ro
    depends_on:
      - elasticsearch
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## Performance Optimization

### 1. Database Tuning

```sql
-- PostgreSQL performance optimization
ALTER SYSTEM SET max_connections = 500;
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Create indexes for trading queries
CREATE INDEX CONCURRENTLY idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
CREATE INDEX CONCURRENTLY idx_orders_status_timestamp ON orders(status, created_at);
CREATE INDEX CONCURRENTLY idx_portfolio_positions_symbol ON portfolio_positions(symbol);
```

### 2. Application Performance

```python
# Performance configuration
PERFORMANCE_CONFIG = {
    "connection_pooling": {
        "postgres_pool_size": 20,
        "postgres_max_overflow": 30,
        "redis_pool_size": 50,
        "mongodb_pool_size": 100
    },
    "caching": {
        "enabled": True,
        "default_ttl": 300,
        "market_data_ttl": 5,
        "analytics_ttl": 600
    },
    "async_processing": {
        "worker_count": 8,
        "queue_size": 10000,
        "batch_size": 100
    }
}
```

## Backup and Recovery

### 1. Automated Backup Script

```bash
#!/bin/bash
# backup.sh - Automated backup script

BACKUP_DIR="/opt/backups"
S3_BUCKET="trading-platform-backups"
RETENTION_DAYS=30

# Database backup
pg_dump trading_platform | gzip > $BACKUP_DIR/postgres_$(date +%Y%m%d_%H%M%S).sql.gz

# MongoDB backup
mongodump --db trading_platform --gzip --archive=$BACKUP_DIR/mongodb_$(date +%Y%m%d_%H%M%S).archive.gz

# Application data backup
tar -czf $BACKUP_DIR/app_data_$(date +%Y%m%d_%H%M%S).tar.gz /opt/trading-platform/data

# Upload to S3
aws s3 sync $BACKUP_DIR s3://$S3_BUCKET/$(date +%Y%m%d)/

# Cleanup old backups
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
```

### 2. Disaster Recovery Plan

```markdown
## Disaster Recovery Procedures

### RTO (Recovery Time Objective): 4 hours
### RPO (Recovery Point Objective): 15 minutes

### Recovery Steps:
1. **Assessment** (30 minutes)
   - Determine scope of failure
   - Identify affected services
   - Notify stakeholders

2. **Infrastructure Recovery** (2 hours)
   - Provision new infrastructure if needed
   - Restore network connectivity
   - Deploy base system configuration

3. **Data Recovery** (1 hour)
   - Restore database from latest backup
   - Verify data integrity
   - Apply any missing transactions

4. **Application Recovery** (30 minutes)
   - Deploy application code
   - Start all services
   - Verify functionality

5. **Validation and Monitoring** (1 hour)
   - Run comprehensive health checks
   - Verify trading functionality
   - Monitor for issues
```

## Operational Procedures

### 1. Health Checks

```bash
#!/bin/bash
# health_check.sh - Comprehensive health monitoring

check_service() {
    local service=$1
    local port=$2
    
    if curl -f -s "http://localhost:$port/health" > /dev/null; then
        echo "✅ $service (port $port) - HEALTHY"
        return 0
    else
        echo "❌ $service (port $port) - UNHEALTHY"
        return 1
    fi
}

echo "🏥 MCP Trading Platform Health Check"
echo "=================================="

# Check all services
check_service "Market Data" 8001
check_service "Trading Engine" 8010
check_service "Risk Management" 8012
check_service "Portfolio Tracker" 8013
check_service "System Health Monitor" 8100

# Check databases
if pg_isready -h localhost -p 5432 -U trading_user; then
    echo "✅ PostgreSQL - HEALTHY"
else
    echo "❌ PostgreSQL - UNHEALTHY"
fi

if redis-cli ping | grep -q PONG; then
    echo "✅ Redis - HEALTHY"
else
    echo "❌ Redis - UNHEALTHY"
fi

# Check system resources
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
MEM_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

echo "📊 System Resources:"
echo "   CPU Usage: ${CPU_USAGE}%"
echo "   Memory Usage: ${MEM_USAGE}%"
echo "   Disk Usage: ${DISK_USAGE}%"
```

### 2. Emergency Procedures

```bash
# Emergency shutdown
sudo systemctl stop trading-platform
sudo systemctl stop postgresql
sudo systemctl stop mongodb
sudo systemctl stop redis

# Emergency startup
sudo systemctl start postgresql
sudo systemctl start mongodb
sudo systemctl start redis
sleep 10
sudo systemctl start trading-platform

# Clear all caches
redis-cli FLUSHALL
sudo systemctl restart trading-platform
```

## Compliance and Auditing

### 1. Audit Logging

```python
# Audit logging configuration
AUDIT_CONFIG = {
    "enabled": True,
    "log_level": "INFO",
    "events": [
        "user_login",
        "order_submission",
        "order_cancellation",
        "portfolio_modification",
        "risk_limit_change",
        "system_configuration_change"
    ],
    "retention_days": 2555,  # 7 years
    "encryption": True,
    "remote_storage": "s3://audit-logs-bucket"
}
```

### 2. Regulatory Compliance

```markdown
## Compliance Requirements

### SOX (Sarbanes-Oxley) Compliance:
- Audit trails for all financial transactions
- Access controls and segregation of duties
- Regular security assessments
- Data retention policies

### FINRA Compliance:
- Real-time monitoring of trading activities
- Best execution reporting
- Order audit trail (OATS)
- Position limit monitoring

### MiFID II Compliance:
- Transaction reporting
- Clock synchronization
- Systematic internalizer reporting
- Best execution monitoring
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **High Latency**
   ```bash
   # Check network latency
   ping -c 10 exchange.example.com
   
   # Check database performance
   SELECT query, calls, total_time, mean_time 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;
   
   # Check system load
   uptime
   iostat -x 1 5
   ```

2. **Memory Issues**
   ```bash
   # Check memory usage
   free -h
   ps aux --sort=-%mem | head -10
   
   # Clear caches if needed
   echo 3 > /proc/sys/vm/drop_caches
   ```

3. **Service Failures**
   ```bash
   # Check service status
   systemctl status trading-platform
   
   # View logs
   journalctl -u trading-platform -f
   
   # Restart service
   sudo systemctl restart trading-platform
   ```

## Support and Maintenance

### Maintenance Schedule

- **Daily**: Health checks, log rotation, backup verification
- **Weekly**: Performance review, security updates
- **Monthly**: Full system backup, capacity planning review
- **Quarterly**: Security audit, disaster recovery testing

### Contact Information

- **Operations Team**: ops@trading-platform.com
- **Security Team**: security@trading-platform.com
- **Emergency Hotline**: +1-XXX-XXX-XXXX

---

This production deployment guide provides comprehensive instructions for deploying and maintaining the MCP Trading Platform in a production environment. Follow all procedures carefully and ensure proper testing before deploying to live trading environments.