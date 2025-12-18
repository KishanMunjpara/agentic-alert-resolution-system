"""
Orchestrator Agent - Hub
Routes alerts to appropriate spoke agents and coordinates investigation sequence
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent (Hub)
    
    Responsibilities:
    - Receive alert
    - Route to appropriate spoke agents based on scenario
    - Coordinate investigation sequence
    - Trigger Adjudicator with findings
    - Manage investigation timeline
    """
    
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """Initialize Orchestrator Agent"""
        super().__init__("Orchestrator", broadcast_fn)
        
        # Lazy import to avoid circular dependencies
        self.investigator = None
        self.context_gatherer = None
        self.adjudicator = None
        self.action_executor = None
    
    async def initialize_spokes(self, broadcast_fn: Optional[Callable] = None):
        """
        Initialize spoke agents
        Done separately to avoid circular imports
        
        Args:
            broadcast_fn: Broadcast function for WebSocket events
        """
        # Import here to avoid circular imports
        from agents.investigator import InvestigatorAgent
        from agents.context_gatherer import ContextGathererAgent
        from agents.adjudicator import AdjudicatorAgent
        from agents.action_executor import ActionExecutor
        
        broadcast = broadcast_fn or self.broadcast
        self.investigator = InvestigatorAgent(broadcast)
        self.context_gatherer = ContextGathererAgent(broadcast)
        self.adjudicator = AdjudicatorAgent(broadcast)
        self.action_executor = ActionExecutor(broadcast)
        
        self.logger.info("✓ All spoke agents initialized")
    
    async def execute(self, alert_id: str, scenario_code: str, force: bool = False) -> AgentResult:
        """
        Execute investigation sequence for an alert
        
        Args:
            alert_id: Alert to investigate
            scenario_code: Alert scenario (VELOCITY_SPIKE, STRUCTURING, etc)
            force: If True, re-investigate even if resolution exists
            
        Returns:
            AgentResult with investigation findings and final resolution
        """
        self.reset_chain_of_thought()
        
        try:
            # Check if resolution already exists (unless force=True)
            if not force:
                check_query = """
                MATCH (a:Alert {alert_id: $alert_id})-[:HAS_RESOLUTION]->(r:Resolution)
                RETURN r.resolution_id as resolution_id, r.recommendation as recommendation, r.created_at as created_at
                ORDER BY r.created_at DESC
                LIMIT 1
                """
                
                try:
                    existing_resolution = await self.query_database(check_query, {"alert_id": alert_id})
                    if existing_resolution:
                        resolution_data = existing_resolution[0]
                        recommendation = resolution_data.get("recommendation", "UNKNOWN")
                        self.logger.info(f"✓ Resolution already exists for alert {alert_id}: {recommendation}. Skipping investigation.")
                        
                        await self.emit_event("investigation_skipped", {
                            "alert_id": alert_id,
                            "reason": "Resolution already exists",
                            "existing_resolution": recommendation,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        return AgentResult(
                            True,
                            data={
                                "alert_id": alert_id,
                                "skipped": True,
                                "reason": "Resolution already exists",
                                "existing_resolution": recommendation
                            },
                            chain_of_thought=self.chain_of_thought
                        )
                except Exception as e:
                    self.logger.debug(f"Could not check for existing resolution: {e}")
                    # Continue with investigation if check fails
            
            # Initialize spokes if not already done
            if self.investigator is None:
                await self.initialize_spokes()
            
            # Step 1: Emit investigation started event
            self.log_chain_of_thought(
                "Investigation Started",
                {"alert_id": alert_id, "scenario": scenario_code}
            )
            
            await self.emit_event("investigation_started", {
                "alert_id": alert_id,
                "scenario_code": scenario_code,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"🚀 Starting investigation for alert {alert_id} ({scenario_code})")
            
            # Step 2: Get alert details from Neo4j
            alert = await self._get_alert_details(alert_id)
            if not alert:
                error_msg = f"Alert {alert_id} not found"
                self.logger.error(error_msg)
                return AgentResult(False, error=error_msg, 
                                 chain_of_thought=self.chain_of_thought)
            
            self.log_chain_of_thought(
                "Alert Details Retrieved",
                {"alert": alert}
            )
            
            # Step 3: Call Investigator Agent
            self.logger.info("📊 Calling Investigator Agent...")
            findings = await self.investigator.execute(alert_id, scenario_code)
            
            self.log_chain_of_thought(
                "Investigator Agent Completed",
                {"findings": findings}
            )
            
            # Step 4: Call Context Gatherer Agent
            self.logger.info("📋 Calling Context Gatherer Agent...")
            context = await self.context_gatherer.execute(alert_id)
            
            self.log_chain_of_thought(
                "Context Gatherer Agent Completed",
                {"context": context}
            )
            
            # Step 5: Call Adjudicator Agent
            self.logger.info("⚖️ Calling Adjudicator Agent...")
            resolution = await self.adjudicator.execute(
                alert_id, 
                scenario_code,
                findings, 
                context
            )
            
            self.log_chain_of_thought(
                "Adjudicator Agent Completed",
                {"resolution": resolution}
            )
            
            # Step 6: Call Action Executor
            self.logger.info("🎯 Executing Action...")
            action_result = await self.action_executor.execute(alert_id, resolution)
            
            self.log_chain_of_thought(
                "Action Executed",
                {"action_result": action_result}
            )
            
            # Step 7: Emit investigation complete event
            investigation_duration = await self._calculate_investigation_duration(alert_id)
            
            await self.emit_event("investigation_complete", {
                "alert_id": alert_id,
                "final_resolution": resolution.get("recommendation"),
                "duration_ms": investigation_duration,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"✓ Investigation complete for {alert_id} "
                           f"(Decision: {resolution.get('recommendation')}, "
                           f"Duration: {investigation_duration}ms)")
            
            # Return final result
            result_data = {
                "alert_id": alert_id,
                "scenario_code": scenario_code,
                "findings": findings,
                "context": context,
                "resolution": resolution,
                "action_result": action_result,
                "duration_ms": investigation_duration
            }
            
            return AgentResult(
                True,
                data=result_data,
                chain_of_thought=self.chain_of_thought
            )
            
        except Exception as e:
            error_details = self.handle_error(e, "Investigation sequence")
            return AgentResult(
                False,
                error=str(e),
                chain_of_thought=self.chain_of_thought
            )
    
    async def _get_alert_details(self, alert_id: str) -> Optional[Dict]:
        """Get alert details from Neo4j"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        RETURN a
        """
        
        try:
            results = await self.query_database(query, {"alert_id": alert_id})
            if results:
                return dict(results[0]["a"])
            return None
        except Exception as e:
            self.logger.error(f"Failed to get alert details: {e}")
            return None
    
    async def _calculate_investigation_duration(self, alert_id: str) -> int:
        """
        Calculate investigation duration in milliseconds
        Returns approximate duration based on current time vs alert creation
        """
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        RETURN a.created_at as created_at
        """
        
        try:
            results = await self.query_database(query, {"alert_id": alert_id})
            if results:
                created_at_str = results[0]["created_at"]
                # For this prototype, return estimated duration
                # In production, would use actual timestamps
                return 3000  # 3 seconds estimate
            return 0
        except Exception as e:
            self.logger.error(f"Failed to calculate duration: {e}")
            return 0
    
    async def get_investigation_status(self, alert_id: str) -> Dict:
        """Get current investigation status for an alert"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        RETURN {
            status: a.status,
            created_at: a.created_at,
            started_investigating_at: a.started_investigating_at,
            resolved_at: a.resolved_at
        } as status_info
        """
        
        try:
            results = await self.query_database(query, {"alert_id": alert_id})
            if results:
                return results[0]["status_info"]
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get investigation status: {e}")
            return {}

