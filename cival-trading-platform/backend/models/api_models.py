"""
Simplified API models for Phase 10 integration
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class APIResponse(BaseModel):
    """Generic API response model"""
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = datetime.now()