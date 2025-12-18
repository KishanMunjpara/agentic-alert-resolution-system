"""
System Guardrails and Security Controls
Implements security guardrails, input validation, and output sanitization
"""

import logging
import re
from typing import Dict, Optional, List, Any
from datetime import datetime
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class SystemGuardrails:
    """
    System Guardrails for Security and Safety
    
    Features:
    - Input validation and sanitization
    - Output validation
    - Rate limiting
    - Content filtering
    - Audit logging
    - Anomaly detection
    """
    
    def __init__(self):
        """Initialize System Guardrails"""
        # Rate limiting
        self.request_counts = defaultdict(int)
        self.request_timestamps = defaultdict(list)
        
        # Content validation patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
        ]
        
        # Audit log
        self.audit_log = []
        self.max_audit_log_size = 10000
        
        logger.info("✓ System Guardrails initialized")
    
    def validate_input(self, data: Any, field_name: str = "input") -> Tuple[bool, Optional[str]]:
        """
        Validate and sanitize input data
        
        Args:
            data: Input data to validate
            field_name: Name of the field being validated
            
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        if data is None:
            return True, None
        
        # Convert to string for pattern matching
        data_str = str(data)
        
        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                self._log_security_event("SQL_INJECTION_ATTEMPT", field_name, data_str)
                return False, f"Potential SQL injection detected in {field_name}"
        
        # Check for XSS patterns
        for pattern in self.xss_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                self._log_security_event("XSS_ATTEMPT", field_name, data_str)
                return False, f"Potential XSS attack detected in {field_name}"
        
        # Check for excessive length (DoS prevention)
        max_length = 100000
        if len(data_str) > max_length:
            return False, f"Input too long (max {max_length} characters)"
        
        return True, None
    
    def sanitize_output(self, data: Any) -> Any:
        """
        Sanitize output data before sending to client
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            # Remove potential script tags
            data = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE | re.DOTALL)
            # Remove javascript: protocol
            data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
            # Remove data: URLs
            data = re.sub(r'data:[^;]*;base64,', '', data, flags=re.IGNORECASE)
        elif isinstance(data, dict):
            return {k: self.sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_output(item) for item in data]
        
        return data
    
    def check_rate_limit(
        self, 
        identifier: str, 
        max_requests: int = 100, 
        window_seconds: int = 60
    ) -> Tuple[bool, Optional[str]]:
        """
        Check rate limit for an identifier
        
        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            (allowed: bool, reason: Optional[str])
        """
        now = datetime.now()
        
        # Clean old timestamps
        self.request_timestamps[identifier] = [
            ts for ts in self.request_timestamps[identifier]
            if (now - ts).total_seconds() < window_seconds
        ]
        
        # Check limit
        if len(self.request_timestamps[identifier]) >= max_requests:
            self._log_security_event("RATE_LIMIT_EXCEEDED", identifier, f"{max_requests} requests in {window_seconds}s")
            return False, f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds"
        
        # Add current request
        self.request_timestamps[identifier].append(now)
        self.request_counts[identifier] += 1
        
        return True, None
    
    def validate_alert_data(self, alert_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate alert data before processing
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        required_fields = ["alert_id", "scenario_code", "customer_id", "account_id"]
        
        # Check required fields
        for field in required_fields:
            if field not in alert_data:
                return False, f"Missing required field: {field}"
        
        # Validate each field
        for field, value in alert_data.items():
            is_valid, error = self.validate_input(value, field)
            if not is_valid:
                return False, error
        
        # Validate scenario_code
        valid_scenarios = [
            "VELOCITY_SPIKE", "STRUCTURING", "KYC_INCONSISTENCY",
            "SANCTIONS_HIT", "DORMANT_ACTIVATION"
        ]
        if alert_data.get("scenario_code") not in valid_scenarios:
            return False, f"Invalid scenario_code: {alert_data.get('scenario_code')}"
        
        # Validate alert_id format
        alert_id = alert_data.get("alert_id", "")
        if not re.match(r'^[A-Z0-9\-_]+$', alert_id):
            return False, "Invalid alert_id format (alphanumeric, hyphens, underscores only)"
        
        return True, None
    
    def validate_resolution_output(self, resolution: Dict) -> Dict:
        """
        Validate and sanitize resolution output
        
        Args:
            resolution: Resolution dictionary
            
        Returns:
            Sanitized resolution dictionary
        """
        # Sanitize all string fields
        sanitized = self.sanitize_output(resolution)
        
        # Ensure required fields exist
        required_fields = ["recommendation", "rationale", "confidence"]
        for field in required_fields:
            if field not in sanitized:
                sanitized[field] = None
        
        # Validate recommendation
        valid_recommendations = ["ESCALATE", "RFI", "IVR", "CLOSE", "BLOCK"]
        if sanitized.get("recommendation") not in valid_recommendations:
            logger.warning(f"Invalid recommendation: {sanitized.get('recommendation')}")
            sanitized["recommendation"] = "RFI"  # Default safe value
        
        # Validate confidence (0-1)
        confidence = sanitized.get("confidence", 0)
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            logger.warning(f"Invalid confidence: {confidence}, defaulting to 0.5")
            sanitized["confidence"] = 0.5
        
        return sanitized
    
    def _log_security_event(self, event_type: str, identifier: str, details: str):
        """Log security event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "identifier": identifier,
            "details": details
        }
        
        self.audit_log.append(event)
        
        # Limit audit log size
        if len(self.audit_log) > self.max_audit_log_size:
            self.audit_log = self.audit_log[-self.max_audit_log_size:]
        
        logger.warning(f"Security event: {event_type} - {identifier} - {details}")
    
    def get_security_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get security audit log"""
        return self.audit_log[-limit:]
    
    def get_rate_limit_status(self, identifier: str) -> Dict:
        """Get rate limit status for an identifier"""
        now = datetime.now()
        timestamps = self.request_timestamps.get(identifier, [])
        
        # Count requests in last minute
        recent_count = len([
            ts for ts in timestamps
            if (now - ts).total_seconds() < 60
        ])
        
        return {
            "identifier": identifier,
            "requests_last_minute": recent_count,
            "total_requests": self.request_counts.get(identifier, 0)
        }


# Singleton instance
_guardrails: Optional[SystemGuardrails] = None


def get_guardrails() -> SystemGuardrails:
    """Get singleton SystemGuardrails instance"""
    global _guardrails
    if _guardrails is None:
        _guardrails = SystemGuardrails()
    return _guardrails

