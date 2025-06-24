#!/usr/bin/env python3
"""
Enhanced Security, Compliance, and Audit Logging System
Comprehensive security monitoring and compliance tracking for MCP servers
"""

import asyncio
import json
import logging
import os
import uuid
import hashlib
import hmac
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from pydantic import BaseModel, Field
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/security_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Security & Compliance System",
    description="Enhanced security monitoring and compliance tracking",
    version="1.0.0"
)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.cival.ai"]
)

security = HTTPBearer()

# Enums
class SecurityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"

class EventType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    API_ACCESS = "api_access"
    DATA_ACCESS = "data_access"
    TRADE_EXECUTION = "trade_execution"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_ALERT = "security_alert"
    COMPLIANCE_CHECK = "compliance_check"
    SYSTEM_ERROR = "system_error"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

class ComplianceFramework(str, Enum):
    SOX = "sox"  # Sarbanes-Oxley
    PCI_DSS = "pci_dss"  # Payment Card Industry
    GDPR = "gdpr"  # General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    FINRA = "finra"  # Financial Industry Regulatory Authority
    SEC = "sec"  # Securities and Exchange Commission
    BASEL_III = "basel_iii"  # Basel III banking regulations

class RiskLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Data models
@dataclass
class AuditEvent:
    id: str
    timestamp: str
    event_type: EventType
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: str
    user_agent: Optional[str]
    resource: str
    action: str
    result: str  # success, failure, error
    security_level: SecurityLevel
    details: Dict[str, Any]
    compliance_frameworks: List[ComplianceFramework]
    risk_score: float
    hash_signature: str

@dataclass
class SecurityAlert:
    id: str
    timestamp: str
    alert_type: str
    severity: RiskLevel
    source: str
    description: str
    details: Dict[str, Any]
    affected_systems: List[str]
    recommended_actions: List[str]
    auto_remediated: bool
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class ComplianceReport:
    id: str
    framework: ComplianceFramework
    period_start: str
    period_end: str
    generated_at: str
    total_events: int
    compliant_events: int
    violations: List[Dict[str, Any]]
    compliance_score: float
    recommendations: List[str]
    next_review_date: str

@dataclass
class UserSession:
    session_id: str
    user_id: str
    created_at: str
    last_activity: str
    ip_address: str
    user_agent: str
    permissions: List[str]
    security_clearance: SecurityLevel
    expires_at: str
    is_active: bool

class SecurityConfig(BaseModel):
    jwt_secret: str = Field(default="your-secret-key", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=8, description="JWT expiration in hours")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(default=30, description="Account lockout duration")
    password_min_length: int = Field(default=12, description="Minimum password length")
    require_mfa: bool = Field(default=True, description="Require multi-factor authentication")
    audit_retention_days: int = Field(default=2555, description="Audit log retention (7 years)")

class LoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    mfa_token: Optional[str] = Field(None, description="MFA token")

