"""
Proof Evaluator Agent
Evaluates customer-submitted proof/documents to determine legitimacy
Uses LLM to analyze proof and make decision
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ProofEvaluatorAgent(BaseAgent):
    """
    Proof Evaluator Agent
    
    Responsibilities:
    - Evaluate customer-submitted proof/documents
    - Use LLM to determine legitimacy
    - Make resolution decision (RESOLVED or ESCALATED_TO_BRANCH)
    - Generate evaluation rationale
    - Update alert status
    """
    
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """Initialize Proof Evaluator Agent"""
        super().__init__("ProofEvaluator", broadcast_fn)
    
    async def execute(self, alert_id: str, proof_text: str, proof_type: str,
                     original_resolution: Dict, findings: Dict, context: Dict) -> Dict:
        """
        Execute proof evaluation (required by BaseAgent)
        
        This is a wrapper around evaluate_proof to satisfy the abstract method requirement
        """
        return await self.evaluate_proof(
            alert_id, proof_text, proof_type, original_resolution, findings, context
        )
    
    async def evaluate_proof(
        self,
        alert_id: str,
        proof_text: str,
        proof_type: str,
        original_resolution: Dict,
        findings: Dict,
        context: Dict
    ) -> Dict:
        """
        Evaluate customer-submitted proof
        
        Args:
            alert_id: Alert ID
            proof_text: Customer's explanation/proof text
            proof_type: Type of proof (e.g., "EXPLANATION", "DOCUMENT_DESCRIPTION")
            original_resolution: Original resolution that triggered RFI
            findings: Original investigation findings
            context: Customer context
            
        Returns:
            Evaluation result with decision and rationale
        """
        self.reset_chain_of_thought()
        
        self.logger.info(f"🔍 Evaluating proof for alert {alert_id}")
        
        try:
            # Step 1: Use LLM to evaluate proof
            llm_evaluation = await self._evaluate_with_llm(
                alert_id, proof_text, proof_type, original_resolution, findings, context
            )
            
            # Step 2: Determine decision
            if llm_evaluation.get("legitimate", False):
                decision = "RESOLVED"
                confidence = llm_evaluation.get("confidence", 0.8)
                rationale = llm_evaluation.get("rationale", "Proof accepted - transaction appears legitimate")
                new_status = "RESOLVED"
            else:
                decision = "ESCALATED_TO_BRANCH"
                confidence = llm_evaluation.get("confidence", 0.7)
                rationale = llm_evaluation.get("rationale", "Proof insufficient - requires branch verification")
                new_status = "ESCALATED_TO_BRANCH"
            
            # Step 3: Update alert status
            await self._update_alert_status(alert_id, new_status)
            
            # Step 4: Log evaluation
            self.log_chain_of_thought(
                "Proof Evaluation Complete",
                {
                    "alert_id": alert_id,
                    "decision": decision,
                    "confidence": confidence,
                    "rationale": rationale
                }
            )
            
            result = {
                "alert_id": alert_id,
                "decision": decision,
                "status": new_status,
                "confidence": confidence,
                "rationale": rationale,
                "llm_reasoning": llm_evaluation.get("reasoning", ""),
                "evaluated_at": datetime.now().isoformat()
            }
            
            # Emit evaluation event
            await self.emit_event("proof_evaluated", {
                "alert_id": alert_id,
                "decision": decision,
                "status": new_status
            })
            
            self.logger.info(f"✓ Proof evaluation: {decision} (confidence: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            error_details = self.handle_error(e, "Proof evaluation")
            return {"error": str(e), **error_details}
    
    async def _evaluate_with_llm(
        self,
        alert_id: str,
        proof_text: str,
        proof_type: str,
        original_resolution: Dict,
        findings: Dict,
        context: Dict
    ) -> Dict:
        """Use LLM to evaluate proof legitimacy"""
        
        try:
            from services.llm_service import get_llm_service
            llm_service = get_llm_service()
            
            if not llm_service.is_enabled():
                # Fallback: Basic rule-based evaluation
                return self._evaluate_without_llm(proof_text, findings, context)
            
            from langchain.schema import HumanMessage, SystemMessage
            import json
            
            prompt = f"""
Evaluate the legitimacy of customer-submitted proof for a banking compliance alert.

ALERT DETAILS:
- Alert ID: {alert_id}
- Scenario: {findings.get('scenario', 'Unknown')}
- Original Resolution: {original_resolution.get('recommendation', 'RFI')}
- Original Rationale: {original_resolution.get('rationale', 'N/A')}

INVESTIGATION FINDINGS:
{json.dumps(findings, indent=2)}

CUSTOMER CONTEXT:
- KYC Risk: {context.get('kyc_risk', 'N/A')}
- Occupation: {context.get('occupation', 'N/A')}
- Profile Age: {context.get('profile_age_days', 0)} days

