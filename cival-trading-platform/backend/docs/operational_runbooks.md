# MCP Trading Platform - Operational Runbooks

## Overview

This document provides step-by-step operational procedures for managing the MCP Trading Platform in production environments. These runbooks cover common operational scenarios, troubleshooting procedures, and emergency response protocols.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Service Management](#service-management)
3. [Incident Response](#incident-response)
4. [Performance Troubleshooting](#performance-troubleshooting)
5. [Data Management](#data-management)
6. [Security Procedures](#security-procedures)
7. [Emergency Procedures](#emergency-procedures)

---

## Daily Operations

### Morning Startup Checklist

**Timing**: Every trading day, 30 minutes before market open

```bash
#!/bin/bash
# daily_startup_check.sh

echo "🌅 Daily Startup Checklist - $(date)"
echo "=================================="

# 1. Check system health
echo "1. System Health Check..."
python system_health_monitor.py --check-all

# 2. Verify market data connections
echo "2. Market Data Verification..."
curl -s http://localhost:8001/health | jq '.market_data_status'

# 3. Check trading engine status
echo "3. Trading Engine Status..."
curl -s http://localhost:8010/health | jq '.trading_status'

# 4. Verify risk management systems
echo "4. Risk Management Check..."
curl -s http://localhost:8012/health | jq '.risk_status'

# 5. Check portfolio positions
echo "5. Portfolio Status..."
curl -s http://localhost:8013/portfolio/summary

# 6. Verify external data feeds
echo "6. External Data Feeds..."
curl -s http://localhost:8093/providers | jq '.active_providers'

# 7. Check system resources
echo "7. System Resources..."
df -h
free -h
uptime

echo "✅ Daily startup check completed"
```

### End-of-Day Procedures

**Timing**: After market close

```bash
#!/bin/bash
# daily_eod_procedures.sh

echo "🌇 End-of-Day Procedures - $(date)"
echo "=================================="

# 1. Generate daily trading report
echo "1. Generating daily reports..."
python reports/daily_trading_report.py --date=$(date +%Y-%m-%d)

# 2. Backup trading data
echo "2. Backing up trading data..."
./scripts/backup_trading_data.sh

# 3. Risk reporting
echo "3. Risk reporting..."
python reports/daily_risk_report.py

# 4. Performance metrics
echo "4. Performance metrics..."
python reports/performance_summary.py

# 5. Clean up temporary files
echo "5. Cleanup..."
find /tmp -name "trading_*" -mtime +1 -delete

echo "✅ End-of-day procedures completed"
```

---

## Service Management

### Starting Services

```bash
# Start all services in correct order
sudo systemctl start postgresql
sudo systemctl start mongodb  
sudo systemctl start redis
sleep 10

# Start platform services
python start_platform.py

# Verify all services are running
./scripts/health_check.sh
```

### Stopping Services

```bash
# Graceful shutdown
echo "Initiating graceful shutdown..."

# Stop platform services first
pkill -f "python.*mcp_servers"

# Stop databases
sudo systemctl stop redis
sudo systemctl stop mongodb
sudo systemctl stop postgresql

echo "All services stopped"
```

### Restarting Individual Services

```bash
# Market Data Server
echo "Restarting Market Data Server..."
pkill -f "market_data_server.py"
sleep 5
python mcp_servers/market_data_server.py &

# Trading Engine
echo "Restarting Trading Engine..."
pkill -f "trading_engine.py"
sleep 5
python mcp_servers/trading_engine.py &

# Verify restart
sleep 10
curl -f http://localhost:8001/health
curl -f http://localhost:8010/health
```

---

## Incident Response

### High-Priority Incident Response

**Trigger**: System unavailability, trading halted, or critical alerts

#### Immediate Response (0-5 minutes)

1. **Assess Situation**
   ```bash
   # Quick system assessment
   ./scripts/quick_health_check.sh
   
   # Check critical services
   systemctl status trading-platform
   systemctl status postgresql
   systemctl status redis
   ```

2. **Notify Stakeholders**
   ```bash
   # Send alert to operations team
   echo "CRITICAL: Trading platform incident at $(date)" | \
   mail -s "URGENT: Platform Incident" ops-team@company.com
   ```

3. **Initial Stabilization**
   ```bash
   # If services are down, attempt restart
   sudo systemctl restart trading-platform
   
   # Check if issue persists
   sleep 30
   ./scripts/health_check.sh
   ```

#### Investigation Phase (5-15 minutes)

1. **Gather Diagnostics**
   ```bash
   # Collect system logs
   journalctl -u trading-platform --since "10 minutes ago" > incident_logs.txt
   
   # Check resource usage
   top -b -n 1 > system_status.txt
   df -h >> system_status.txt
   free -h >> system_status.txt
   
   # Database status
   pg_isready -h localhost -p 5432
   redis-cli ping
   ```

2. **Identify Root Cause**
   ```bash
   # Check error logs
   grep -i error /var/log/trading-platform/*.log | tail -50
   
   # Check database connections
   psql -h localhost -U trading_user -d trading_platform -c "SELECT 1"
   
   # Network connectivity
   ping -c 5 market-data-provider.com
   ```

#### Resolution Phase (15-60 minutes)

1. **Apply Fix**
   ```bash
   # Common fixes based on root cause:
   
   # Database connection issues
   sudo systemctl restart postgresql
   
   # Memory issues
   echo 3 > /proc/sys/vm/drop_caches
   sudo systemctl restart trading-platform
   
   # Network issues
   sudo systemctl restart networking
   ```

2. **Verify Resolution**
   ```bash
   # Full system test
   python tests/integration_test.py
   
   # Verify trading functionality
   curl -X POST http://localhost:8010/orders/test
   ```

#### Post-Incident (After resolution)

1. **Document Incident**
   ```markdown
   ## Incident Report: [YYYY-MM-DD HH:MM]
   
   **Duration**: [Start time] - [End time]
   **Impact**: [Description of impact]
   **Root Cause**: [Identified cause]
   **Resolution**: [Steps taken to resolve]
   **Prevention**: [Steps to prevent recurrence]
   ```

2. **Conduct Post-Mortem**
   - Schedule post-incident review meeting
   - Update runbooks if needed
   - Implement preventive measures

---

## Performance Troubleshooting

### High Latency Issues

**Symptoms**: Response times > 1000ms, trading delays

#### Diagnosis Steps

1. **Check System Load**
   ```bash
   # System load
   uptime
   
   # Top processes
   top -o %CPU
   
   # I/O wait
   iostat -x 1 5
   ```

2. **Database Performance**
   ```sql
   -- Check slow queries
   SELECT query, calls, total_time, mean_time 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;
   
   -- Check blocking queries
   SELECT blocked_locks.pid AS blocked_pid,
          blocked_activity.usename AS blocked_user,
          blocking_locks.pid AS blocking_pid,
          blocking_activity.usename AS blocking_user,
          blocked_activity.query AS blocked_statement,
          blocking_activity.query AS current_statement_in_blocking_process
   FROM pg_catalog.pg_locks blocked_locks
   JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
   JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
   JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
   WHERE NOT blocked_locks.granted;
   ```

3. **Network Performance**
   ```bash
   # Check network latency to external services
   ping -c 10 alpha-vantage.co
   
   # Check bandwidth usage
   iftop -i eth0
   
   # Check connection counts
   netstat -an | grep :8001 | wc -l
   ```

#### Resolution Steps

1. **Immediate Mitigation**
   ```bash
   # Restart high-latency services
   pkill -f "high_latency_service.py"
   python mcp_servers/high_latency_service.py &
   
   # Clear caches
   redis-cli FLUSHALL
   ```

2. **Database Optimization**
   ```sql
   -- Kill long-running queries
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'active' AND query_start < now() - interval '5 minutes';
   
   -- Update table statistics
   ANALYZE;
   ```

### High Memory Usage

**Symptoms**: Memory usage > 90%, OOM errors

#### Diagnosis and Resolution

1. **Identify Memory Consumers**
   ```bash
   # Top memory consumers
   ps aux --sort=-%mem | head -20
   
   # Check for memory leaks
   python memory_profiler.py
   ```

2. **Free Memory**
   ```bash
   # Clear system caches
   echo 3 > /proc/sys/vm/drop_caches
   
   # Restart memory-intensive services
   sudo systemctl restart trading-strategies
   sudo systemctl restart ml-portfolio-optimizer
   ```

### Database Issues

**Symptoms**: Connection errors, slow queries, deadlocks

#### PostgreSQL Issues

1. **Connection Problems**
   ```bash
   # Check connection count
   psql -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Check max connections
   psql -c "SHOW max_connections;"
   
   # Kill idle connections
   psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '1 hour';"
   ```

2. **Performance Issues**
   ```sql
   -- Check table sizes
   SELECT schemaname,tablename,attname,n_distinct,correlation 
   FROM pg_stats WHERE schemaname = 'public';
   
   -- Check index usage
   SELECT schemaname,tablename,indexname,idx_scan,idx_tup_read,idx_tup_fetch 
   FROM pg_stat_user_indexes;
   
   -- Vacuum and analyze
   VACUUM ANALYZE;
   ```

#### MongoDB Issues

1. **Connection Issues**
   ```javascript
   // Check connection status
   db.runCommand({connectionStatus: 1})
   
   // Check current operations
   db.currentOp()
   
   // Kill long-running operations
   db.killOp(opid)
   ```

2. **Performance Issues**
   ```javascript
   // Check slow operations
   db.setProfilingLevel(2, {slowms: 1000})
   db.system.profile.find().sort({ts: -1}).limit(10)
   
   // Check index usage
   db.collection.getIndexes()
   db.collection.aggregate([{$indexStats: {}}])
   ```

---

## Data Management

### Backup Procedures

#### Database Backup

```bash
#!/bin/bash
# backup_databases.sh

BACKUP_DIR="/opt/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
echo "Backing up PostgreSQL..."
pg_dump -h localhost -U trading_user trading_platform | \
gzip > $BACKUP_DIR/postgres_$(date +%H%M%S).sql.gz

# MongoDB backup
echo "Backing up MongoDB..."
mongodump --host localhost --db trading_platform --gzip \
--archive=$BACKUP_DIR/mongodb_$(date +%H%M%S).archive.gz

# Verify backups
echo "Verifying backups..."
if [ -f "$BACKUP_DIR/postgres_*.sql.gz" ] && [ -f "$BACKUP_DIR/mongodb_*.archive.gz" ]; then
    echo "✅ Backups completed successfully"
else
    echo "❌ Backup verification failed"
    exit 1
fi

# Upload to remote storage
aws s3 sync $BACKUP_DIR s3://trading-platform-backups/$(date +%Y%m%d)/
```

#### Data Recovery

```bash
#!/bin/bash
# restore_databases.sh

BACKUP_FILE=$1
RESTORE_TYPE=$2

if [ "$RESTORE_TYPE" = "postgres" ]; then
    echo "Restoring PostgreSQL from $BACKUP_FILE..."
    
    # Stop applications
    sudo systemctl stop trading-platform
    
    # Drop and recreate database
    psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS trading_platform;"
    psql -h localhost -U postgres -c "CREATE DATABASE trading_platform;"
    
    # Restore data
    gunzip -c $BACKUP_FILE | psql -h localhost -U trading_user trading_platform
    
    # Start applications
    sudo systemctl start trading-platform
    
elif [ "$RESTORE_TYPE" = "mongodb" ]; then
    echo "Restoring MongoDB from $BACKUP_FILE..."
    
    # Stop applications
    sudo systemctl stop trading-platform
    
    # Drop database
    mongo trading_platform --eval "db.dropDatabase()"
    
    # Restore data
    mongorestore --gzip --archive=$BACKUP_FILE
    
    # Start applications
    sudo systemctl start trading-platform
fi

echo "✅ Database restoration completed"
```

### Data Archival

```bash
#!/bin/bash
# archive_old_data.sh

# Archive data older than 1 year
ARCHIVE_DATE=$(date -d "1 year ago" +%Y-%m-%d)

echo "Archiving data older than $ARCHIVE_DATE..."

# PostgreSQL archival
psql -h localhost -U trading_user trading_platform << EOF
-- Archive old market data
INSERT INTO market_data_archive SELECT * FROM market_data WHERE date < '$ARCHIVE_DATE';
DELETE FROM market_data WHERE date < '$ARCHIVE_DATE';

-- Archive old orders
INSERT INTO orders_archive SELECT * FROM orders WHERE created_at < '$ARCHIVE_DATE';
DELETE FROM orders WHERE created_at < '$ARCHIVE_DATE';
EOF

# MongoDB archival
mongo trading_platform << EOF
// Archive old analytics data
db.analytics_data.find({timestamp: {\$lt: new Date('$ARCHIVE_DATE')}}).forEach(
    function(doc) {
        db.analytics_data_archive.insert(doc);
        db.analytics_data.remove({_id: doc._id});
    }
);
EOF

echo "✅ Data archival completed"
```

---

## Security Procedures

### Security Incident Response

#### Suspected Breach

1. **Immediate Actions**
   ```bash
   # Isolate affected systems
   sudo iptables -A INPUT -j DROP
   sudo iptables -A OUTPUT -j DROP
   
   # Stop trading operations
   curl -X POST http://localhost:8010/emergency/halt
   
   # Collect evidence
   cp /var/log/auth.log /tmp/evidence/
   cp /var/log/trading-platform/*.log /tmp/evidence/
   netstat -an > /tmp/evidence/network_connections.txt
   ```

2. **Notification**
   ```bash
   # Alert security team
   echo "SECURITY INCIDENT: Suspected breach at $(date)" | \
   mail -s "URGENT: Security Incident" security-team@company.com
   ```

#### Password Reset Procedure

```bash
# Reset application passwords
echo "Resetting application passwords..."

# Generate new passwords
NEW_DB_PASSWORD=$(openssl rand -base64 32)
NEW_REDIS_PASSWORD=$(openssl rand -base64 32)
NEW_JWT_SECRET=$(openssl rand -base64 64)

# Update database password
psql -h localhost -U postgres -c "ALTER USER trading_user PASSWORD '$NEW_DB_PASSWORD';"

# Update configuration files
sed -i "s/DATABASE_PASSWORD=.*/DATABASE_PASSWORD=$NEW_DB_PASSWORD/" /opt/trading-platform/.env
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_REDIS_PASSWORD/" /opt/trading-platform/.env
sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_JWT_SECRET/" /opt/trading-platform/.env

# Restart services
sudo systemctl restart trading-platform

echo "✅ Password reset completed"
```

### Certificate Management

```bash
#!/bin/bash
# manage_certificates.sh

ACTION=$1

case $ACTION in
    "renew")
        echo "Renewing SSL certificates..."
        certbot renew --quiet
        sudo systemctl reload nginx
        ;;
    "check")
        echo "Checking certificate expiry..."
        openssl x509 -in /etc/ssl/certs/trading-platform.crt -text -noout | grep "Not After"
        ;;
    "backup")
        echo "Backing up certificates..."
        tar -czf /opt/backups/certificates_$(date +%Y%m%d).tar.gz /etc/ssl/
        ;;
esac
```

---

## Emergency Procedures

### Trading Halt

**When to Use**: System instability, market anomalies, regulatory requirements

```bash
#!/bin/bash
# emergency_halt.sh

echo "🚨 EMERGENCY TRADING HALT - $(date)"

# 1. Stop all new order submissions
curl -X POST http://localhost:8010/emergency/halt-new-orders

# 2. Cancel all pending orders
curl -X POST http://localhost:8011/orders/cancel-all-pending

# 3. Close all open positions (if required)
# curl -X POST http://localhost:8010/emergency/close-all-positions

# 4. Notify stakeholders
echo "EMERGENCY: Trading halted at $(date)" | \
mail -s "URGENT: Trading Halt" trading-desk@company.com

# 5. Log the halt
echo "$(date): EMERGENCY HALT ACTIVATED" >> /var/log/trading-platform/emergency.log

echo "✅ Emergency halt completed"
```

### Resume Trading

```bash
#!/bin/bash
# resume_trading.sh

echo "🔄 RESUMING TRADING - $(date)"

# 1. Verify system health
./scripts/comprehensive_health_check.sh
if [ $? -ne 0 ]; then
    echo "❌ Health check failed. Cannot resume trading."
    exit 1
fi

# 2. Enable order submissions
curl -X POST http://localhost:8010/emergency/resume-trading

# 3. Notify stakeholders
echo "Trading resumed at $(date)" | \
mail -s "Trading Resumed" trading-desk@company.com

# 4. Log the resumption
echo "$(date): TRADING RESUMED" >> /var/log/trading-platform/emergency.log

echo "✅ Trading resumed"
```

### Full System Recovery

**Use Case**: Complete system failure, disaster recovery

```bash
#!/bin/bash
# full_system_recovery.sh

echo "🔄 FULL SYSTEM RECOVERY - $(date)"

# 1. Restore infrastructure
echo "1. Restoring infrastructure..."
./scripts/deploy_infrastructure.sh

# 2. Restore databases
echo "2. Restoring databases..."
./scripts/restore_databases.sh latest

# 3. Deploy application
echo "3. Deploying application..."
./scripts/deploy_application.sh production

# 4. Verify data integrity
echo "4. Verifying data integrity..."
python scripts/verify_data_integrity.py

# 5. Run comprehensive tests
echo "5. Running comprehensive tests..."
python tests/system_integration_test.py

# 6. Resume trading (manual approval required)
echo "6. System recovery complete. Manual approval required to resume trading."
echo "   Run: ./scripts/resume_trading.sh"

echo "✅ Full system recovery completed"
```

---

## Monitoring and Alerting

### Alert Response Procedures

#### High CPU Usage Alert

```bash
# CPU usage > 90% for 5 minutes
echo "Investigating high CPU usage..."

# Identify top CPU consumers
top -o %CPU -n 1 | head -20

# Check for runaway processes
ps aux --sort=-%cpu | head -10

# If specific service is consuming high CPU
pkill -f problematic_service.py
python mcp_servers/problematic_service.py &
```

#### High Memory Usage Alert

```bash
# Memory usage > 95%
echo "Investigating high memory usage..."

# Identify memory consumers
ps aux --sort=-%mem | head -20

# Clear caches
echo 3 > /proc/sys/vm/drop_caches

# Check for memory leaks
python scripts/memory_leak_detector.py
```

#### Database Connection Alert

```bash
# Database connection failures
echo "Investigating database connectivity..."

# Check database status
systemctl status postgresql
pg_isready -h localhost -p 5432

# Check connection count
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Restart if necessary
sudo systemctl restart postgresql
```

### Performance Monitoring

```bash
#!/bin/bash
# performance_monitor.sh

echo "📊 Performance Monitoring Report - $(date)"
echo "=========================================="

# System metrics
echo "System Metrics:"
echo "  CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')%"
echo "  Memory Usage: $(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')%"
echo "  Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"
echo "  Load Average: $(uptime | awk -F'load average:' '{print $2}')"

# Service response times
echo "Service Response Times:"
for port in 8001 8010 8011 8012 8013; do
    response_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:$port/health)
    echo "  Port $port: ${response_time}s"
done

# Database performance
echo "Database Performance:"
psql -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';" | grep -E '[0-9]+'
```

---

## Maintenance Procedures

### Planned Maintenance

```bash
#!/bin/bash
# planned_maintenance.sh

MAINTENANCE_TYPE=$1

echo "🔧 Starting planned maintenance: $MAINTENANCE_TYPE"

# 1. Notify users
curl -X POST http://localhost:8100/alerts/maintenance-start

# 2. Graceful shutdown
echo "Initiating graceful shutdown..."
./scripts/graceful_shutdown.sh

# 3. Perform maintenance
case $MAINTENANCE_TYPE in
    "security-update")
        apt update && apt upgrade -y
        ;;
    "database-maintenance")
        ./scripts/database_maintenance.sh
        ;;
    "log-rotation")
        ./scripts/rotate_logs.sh
        ;;
esac

# 4. Restart services
echo "Restarting services..."
./scripts/startup.sh

# 5. Verify functionality
echo "Verifying functionality..."
./scripts/post_maintenance_check.sh

# 6. Notify completion
curl -X POST http://localhost:8100/alerts/maintenance-complete

echo "✅ Planned maintenance completed"
```

### Log Management

```bash
#!/bin/bash
# log_management.sh

echo "📝 Log Management - $(date)"

# Rotate logs
logrotate /etc/logrotate.d/trading-platform

# Archive old logs
find /var/log/trading-platform/ -name "*.log.*" -mtime +30 -exec gzip {} \;

# Clean up old archives
find /var/log/trading-platform/ -name "*.gz" -mtime +90 -delete

# Backup important logs
tar -czf /opt/backups/logs_$(date +%Y%m%d).tar.gz /var/log/trading-platform/

echo "✅ Log management completed"
```

---

## Contact Information and Escalation

### Primary Contacts

- **Operations Team**: ops@company.com
- **Development Team**: dev@company.com
- **Security Team**: security@company.com
- **Database Team**: dba@company.com

### Escalation Matrix

1. **Level 1** (0-15 minutes): Operations team
2. **Level 2** (15-30 minutes): Senior operations + Development team lead
3. **Level 3** (30+ minutes): CTO + All hands

### Emergency Contacts

- **Emergency Hotline**: +1-XXX-XXX-XXXX
- **On-call Engineer**: Available 24/7 via PagerDuty
- **Management Escalation**: Available via emergency hotline

---

This operational runbook provides comprehensive procedures for managing the MCP Trading Platform. Keep this document updated as systems evolve and new procedures are developed.