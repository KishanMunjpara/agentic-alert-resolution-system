"""
Pydantic Schemas for API Request/Response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ScenarioEnum(str, Enum):
    """Alert scenario types"""
    VELOCITY_SPIKE = "VELOCITY_SPIKE"
    STRUCTURING = "STRUCTURING"
    KYC_INCONSISTENCY = "KYC_INCONSISTENCY"
    SANCTIONS_HIT = "SANCTIONS_HIT"
    DORMANT_ACTIVATION = "DORMANT_ACTIVATION"


class AlertStatusEnum(str, Enum):
    """Alert status"""
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_PROOF = "AWAITING_PROOF"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    ESCALATED_TO_BRANCH = "ESCALATED_TO_BRANCH"


class ResolutionEnum(str, Enum):
    """Resolution recommendations"""
    ESCALATE = "ESCALATE"
    RFI = "RFI"
    IVR = "IVR"
    CLOSE = "CLOSE"
    BLOCK = "BLOCK"


class SeverityEnum(str, Enum):
    """Alert severity"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class KYCRiskEnum(str, Enum):
    """KYC Risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserRegisterResponse(BaseModel):
    """User registration response"""
    success: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None


class UserLoginRequest(BaseModel):
    """User login request"""
    username: str
    password: str


class UserLoginResponse(BaseModel):
    """User login response"""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    user_id: Optional[str] = None
    error: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response"""
    success: bool
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertCreateRequest(BaseModel):
    """Create new alert request"""
    alert_id: str
    scenario_code: ScenarioEnum
    customer_id: str
    account_id: str
    severity: SeverityEnum = SeverityEnum.MEDIUM
    description: Optional[str] = None


class AlertResponse(BaseModel):
    """Alert response"""
    alert_id: str
    scenario_code: str
    customer_id: str
    account_id: str
    status: str
    severity: str
    risk_score: Optional[float] = None
    created_at: datetime
    started_investigating_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """List alerts response"""
    total: int
    alerts: List[AlertResponse]


class AlertInvestigateRequest(BaseModel):
    """Start investigation request"""
    force: bool = False


class AlertInvestigateResponse(BaseModel):
    """Investigation started response"""
    alert_id: str
    status: str
    investigation_started_at: datetime
    message: Optional[str] = None


# ============================================================================
# RESOLUTION SCHEMAS
# ============================================================================

class FindingsSchema(BaseModel):
    """Investigation findings"""
    alert_id: str
    scenario: str
    transaction_count: Optional[int] = None
    total_amount: Optional[float] = None
    threshold_exceeded: Optional[bool] = None


class ContextSchema(BaseModel):
    """Customer context"""
    alert_id: str
    customer_id: str
    kyc_risk: str
    occupation: Optional[str] = None
    declared_income: Optional[float] = None
    profile_age_days: Optional[int] = None


class ResolutionResponse(BaseModel):
    """Resolution response"""
    resolution_id: str
    alert_id: str
    recommendation: str
    rationale: str
    confidence: float = Field(..., ge=0, le=1)
    created_at: datetime
    findings: Dict
    context: Dict

    class Config:
        from_attributes = True


# ============================================================================
# WEBSOCKET EVENT SCHEMAS
# ============================================================================

class WebSocketEventSchema(BaseModel):
    """WebSocket event"""
    event: str
    timestamp: datetime
    data: Dict

    class Config:
        from_attributes = True


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class AlertMetricsResponse(BaseModel):
    """Alert metrics for dashboard"""
    total_alerts: int
    open_alerts: int
    investigating_alerts: int
    resolved_alerts: int


class AlertsByScenarioResponse(BaseModel):
    """Alerts grouped by scenario"""
    VELOCITY_SPIKE: int = 0
    STRUCTURING: int = 0
    KYC_INCONSISTENCY: int = 0
    SANCTIONS_HIT: int = 0
    DORMANT_ACTIVATION: int = 0


class ResolutionDistributionResponse(BaseModel):
    """Resolution distribution"""
    ESCALATE: int = 0
    CLOSE: int = 0
    RFI: int = 0
    BLOCK: int = 0


class DashboardMetricsResponse(BaseModel):
    """Dashboard metrics"""
    total_alerts: int
    alerts_by_status: Dict
    alerts_by_scenario: AlertsByScenarioResponse
    resolution_distribution: ResolutionDistributionResponse
    avg_resolution_time_seconds: float


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict] = None


# ============================================================================
# PROOF SUBMISSION SCHEMAS
# ============================================================================

class ProofSubmissionRequest(BaseModel):
    """Request to submit proof for alert"""
    proof_text: str = Field(..., min_length=10, max_length=5000, description="Customer's explanation or proof description")
    proof_type: str = Field(default="EXPLANATION", description="Type of proof (EXPLANATION, DOCUMENT_DESCRIPTION, etc.)")
    customer_email: Optional[str] = Field(None, description="Customer email for verification")


class ProofEvaluationResponse(BaseModel):
    """Response from proof evaluation"""
    alert_id: str
    decision: str = Field(..., description="RESOLVED or ESCALATED_TO_BRANCH")
    status: str
    confidence: float = Field(..., ge=0, le=1)
    rationale: str
    message: str
    timestamp: datetime


class EvaluationReportResponse(BaseModel):
    """Response containing evaluation report"""
    alert_id: str
    report_content: str = Field(..., description="Full formatted evaluation report")
    metadata: Dict = Field(default_factory=dict, description="Report metadata")
    next_steps: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)
    format: str = Field(default="text", description="Report format (text, pdf, html)")
    can_send_email: bool = Field(default=False, description="Whether email can be sent to customer")
    email_sent: bool = Field(default=False, description="Whether email has been sent")
    email_sent_at: Optional[datetime] = None
    email_sent_to: Optional[str] = Field(default=None, description="Email address report was sent to")