CUSTOMER PROOF/EXPLANATION:
{proof_text}

PROOF TYPE: {proof_type}

TASK:
Evaluate if the customer's proof/explanation is legitimate and sufficient to resolve the alert.

Consider:
1. Does the explanation align with the transaction patterns?
2. Is the proof credible and consistent?
3. Are there any red flags or inconsistencies?
4. Is the explanation reasonable for the customer's profile?
5. Would this require further verification?

Respond in JSON format:
{{
    "legitimate": true/false,
    "confidence": 0.0-1.0,
    "rationale": "Brief explanation of decision",
    "reasoning": "Detailed analysis of why the proof is/isn't sufficient",
    "red_flags": ["list of any concerns"],
    "recommendation": "RESOLVED" or "ESCALATED_TO_BRANCH"
}}
            """
            
            messages = [
                SystemMessage(content="""You are a compliance analyst evaluating customer-submitted proof.
Your role:
- Determine if customer explanations are legitimate
- Identify inconsistencies or red flags
- Make decisions on whether to resolve or escalate
- Be thorough but fair in evaluation

Guidelines:
- Legitimate explanations should be consistent with transaction patterns
- Look for reasonable business or personal justifications
- Flag suspicious or inconsistent explanations
- Consider customer profile and history
- When in doubt, recommend branch verification"""),
                HumanMessage(content=prompt)
            ]
            
            response = llm_service.chat_model(messages)
            llm_response = response.content.strip()
            
            # Parse LLM response
            evaluation = self._parse_llm_response(llm_response)
            
            self.logger.info(f"LLM proof evaluation: legitimate={evaluation.get('legitimate')}, confidence={evaluation.get('confidence', 0.5):.2f}")
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"LLM evaluation failed: {e}", exc_info=True)
            # Fallback to rule-based
            return self._evaluate_without_llm(proof_text, findings, context)
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        import json
        
        try:
            # Extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            parsed = json.loads(json_str)
            
            return {
                "legitimate": parsed.get("legitimate", False),
                "confidence": float(parsed.get("confidence", 0.5)),
                "rationale": parsed.get("rationale", ""),
                "reasoning": parsed.get("reasoning", ""),
                "red_flags": parsed.get("red_flags", []),
                "recommendation": parsed.get("recommendation", "ESCALATED_TO_BRANCH")
            }
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse LLM response: {e}. Response: {response[:200]}")
            # Fallback: try to determine from text
            legitimate = "legitimate" in response.lower() and "true" in response.lower()
            return {
                "legitimate": legitimate,
                "confidence": 0.5,
                "rationale": "LLM evaluation completed",
                "reasoning": response[:500],
                "red_flags": [],
                "recommendation": "RESOLVED" if legitimate else "ESCALATED_TO_BRANCH"
            }
    
    def _evaluate_without_llm(self, proof_text: str, findings: Dict, context: Dict) -> Dict:
        """Fallback rule-based evaluation when LLM unavailable"""
        
        # Basic heuristics
        proof_lower = proof_text.lower()
        
        # Positive indicators
        positive_keywords = ["invoice", "receipt", "contract", "salary", "payment", "legitimate", "business", "explanation"]
        positive_count = sum(1 for keyword in positive_keywords if keyword in proof_lower)
        
        # Negative indicators
        negative_keywords = ["don't know", "not sure", "unclear", "confused", "suspicious"]
        negative_count = sum(1 for keyword in negative_keywords if keyword in proof_lower)
        
        # Length check (very short explanations are suspicious)
        is_sufficient = len(proof_text.strip()) > 50
        
        # Decision logic
        if positive_count >= 2 and negative_count == 0 and is_sufficient:
            legitimate = True
            confidence = 0.7
            rationale = "Proof contains legitimate explanations and sufficient detail"
        elif negative_count > 0 or not is_sufficient:
            legitimate = False
            confidence = 0.6
            rationale = "Proof is insufficient or contains concerning statements"
        else:
            legitimate = False
            confidence = 0.5
            rationale = "Proof requires further verification"
        
        return {
            "legitimate": legitimate,
            "confidence": confidence,
            "rationale": rationale,
            "reasoning": "Rule-based evaluation (LLM unavailable)",
            "red_flags": [] if legitimate else ["Requires verification"],
            "recommendation": "RESOLVED" if legitimate else "ESCALATED_TO_BRANCH"
        }
    
    async def _update_alert_status(self, alert_id: str, new_status: str):
        """Update alert status in database"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        SET a.status = $status,
            a.resolved_at = CASE 
                WHEN $status = 'RESOLVED' THEN datetime() 
                ELSE a.resolved_at 
            END,
            a.updated_at = datetime()
        RETURN a
        """
        
        await self.query_database(query, {
            "alert_id": alert_id,
            "status": new_status
        })
        
        self.logger.info(f"✓ Updated alert {alert_id} status to {new_status}")

