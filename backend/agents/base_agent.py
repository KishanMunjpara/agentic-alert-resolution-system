"""
Base Agent Class
Abstract base class for all agents in the multi-agent system
Provides common functionality for logging, event emission, and neo4j access
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from database.neo4j_connector import Neo4jConnector

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents
    
    Provides:
    - Event broadcasting via WebSocket
    - Chain-of-thought logging
    - Neo4j database access
    - Error handling
    """
    
    def __init__(self, name: str, broadcast_fn: Optional[Callable] = None):
        """
        Initialize agent
        
        Args:
            name: Agent name (for logging)
            broadcast_fn: Function to broadcast WebSocket events
                         Signature: async def broadcast_fn(event_type: str, data: dict)
        """
        self.name = name
        self.broadcast = broadcast_fn
        self.db = Neo4jConnector()
        self.logger = logging.getLogger(f"agent.{name.lower()}")
        self.chain_of_thought = []
        
        self.logger.info(f"✓ {self.name} Agent initialized")
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Main execution method - must be implemented by subclasses
        
        Returns:
            Agent-specific result data
        """
        pass
    
    async def emit_event(self, event_type: str, data: Dict) -> None:
        """
        Emit a WebSocket event for real-time updates and store in database
        
        Args:
            event_type: Type of event (e.g., 'investigator_finding')
            data: Event data to broadcast
        """
        # Store event in database first
        alert_id = data.get("alert_id")
        if alert_id:
            try:
                self.log_investigation_event(alert_id, event_type, data)
            except Exception as e:
                self.logger.warning(f"Failed to log event to database: {e}")
        
        # Then broadcast via WebSocket
        if self.broadcast is None:
            self.logger.debug(f"No broadcast function, skipping event: {event_type}")
            return
        
        try:
            await self.broadcast(event_type, data)
            self.logger.debug(f"Event emitted: {event_type}")
        except Exception as e:
            self.logger.error(f"Failed to emit event {event_type}: {e}")
    
    def log_chain_of_thought(self, step: str, details: Dict, confidence: float = 1.0) -> None:
        """
        Log a step in the agent's reasoning process
        
        Args:
            step: Step description
            details: Step details
            confidence: Confidence level (0-1)
        """
        thought = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "details": details,
            "confidence": confidence
        }
        self.chain_of_thought.append(thought)
        self.logger.info(f"[{self.name}] {step}: {details} (confidence: {confidence:.2f})")
    
    def get_chain_of_thought(self) -> list:
        """Get complete chain of thought"""
        return self.chain_of_thought
    
    def reset_chain_of_thought(self) -> None:
        """Reset chain of thought for next investigation"""
        self.chain_of_thought = []
    
    async def query_database(self, query: str, parameters: Optional[Dict] = None) -> list:
        """
        Execute a Cypher query on Neo4j
        
        Args:
            query: Cypher query
            parameters: Query parameters
            
        Returns:
            Query results
        """
        try:
            results = self.db.execute_query(query, parameters)
            self.logger.debug(f"Query executed: {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return []
    
    async def write_to_database(self, query: str, parameters: Optional[Dict] = None) -> Dict:
        """
        Execute a write transaction on Neo4j
        
        Args:
            query: Cypher write query
            parameters: Query parameters
            
        Returns:
            Transaction summary
        """
        try:
            summary = self.db.execute_write(query, parameters)
            self.logger.debug(f"Write transaction executed: {summary}")
            return summary
        except Exception as e:
            self.logger.error(f"Write transaction failed: {e}")
            return {}
    
    def log_investigation_event(self, alert_id: str, event_type: str, 
                               event_data: Dict) -> None:
        """
        Log an investigation event to Neo4j audit trail
        
        Args:
            alert_id: Alert being investigated
            event_type: Type of event
            event_data: Event details
        """
        import uuid
        from datetime import datetime
        
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        
        # Create Event node
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        CREATE (e:Event {
            event_id: $event_id,
            event_type: $event_type,
            alert_id: $alert_id,
            agent_name: $agent_name,
            event_data: $event_data,
            timestamp: $timestamp
        })
        CREATE (e)-[:FOR_ALERT]->(a)
        """
        
        # Convert event_data to JSON string if it's a dict
        import json
        if isinstance(event_data, dict):
            try:
                event_data_str = json.dumps(event_data)
            except (TypeError, ValueError):
                event_data_str = str(event_data)
        else:
            event_data_str = str(event_data)
        
        params = {
            "event_id": event_id,
            "event_type": event_type,
            "alert_id": alert_id,
            "agent_name": self.name,
            "event_data": event_data_str,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            self.db.execute_write(query, params)
            self.logger.debug(f"Event logged: {event_type}")
        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")
    
    def handle_error(self, error: Exception, context: str) -> Dict:
        """
        Handle agent errors gracefully
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            
        Returns:
            Error details dictionary
        """
        error_details = {
            "agent": self.name,
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.error(f"Error in {context}: {error}", exc_info=True)
        return error_details


class AgentResult:
    """
    Standardized result object for agent execution
    """
    
    def __init__(self, success: bool, data: Optional[Dict] = None, 
                 error: Optional[str] = None, chain_of_thought: Optional[list] = None):
        """
        Initialize agent result
        
        Args:
            success: Whether execution was successful
            data: Result data
            error: Error message if unsuccessful
            chain_of_thought: Agent's reasoning chain
        """
        self.success = success
        self.data = data or {}
        self.error = error
        self.chain_of_thought = chain_of_thought or []
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "chain_of_thought": self.chain_of_thought,
            "timestamp": self.timestamp
        }