class SecurityComplianceService:
    def __init__(self):
        self.config = SecurityConfig()
        self.audit_events: List[AuditEvent] = []
        self.security_alerts: List[SecurityAlert] = []
        self.compliance_reports: Dict[str, ComplianceReport] = {}
        self.active_sessions: Dict[str, UserSession] = {}
        self.failed_login_attempts: Dict[str, List[datetime]] = {}
        self.encryption_key = self._generate_encryption_key()
        
        # User database (in production, this would be a proper database)
        self.users = {
            "admin": {
                "password_hash": bcrypt.hashpw("AdminPass123!".encode(), bcrypt.gensalt()).decode(),
                "security_clearance": SecurityLevel.TOP_SECRET,
                "permissions": ["read", "write", "admin", "trade", "compliance"],
                "mfa_enabled": True,
                "created_at": datetime.now().isoformat()
            },
            "trader": {
                "password_hash": bcrypt.hashpw("TraderPass123!".encode(), bcrypt.gensalt()).decode(),
                "security_clearance": SecurityLevel.CONFIDENTIAL,
                "permissions": ["read", "trade"],
                "mfa_enabled": True,
                "created_at": datetime.now().isoformat()
            },
            "analyst": {
                "password_hash": bcrypt.hashpw("AnalystPass123!".encode(), bcrypt.gensalt()).decode(),
                "security_clearance": SecurityLevel.INTERNAL,
                "permissions": ["read"],
                "mfa_enabled": False,
                "created_at": datetime.now().isoformat()
            }
        }
        
    def _generate_encryption_key(self) -> Fernet:
        """Generate encryption key for sensitive data"""
        password = b"encryption-password-key"
        salt = b"salt_"  # In production, use a random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return Fernet(key)
    
    def _calculate_hash_signature(self, data: Dict[str, Any]) -> str:
        """Calculate hash signature for audit trail integrity"""
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    async def authenticate_user(self, username: str, password: str, mfa_token: Optional[str] = None) -> Optional[str]:
        """Authenticate user and return session token"""
        # Check failed login attempts
        now = datetime.now()
        if username in self.failed_login_attempts:
            recent_attempts = [
                attempt for attempt in self.failed_login_attempts[username]
                if now - attempt < timedelta(minutes=self.config.lockout_duration_minutes)
            ]
            
            if len(recent_attempts) >= self.config.max_login_attempts:
                await self._log_security_event(
                    EventType.UNAUTHORIZED_ACCESS,
                    username,
                    "Authentication failed - account locked",
                    {"reason": "too_many_attempts", "attempts": len(recent_attempts)}
                )
                raise HTTPException(status_code=423, detail="Account locked due to too many failed attempts")
        
        # Verify user credentials
        if username not in self.users:
            await self._record_failed_login(username, "user_not_found")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = self.users[username]
        
        # Verify password
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            await self._record_failed_login(username, "invalid_password")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify MFA if required
        if user["mfa_enabled"] and not mfa_token:
            raise HTTPException(status_code=428, detail="MFA token required")
        
        if user["mfa_enabled"] and mfa_token:
            # In production, verify MFA token with TOTP or similar
            if not self._verify_mfa_token(mfa_token):
                await self._record_failed_login(username, "invalid_mfa")
                raise HTTPException(status_code=401, detail="Invalid MFA token")
        
        # Create session
        session_id = str(uuid.uuid4())
        expires_at = now + timedelta(hours=self.config.jwt_expiration_hours)
        
        session = UserSession(
            session_id=session_id,
            user_id=username,
            created_at=now.isoformat(),
            last_activity=now.isoformat(),
            ip_address="127.0.0.1",  # Would get from request
            user_agent="test-agent",  # Would get from request
            permissions=user["permissions"],
            security_clearance=SecurityLevel(user["security_clearance"]),
            expires_at=expires_at.isoformat(),
            is_active=True
        )
        
        self.active_sessions[session_id] = session
        
        # Clear failed login attempts
        if username in self.failed_login_attempts:
            del self.failed_login_attempts[username]
        
        # Generate JWT token
        token_payload = {
            "session_id": session_id,
            "user_id": username,
            "permissions": user["permissions"],
            "security_clearance": user["security_clearance"],
            "exp": expires_at
        }
        
        token = jwt.encode(token_payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
        
        await self._log_security_event(
            EventType.LOGIN,
            username,
            "User login successful",
            {"session_id": session_id, "security_clearance": user["security_clearance"]}
        )
        
        return token
    
    def _verify_mfa_token(self, token: str) -> bool:
        """Verify MFA token (simplified implementation)"""
        # In production, this would verify TOTP, SMS, or hardware token
        return token == "123456"  # Mock verification
    
    async def _record_failed_login(self, username: str, reason: str):
        """Record failed login attempt"""
        now = datetime.now()
        
        if username not in self.failed_login_attempts:
            self.failed_login_attempts[username] = []
        
        self.failed_login_attempts[username].append(now)
        
        await self._log_security_event(
            EventType.UNAUTHORIZED_ACCESS,
            username,
            "Authentication failed",
            {"reason": reason, "timestamp": now.isoformat()}
        )
    
    async def verify_session(self, credentials: HTTPAuthorizationCredentials) -> UserSession:
        """Verify JWT token and return session"""
        try:
            token = credentials.credentials
            payload = jwt.decode(token, self.config.jwt_secret, algorithms=[self.config.jwt_algorithm])
            
            session_id = payload.get("session_id")
            if not session_id or session_id not in self.active_sessions:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            session = self.active_sessions[session_id]
            
            # Check if session is still active and not expired
            now = datetime.now()
            expires_at = datetime.fromisoformat(session.expires_at.replace('Z', '+00:00').replace('+00:00', ''))
            
            if not session.is_active or now > expires_at:
                del self.active_sessions[session_id]
                raise HTTPException(status_code=401, detail="Session expired")
            
            # Update last activity
            session.last_activity = now.isoformat()
            
            return session
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def _log_security_event(self, event_type: EventType, user_id: Optional[str], 
                                 action: str, details: Dict[str, Any], 
                                 security_level: SecurityLevel = SecurityLevel.INTERNAL):
        """Log security event for audit trail"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Determine applicable compliance frameworks
        compliance_frameworks = []
        if event_type in [EventType.LOGIN, EventType.LOGOUT, EventType.API_ACCESS]:
            compliance_frameworks.extend([ComplianceFramework.SOX, ComplianceFramework.FINRA])
        if event_type == EventType.DATA_ACCESS:
            compliance_frameworks.extend([ComplianceFramework.GDPR, ComplianceFramework.CCPA])
        if event_type == EventType.TRADE_EXECUTION:
            compliance_frameworks.extend([ComplianceFramework.SEC, ComplianceFramework.FINRA])
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(event_type, details)
        
        event_data = {
            "id": event_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "user_id": user_id,
            "action": action,
            "details": details,
            "security_level": security_level.value,
            "risk_score": risk_score
        }
        
        hash_signature = self._calculate_hash_signature(event_data)
        
        audit_event = AuditEvent(
            id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            user_id=user_id,
            session_id=details.get("session_id"),
            source_ip="127.0.0.1",  # Would get from request
            user_agent="system",  # Would get from request
            resource=details.get("resource", "system"),
            action=action,
            result=details.get("result", "success"),
            security_level=security_level,
            details=details,
            compliance_frameworks=compliance_frameworks,
            risk_score=risk_score,
            hash_signature=hash_signature
        )
        
        self.audit_events.append(audit_event)
        
        # Generate security alert if high risk
        if risk_score >= 0.8:
            await self._generate_security_alert(event_type, details, risk_score)
        
        # Log to file for external SIEM systems
        logger.info(f"AUDIT_EVENT: {json.dumps(asdict(audit_event), default=str)}")
    
    def _calculate_risk_score(self, event_type: EventType, details: Dict[str, Any]) -> float:
        """Calculate risk score for an event"""
        base_scores = {
            EventType.LOGIN: 0.1,
            EventType.LOGOUT: 0.05,
            EventType.API_ACCESS: 0.2,
            EventType.DATA_ACCESS: 0.3,
            EventType.TRADE_EXECUTION: 0.7,
            EventType.CONFIGURATION_CHANGE: 0.8,
            EventType.SECURITY_ALERT: 0.9,
            EventType.UNAUTHORIZED_ACCESS: 1.0,
            EventType.SYSTEM_ERROR: 0.4
        }
        
        score = base_scores.get(event_type, 0.5)
        
        # Adjust based on details
        if details.get("result") == "failure":
            score += 0.3
        
        if details.get("reason") == "too_many_attempts":
            score += 0.4
        
        if details.get("security_clearance") == SecurityLevel.TOP_SECRET.value:
            score += 0.1
        
        return min(1.0, score)
    
    async def _generate_security_alert(self, event_type: EventType, details: Dict[str, Any], risk_score: float):
        """Generate security alert for high-risk events"""
        alert_id = str(uuid.uuid4())
        
        severity = RiskLevel.CRITICAL if risk_score >= 0.9 else RiskLevel.HIGH
        
        alert = SecurityAlert(
            id=alert_id,
            timestamp=datetime.now().isoformat(),
            alert_type=f"high_risk_{event_type.value}",
            severity=severity,
            source="security_monitoring",
            description=f"High-risk {event_type.value} event detected",
            details=details,
            affected_systems=["mcp_servers"],
            recommended_actions=[
                "Review event details",
                "Verify user identity",
                "Check for additional suspicious activity",
                "Consider temporary access restriction"
            ],
            auto_remediated=False
        )
        
        self.security_alerts.append(alert)
        
        logger.warning(f"SECURITY_ALERT: {json.dumps(asdict(alert), default=str)}")
    
    async def generate_compliance_report(self, framework: ComplianceFramework, 
                                       start_date: datetime, end_date: datetime) -> ComplianceReport:
        """Generate compliance report for specified framework and period"""
        report_id = str(uuid.uuid4())
        
        # Filter events for the framework and period
        relevant_events = []
        for event in self.audit_events:
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00').replace('+00:00', ''))
            if (start_date <= event_time <= end_date and 
                framework in event.compliance_frameworks):
                relevant_events.append(event)
        
        total_events = len(relevant_events)
        
        # Check compliance violations
        violations = []
        compliant_events = 0
        
        for event in relevant_events:
            is_compliant = True
            
            # Framework-specific compliance checks
            if framework == ComplianceFramework.SOX:
                # SOX requires proper access controls and audit trails
                if event.event_type == EventType.CONFIGURATION_CHANGE and not event.user_id:
                    violations.append({
                        "event_id": event.id,
                        "violation_type": "unauthorized_configuration_change",
                        "description": "Configuration change without proper user identification"
                    })
                    is_compliant = False
            
            elif framework == ComplianceFramework.GDPR:
                # GDPR requires consent and data protection
                if event.event_type == EventType.DATA_ACCESS and event.security_level == SecurityLevel.PUBLIC:
                    # Check if personal data access is properly authorized
                    if "personal_data" in event.details and not event.details.get("consent"):
                        violations.append({
                            "event_id": event.id,
                            "violation_type": "gdpr_consent_missing",
                            "description": "Personal data access without proper consent"
                        })
                        is_compliant = False
            
            elif framework == ComplianceFramework.FINRA:
                # FINRA requires trade supervision and record keeping
                if event.event_type == EventType.TRADE_EXECUTION:
                    if not event.details.get("supervisor_approval"):
                        violations.append({
                            "event_id": event.id,
                            "violation_type": "finra_supervision_missing",
                            "description": "Trade execution without supervisor approval"
                        })
                        is_compliant = False
            
            if is_compliant:
                compliant_events += 1
        
        # Calculate compliance score
        compliance_score = (compliant_events / total_events) * 100 if total_events > 0 else 100
        
        # Generate recommendations
        recommendations = []
        if compliance_score < 100:
            recommendations.append("Review and address compliance violations")
        if compliance_score < 90:
            recommendations.append("Implement additional controls and monitoring")
        if compliance_score < 80:
            recommendations.append("Conduct comprehensive compliance audit")
        
        # Next review date (quarterly for most frameworks)
        next_review = end_date + timedelta(days=90)
        
        report = ComplianceReport(
            id=report_id,
            framework=framework,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            generated_at=datetime.now().isoformat(),
            total_events=total_events,
            compliant_events=compliant_events,
            violations=violations,
            compliance_score=compliance_score,
            recommendations=recommendations,
            next_review_date=next_review.isoformat()
        )
        
        self.compliance_reports[report_id] = report
        
        await self._log_security_event(
            EventType.COMPLIANCE_CHECK,
            None,
            f"Generated {framework.value} compliance report",
            {
                "report_id": report_id,
                "compliance_score": compliance_score,
                "violations_count": len(violations)
            }
        )
        
        return report
    
    async def get_security_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive security dashboard data"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Filter recent events
        recent_events_24h = [
            e for e in self.audit_events
            if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00').replace('+00:00', '')) >= last_24h
        ]
        
        recent_events_7d = [
            e for e in self.audit_events
            if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00').replace('+00:00', '')) >= last_7d
        ]
        
        # Recent alerts
        recent_alerts = [
            a for a in self.security_alerts
            if datetime.fromisoformat(a.timestamp.replace('Z', '+00:00').replace('+00:00', '')) >= last_24h
        ]
        
        # Active sessions
        active_session_count = len([s for s in self.active_sessions.values() if s.is_active])
        
        # Event statistics
        event_types_24h = {}
        for event in recent_events_24h:
            event_types_24h[event.event_type.value] = event_types_24h.get(event.event_type.value, 0) + 1
        
        # Risk distribution
        risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for event in recent_events_24h:
            if event.risk_score < 0.3:
                risk_distribution["low"] += 1
            elif event.risk_score < 0.6:
                risk_distribution["medium"] += 1
            elif event.risk_score < 0.9:
                risk_distribution["high"] += 1
            else:
                risk_distribution["critical"] += 1
        
        # Compliance status
        compliance_status = {}
        for framework in ComplianceFramework:
            # Check recent compliance (simplified)
            compliance_events = [
                e for e in recent_events_7d
                if framework in e.compliance_frameworks
            ]
            violations = len([e for e in compliance_events if e.risk_score > 0.7])
            total = len(compliance_events)
            
            compliance_status[framework.value] = {
                "total_events": total,
                "violations": violations,
                "compliance_rate": ((total - violations) / total * 100) if total > 0 else 100
            }
        
        return {
            "timestamp": now.isoformat(),
            "overview": {
                "total_audit_events": len(self.audit_events),
                "events_last_24h": len(recent_events_24h),
                "events_last_7d": len(recent_events_7d),
                "active_sessions": active_session_count,
                "security_alerts_24h": len(recent_alerts),
                "unresolved_alerts": len([a for a in self.security_alerts if not a.resolved])
            },
            "event_breakdown_24h": event_types_24h,
            "risk_distribution_24h": risk_distribution,
            "compliance_status": compliance_status,
            "recent_alerts": [asdict(a) for a in recent_alerts[-10:]],  # Last 10 alerts
            "system_health": {
                "authentication_failures_24h": len([e for e in recent_events_24h if e.event_type == EventType.UNAUTHORIZED_ACCESS]),
                "high_risk_events_24h": len([e for e in recent_events_24h if e.risk_score > 0.7]),
                "avg_risk_score_24h": sum(e.risk_score for e in recent_events_24h) / len(recent_events_24h) if recent_events_24h else 0
            }
        }

# Initialize service
security_service = SecurityComplianceService()

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserSession:
    return await security_service.verify_session(credentials)

# API Endpoints
@app.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    try:
        token = await security_service.authenticate_user(
            request.username, 
            request.password, 
            request.mfa_token
        )
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.post("/auth/logout")
async def logout(current_user: UserSession = Depends(get_current_user)):
    """Logout user and invalidate session"""
    if current_user.session_id in security_service.active_sessions:
        security_service.active_sessions[current_user.session_id].is_active = False
        del security_service.active_sessions[current_user.session_id]
    
    await security_service._log_security_event(
        EventType.LOGOUT,
        current_user.user_id,
        "User logout",
        {"session_id": current_user.session_id}
    )
    
    return {"message": "Logged out successfully"}

@app.get("/security/dashboard")
async def get_security_dashboard(current_user: UserSession = Depends(get_current_user)):
    """Get comprehensive security dashboard"""
    if "admin" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    dashboard = await security_service.get_security_dashboard()
    
    await security_service._log_security_event(
        EventType.API_ACCESS,
        current_user.user_id,
        "Security dashboard accessed",
        {"resource": "security_dashboard"}
    )
    
    return dashboard

@app.get("/audit/events")
async def get_audit_events(
    limit: int = 100,
    event_type: Optional[EventType] = None,
    current_user: UserSession = Depends(get_current_user)
):
    """Get audit events with filtering"""
    if "admin" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    events = security_service.audit_events
    
    if event_type:
        events = [e for e in events if e.event_type == event_type]
    
    # Sort by timestamp (newest first)
    events.sort(key=lambda x: x.timestamp, reverse=True)
    
    await security_service._log_security_event(
        EventType.API_ACCESS,
        current_user.user_id,
        "Audit events accessed",
        {"resource": "audit_events", "filters": {"event_type": event_type.value if event_type else None}}
    )
    
    return {
        "events": [asdict(e) for e in events[:limit]],
        "total": len(events),
        "filtered": len(events) if event_type else len(security_service.audit_events)
    }

@app.get("/compliance/report/{framework}")
async def generate_compliance_report(
    framework: ComplianceFramework,
    days_back: int = 30,
    current_user: UserSession = Depends(get_current_user)
):
    """Generate compliance report for specified framework"""
    if "compliance" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    report = await security_service.generate_compliance_report(framework, start_date, end_date)
    
    return {"report": asdict(report)}

@app.get("/security/alerts")
async def get_security_alerts(
    limit: int = 50,
    resolved: Optional[bool] = None,
    current_user: UserSession = Depends(get_current_user)
):
    """Get security alerts with filtering"""
    if "admin" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    alerts = security_service.security_alerts
    
    if resolved is not None:
        alerts = [a for a in alerts if a.resolved == resolved]
    
    # Sort by timestamp (newest first)
    alerts.sort(key=lambda x: x.timestamp, reverse=True)
    
    await security_service._log_security_event(
        EventType.API_ACCESS,
        current_user.user_id,
        "Security alerts accessed",
        {"resource": "security_alerts", "filters": {"resolved": resolved}}
    )
    
    return {
        "alerts": [asdict(a) for a in alerts[:limit]],
        "total": len(alerts),
        "unresolved": len([a for a in security_service.security_alerts if not a.resolved])
    }

@app.put("/security/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: UserSession = Depends(get_current_user)
):
    """Acknowledge a security alert"""
    if "admin" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    for alert in security_service.security_alerts:
        if alert.id == alert_id:
            alert.acknowledged = True
            
            await security_service._log_security_event(
                EventType.SECURITY_ALERT,
                current_user.user_id,
                "Security alert acknowledged",
                {"alert_id": alert_id, "alert_type": alert.alert_type}
            )
            
            return {"message": "Alert acknowledged"}
    
    raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Security & Compliance System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "security_compliance_system:app",
        host="0.0.0.0",
        port=8030,
        reload=True,
        log_level="info"
    )