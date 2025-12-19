"""
System Malfunction Handler
Handles system failures, errors, and recovery mechanisms
"""

import logging
import asyncio
from typing import Dict, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


class MalfunctionSeverity(Enum):
    """Malfunction severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MalfunctionType(Enum):
    """Types of system malfunctions"""
    DATABASE_CONNECTION = "DATABASE_CONNECTION"
    AGENT_FAILURE = "AGENT_FAILURE"
    EMAIL_SERVICE_FAILURE = "EMAIL_SERVICE_FAILURE"
    WEBSOCKET_FAILURE = "WEBSOCKET_FAILURE"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class MalfunctionEvent:
    """Malfunction event record"""
    event_id: str
    malfunction_type: MalfunctionType
    severity: MalfunctionSeverity
    alert_id: Optional[str]
    component: str
    error_message: str
    timestamp: datetime
    resolved: bool = False
    resolution_action: Optional[str] = None
    retry_count: int = 0


class CircuitBreaker:
    """
    Circuit Breaker pattern for preventing cascading failures
    """
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """
        Initialize Circuit Breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception(f"Circuit breaker is OPEN. Retry after {self.timeout_seconds - elapsed:.0f} seconds")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                logger.info("Circuit breaker closed after successful call")
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            raise


class SystemMalfunctionHandler:
    """
    System Malfunction Handler
    
    Features:
    - Error detection and classification
    - Automatic retry with exponential backoff
    - Circuit breaker pattern
    - Dead letter queue for failed operations
    - Alert escalation
    - Manual intervention triggers
    """
    
    def __init__(self):
        """Initialize System Malfunction Handler"""
        self.malfunction_events: List[MalfunctionEvent] = []
        self.dead_letter_queue: List[Dict] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.max_retries = 3
        self.max_dlq_size = 1000
        
        logger.info("✓ System Malfunction Handler initialized")
    
    def _create_circuit_breaker(self, component: str) -> CircuitBreaker:
        """Get or create circuit breaker for component"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = CircuitBreaker(
                failure_threshold=5,
                timeout_seconds=60
            )
        return self.circuit_breakers[component]
    
    def check_circuit(self, component: str) -> bool:
        """
        Check if circuit breaker allows execution
        
        Args:
            component: Component name
            
        Returns:
            True if circuit is closed (allows execution), False if open
        """
        circuit_breaker = self._create_circuit_breaker(component)
        
        if circuit_breaker.state == "OPEN":
            # Check if timeout has passed
            if circuit_breaker.last_failure_time:
                elapsed = (datetime.now() - circuit_breaker.last_failure_time).total_seconds()
                if elapsed >= circuit_breaker.timeout_seconds:
                    circuit_breaker.state = "HALF_OPEN"
                    logger.info(f"Circuit breaker transitioning to HALF_OPEN for {component}")
                    return True
                else:
                    return False
            else:
                return False
        
        return True  # CLOSED or HALF_OPEN allows execution
    
    def trip_circuit(self, component: str):
        """Manually trip circuit breaker for a component"""
        circuit_breaker = self._create_circuit_breaker(component)
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure_time = datetime.now()
        
        if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
            circuit_breaker.state = "OPEN"
            logger.warning(f"Circuit breaker OPENED for {component} after {circuit_breaker.failure_count} failures")
    
    def reset_circuit(self, component: str):
        """Reset circuit breaker for a component"""
        if component in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[component]
            circuit_breaker.failure_count = 0
            if circuit_breaker.state != "CLOSED":
                circuit_breaker.state = "CLOSED"
                logger.info(f"Circuit breaker reset for {component}")
    
    def record_malfunction(
        self,
        malfunction_type: MalfunctionType,
        severity: MalfunctionSeverity,
        component: str,
        error_message: str,
        alert_id: Optional[str] = None
    ) -> str:
        """
        Record a system malfunction
        
        Args:
            malfunction_type: Type of malfunction
            severity: Severity level
            component: Component that failed
            error_message: Error message
            alert_id: Associated alert ID (if any)
            
        Returns:
            Event ID
        """
        event_id = f"malf-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.malfunction_events)}"
        
        event = MalfunctionEvent(
            event_id=event_id,
            malfunction_type=malfunction_type,
            severity=severity,
            alert_id=alert_id,
            component=component,
            error_message=error_message,
            timestamp=datetime.now()
        )
        
        self.malfunction_events.append(event)
        
        # Log based on severity
        if severity == MalfunctionSeverity.CRITICAL:
            logger.critical(f"CRITICAL MALFUNCTION: {malfunction_type.value} in {component}: {error_message}")
        elif severity == MalfunctionSeverity.HIGH:
            logger.error(f"HIGH SEVERITY MALFUNCTION: {malfunction_type.value} in {component}: {error_message}")
        else:
            logger.warning(f"Malfunction: {malfunction_type.value} in {component}: {error_message}")
        
        # Auto-escalate critical issues
        if severity == MalfunctionSeverity.CRITICAL:
            self._escalate_to_manual_intervention(event)
        
        return event_id
    
    async def execute_with_retry(
        self,
        func: Callable,
        component: str,
        *args,
        **kwargs
    ) -> any:
        """
        Execute function with automatic retry and circuit breaker
        
        Args:
            func: Function to execute
            component: Component name for circuit breaker
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        circuit_breaker = self._create_circuit_breaker(component)
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Use circuit breaker
                result = circuit_breaker.call(func, *args, **kwargs)
                
                # Success
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt} retries: {component}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed for {component}: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # All retries failed
                    logger.error(f"All {self.max_retries} retries failed for {component}: {e}")
                    
                    # Determine severity
                    severity = MalfunctionSeverity.HIGH
                    if "timeout" in str(e).lower():
                        malfunction_type = MalfunctionType.TIMEOUT
                    elif "database" in str(e).lower() or "neo4j" in str(e).lower():
                        malfunction_type = MalfunctionType.DATABASE_CONNECTION
                        severity = MalfunctionSeverity.CRITICAL
                    else:
                        malfunction_type = MalfunctionType.UNKNOWN
                    
                    # Record malfunction
                    self.record_malfunction(
                        malfunction_type=malfunction_type,
                        severity=severity,
                        component=component,
                        error_message=str(e)
                    )
        
        # All retries exhausted
        raise last_exception
    
    async def execute_with_retry_async(
        self,
        func: Callable,
        component: str,
        *args,
        **kwargs
    ) -> any:
        """
        Execute async function with automatic retry and circuit breaker
        
        Args:
            func: Async function to execute
            component: Component name for circuit breaker
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        circuit_breaker = self._create_circuit_breaker(component)
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Check circuit breaker
                if not self.check_circuit(component):
                    raise Exception(f"Circuit breaker is OPEN for {component}")
                
                # Execute async function directly (circuit breaker doesn't work with async)
                result = await func(*args, **kwargs)
                
                # Reset circuit on success
                self.reset_circuit(component)
                
                # Success
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt} retries: {component}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Trip circuit on failure
                self.trip_circuit(component)
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed for {component}: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # All retries failed
                    logger.error(f"All {self.max_retries} retries failed for {component}: {e}")
                    
                    # Determine severity
                    severity = MalfunctionSeverity.HIGH
                    if "timeout" in str(e).lower():
                        malfunction_type = MalfunctionType.TIMEOUT
                    elif "database" in str(e).lower() or "neo4j" in str(e).lower():
                        malfunction_type = MalfunctionType.DATABASE_CONNECTION
                        severity = MalfunctionSeverity.CRITICAL
                    elif "email" in str(e).lower() or "smtp" in str(e).lower():
                        malfunction_type = MalfunctionType.EMAIL_SERVICE_FAILURE
                    else:
                        malfunction_type = MalfunctionType.UNKNOWN
                    
                    # Record malfunction
                    self.record_malfunction(
                        malfunction_type=malfunction_type,
                        severity=severity,
                        component=component,
                        error_message=str(e)
                    )
        
        # All retries exhausted
        raise last_exception
    
    def add_to_dead_letter_queue(self, operation: Dict):
        """
        Add failed operation to dead letter queue
        
        Args:
            operation: Operation data to queue
        """
        dlq_entry = {
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "retry_count": operation.get("retry_count", 0)
        }
        
        self.dead_letter_queue.append(dlq_entry)
        
        # Limit DLQ size
        if len(self.dead_letter_queue) > self.max_dlq_size:
            self.dead_letter_queue = self.dead_letter_queue[-self.max_dlq_size:]
        
        logger.warning(f"Operation added to dead letter queue: {operation.get('type', 'unknown')}")
    
    def _escalate_to_manual_intervention(self, event: MalfunctionEvent):
        """
        Escalate critical malfunction to manual intervention
        
        Args:
            event: Malfunction event
        """
        escalation = {
            "event_id": event.event_id,
            "malfunction_type": event.malfunction_type.value,
            "severity": event.severity.value,
            "component": event.component,
            "error_message": event.error_message,
            "alert_id": event.alert_id,
            "timestamp": event.timestamp.isoformat(),
            "action_required": "MANUAL_INTERVENTION",
            "recommended_actions": self._get_recommended_actions(event)
        }
        
        logger.critical(f"ESCALATION REQUIRED: {json.dumps(escalation, indent=2)}")
        
        # In production, this would:
        # 1. Send alert to on-call engineer
        # 2. Create incident ticket
        # 3. Notify management
        # 4. Log to monitoring system
    
    def _get_recommended_actions(self, event: MalfunctionEvent) -> List[str]:
        """Get recommended actions for malfunction"""
        actions = []
        
        if event.malfunction_type == MalfunctionType.DATABASE_CONNECTION:
            actions = [
                "Check Neo4j connection status",
                "Verify network connectivity",
                "Check database credentials",
                "Review connection pool settings",
                "Check for database maintenance"
            ]
        elif event.malfunction_type == MalfunctionType.AGENT_FAILURE:
            actions = [
                "Review agent logs",
                "Check agent dependencies",
                "Verify input data validity",
                "Review agent configuration"
            ]
        elif event.malfunction_type == MalfunctionType.EMAIL_SERVICE_FAILURE:
            actions = [
                "Check SMTP server status",
                "Verify email credentials",
                "Check rate limits",
                "Review email content"
            ]
        elif event.malfunction_type == MalfunctionType.TIMEOUT:
            actions = [
                "Check system load",
                "Review query performance",
                "Increase timeout settings",
                "Optimize slow operations"
            ]
        else:
            actions = [
                "Review error logs",
                "Check system health",
                "Verify configuration",
                "Contact support team"
            ]
        
        return actions
    
    def resolve_malfunction(self, event_id: str, resolution_action: str):
        """
        Mark malfunction as resolved
        
        Args:
            event_id: Event ID to resolve
            resolution_action: Action taken to resolve
        """
        for event in self.malfunction_events:
            if event.event_id == event_id:
                event.resolved = True
                event.resolution_action = resolution_action
                logger.info(f"Malfunction resolved: {event_id} - {resolution_action}")
                return
        
        logger.warning(f"Malfunction event not found: {event_id}")
    
    def get_malfunction_stats(self) -> Dict:
        """Get malfunction statistics"""
        total = len(self.malfunction_events)
        unresolved = len([e for e in self.malfunction_events if not e.resolved])
        
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        
        for event in self.malfunction_events:
            by_type[event.malfunction_type.value] += 1
            by_severity[event.severity.value] += 1
        
        return {
            "total_malfunctions": total,
            "unresolved": unresolved,
            "resolved": total - unresolved,
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "circuit_breakers": {
                name: {"state": cb.state, "failure_count": cb.failure_count}
                for name, cb in self.circuit_breakers.items()
            }
        }
    
    def get_recent_malfunctions(self, limit: int = 50) -> List[Dict]:
        """Get recent malfunction events"""
        recent = sorted(
            self.malfunction_events,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
        
        return [
            {
                "event_id": e.event_id,
                "malfunction_type": e.malfunction_type.value,
                "severity": e.severity.value,
                "component": e.component,
                "error_message": e.error_message,
                "alert_id": e.alert_id,
                "timestamp": e.timestamp.isoformat(),
                "resolved": e.resolved,
                "resolution_action": e.resolution_action
            }
            for e in recent
        ]


# Singleton instance
_malfunction_handler: Optional[SystemMalfunctionHandler] = None


def get_malfunction_handler() -> SystemMalfunctionHandler:
    """Get singleton SystemMalfunctionHandler instance"""
    global _malfunction_handler
    if _malfunction_handler is None:
        _malfunction_handler = SystemMalfunctionHandler()
    return _malfunction_handler

