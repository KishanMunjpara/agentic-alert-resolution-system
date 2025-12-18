"""
Adjudicator Agent - Spoke
Evaluates SOPs and makes resolution decisions
"""

import logging
import os
from typing import Dict, Optional, Callable
import uuid
from datetime import datetime
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AdjudicatorAgent(BaseAgent):
    """
    Adjudicator Agent (Spoke)
    
    Responsibilities:
    - Retrieve applicable SOPs
    - Evaluate SOP conditions
    - Apply decision logic
    - Generate rationale
    - Create resolution node
    - Emit decision event
    """
    
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """Initialize Adjudicator Agent"""
        super().__init__("Adjudicator", broadcast_fn)
    
    async def execute(self, alert_id: str, scenario_code: str, 
                     findings: Dict, context: Dict) -> Dict:
        """
        Make resolution decision
        
        Args:
            alert_id: Alert being adjudicated
            scenario_code: Alert scenario
            findings: Findings from Investigator
            context: Context from Context Gatherer
            
        Returns:
            Resolution decision with rationale and confidence
        """
        self.reset_chain_of_thought()
        
        self.logger.info(f"⚖️ Adjudicator evaluating {scenario_code}...")
        
        try:
            # Get applicable SOPs
            sops = await self._get_applicable_sops(scenario_code)
            self.log_chain_of_thought(
                "SOPs Retrieved",
                {"scenario": scenario_code, "sop_count": len(sops)}
            )
            
            # Log findings and context for debugging
            self.logger.info(f"Evaluating SOPs for {scenario_code}")
            self.logger.info(f"Findings: {findings}")
            self.logger.info(f"Context: {context}")
            self.logger.info(f"Found {len(sops)} SOPs to evaluate")
            
            # Evaluate each SOP
            decision = None
            matched_sop = None
            confidence = 0
            rationale = ""
            
            for sop in sops:
                sop_result = await self._evaluate_sop(
                    sop, scenario_code, findings, context
                )
                
                self.log_chain_of_thought(
                    f"SOP Evaluated: {sop.get('rule_id')}",
                    {
                        "rule_id": sop.get("rule_id"),
                        "matched": sop_result["matched"],
                        "confidence": sop_result["confidence"],
                        "rationale": sop_result["rationale"]
                    }
                )
                
                self.logger.info(f"SOP {sop.get('rule_id')}: matched={sop_result['matched']}, "
                               f"confidence={sop_result['confidence']}, "
                               f"rationale={sop_result['rationale']}")
                
                # If this SOP matches and has higher confidence, use it
                if sop_result["matched"] and sop_result["confidence"] > confidence:
                    decision = sop["action"]
                    matched_sop = sop
                    confidence = sop_result["confidence"]
                    rationale = sop_result["rationale"]
                    self.logger.info(f"✓ SOP matched: {sop.get('rule_id')} -> {decision}")
            
            # If no SOP matched, try LLM for edge case handling
            if decision is None:
                # Try LLM for edge case handling
                llm_decision = None
                try:
                    from services.llm_service import get_llm_service
                    llm_service = get_llm_service()
                    
                    if llm_service.is_enabled():
                        self.logger.info("No SOP matched - using LLM for edge case handling")
                        llm_decision = await llm_service.handle_edge_case(
                            scenario_code, findings, context, sops
                        )
                        
                        if llm_decision:
                            decision = llm_decision.get("recommendation", "RFI")
                            confidence = llm_decision.get("confidence", 0.5)
                            rationale = llm_decision.get("rationale", "LLM-based decision for edge case")
                            
                            self.log_chain_of_thought(
                                "LLM Edge Case Decision",
                                {
                                    "decision": decision,
                                    "confidence": confidence,
                                    "llm_reasoning": llm_decision.get("llm_reasoning", "")
                                }
                            )
                            self.logger.info(f"LLM decision: {decision} (confidence: {confidence:.2f})")
                except Exception as e:
                    self.logger.debug(f"LLM edge case handling not available: {e}")
                
                # Fallback to default RFI if LLM didn't provide decision
                if decision is None:
                    decision = "RFI"
                    confidence = 0.5
                    rationale = "No applicable SOP matched. Requesting information from customer."
                    self.log_chain_of_thought(
                        "No SOP Match - Default Decision",
                        {"decision": "RFI", "findings": findings, "context": context}
                    )
                    self.logger.warning(f"No SOP matched for {scenario_code}. Findings: {findings}, Context: {context}")
            else:
                self.log_chain_of_thought(
                    "SOP Matched",
                    {
                        "rule_id": matched_sop.get("rule_id"),
                        "decision": decision,
                        "confidence": confidence
                    }
                )
            
            # Enhance rationale with LLM if available
            try:
                from services.llm_service import get_llm_service
                llm_service = get_llm_service()
                
                if llm_service.is_enabled() and os.getenv("LLM_ENHANCE_RATIONALE", "false").lower() == "true":
                    enhanced_rationale = await llm_service.generate_enhanced_rationale(
                        decision, findings, context, matched_sop
                    )
                    if enhanced_rationale:
                        rationale = enhanced_rationale
                        self.logger.info("Rationale enhanced with LLM")
            except Exception as e:
                self.logger.debug(f"LLM rationale enhancement not available: {e}")
            
            # Create resolution in Neo4j
            resolution_id = await self._create_resolution(
                alert_id, scenario_code, decision, rationale, 
                confidence, findings, context, 
                matched_sop.get("rule_id") if matched_sop else None
            )
            
            resolution = {
                "resolution_id": resolution_id,
                "alert_id": alert_id,
                "recommendation": decision,
                "rationale": rationale,
                "confidence": confidence,
                "findings": findings,
                "context": context,
                "matched_sop": matched_sop.get("rule_id") if matched_sop else None
            }
            
            # Emit decision event
            await self.emit_event("decision_made", {
                "alert_id": alert_id,
                "resolution": resolution
            })
            
            self.logger.info(f"✓ Decision: {decision} (confidence: {confidence:.2f})")
            
            return resolution
            
        except Exception as e:
            error_details = self.handle_error(e, "Adjudication")
            return {"error": str(e), **error_details}
    
    async def _get_applicable_sops(self, scenario_code: str) -> list:
        """Get SOPs applicable to scenario"""
        query = """
        MATCH (s:SOP)
        WHERE s.scenario_code = $scenario_code AND s.active = true
        RETURN s
        ORDER BY s.priority ASC
        """
        
        try:
            results = await self.query_database(query, 
                                               {"scenario_code": scenario_code})
            sops = [dict(record["s"]) for record in results]
            self.logger.debug(f"Retrieved {len(sops)} SOPs for {scenario_code}")
            return sops
        except Exception as e:
            self.logger.error(f"Failed to get SOPs: {e}")
            return []
    
    async def _evaluate_sop(self, sop: Dict, scenario_code: str,
                           findings: Dict, context: Dict) -> Dict:
        """
        Evaluate if SOP condition is met
        Uses rule-based evaluation with optional LLM enhancement
        
        Args:
            sop: SOP rule to evaluate
            scenario_code: Alert scenario
            findings: Investigation findings
            context: Customer context
            
        Returns:
            Evaluation result with matched flag and rationale
        """
        try:
            condition_logic = sop.get("condition_logic", "")
            rule_name = sop.get("rule_name", "Unknown")
            
            # Build evaluation context
            eval_context = {
                "findings": findings,
                "context": context,
                "scenario": scenario_code
            }
            
            # Step 1: Rule-based evaluation (primary)
            matched = self._evaluate_sop_condition(
                sop, scenario_code, condition_logic, findings, context
            )
            
            # Step 2: Always use LLM for confidence scoring when enabled
            llm_enhancement = None
            try:
                from services.llm_service import get_llm_service
                llm_service = get_llm_service()
                
                if llm_service.is_enabled():
                    # Always use LLM to calculate confidence score
                    llm_enhancement = await llm_service.evaluate_sop_with_llm(
                        sop, findings, context, scenario_code, rule_based_match=matched
                    )
                    
                    # If LLM provides different match result for complex cases, consider it
                    if llm_enhancement.get("llm_used") and not matched:
                        # LLM might catch edge cases rule-based logic misses
                        if llm_enhancement.get("matched") and llm_enhancement.get("confidence", 0) > 0.7:
                            matched = True
                            self.logger.info(f"LLM enhanced evaluation: SOP {sop.get('rule_id')} matched via LLM")
            except Exception as e:
                self.logger.debug(f"LLM evaluation not available or failed: {e}")
            
            # Determine confidence and rationale
            # Priority: LLM confidence > Rule-based defaults
            if llm_enhancement and llm_enhancement.get("llm_used"):
                # Use LLM-provided confidence and rationale
                confidence = llm_enhancement.get("confidence", 0.5)
                rationale = llm_enhancement.get("rationale", f"SOP matched: {rule_name}" if matched else f"SOP condition not met: {rule_name}")
                self.logger.info(f"Using LLM confidence score: {confidence:.2f} for SOP {sop.get('rule_id')}")
            elif matched:
                # Fallback: Rule-based match without LLM
                confidence = 0.95
                rationale = f"SOP matched: {rule_name}"
                self.logger.info(f"Using default confidence score: {confidence:.2f} (LLM not available)")
            else:
                # Fallback: No match without LLM
                confidence = 0
                rationale = f"SOP condition not met: {rule_name}"
                self.logger.info(f"Using default confidence score: {confidence:.2f} (LLM not available)")
            
            result = {
                "matched": matched,
                "confidence": confidence,
                "rationale": rationale
            }
            
            # Add LLM reasoning if available
            if llm_enhancement and llm_enhancement.get("llm_used"):
                result["llm_reasoning"] = llm_enhancement.get("llm_reasoning", "")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate SOP: {e}")
            return {"matched": False, "confidence": 0, "rationale": str(e)}
    
    def _is_complex_case(self, findings: Dict, context: Dict) -> bool:
        """
        Determine if this is a complex case that might benefit from LLM reasoning
        
        Args:
            findings: Investigation findings
            context: Customer context
            
        Returns:
            True if case is complex
        """
        # Complex cases:
        # - Multiple conflicting indicators
        # - Unusual patterns
        # - Edge cases in data
        
        # Check for conflicting indicators
        if findings.get("error") or context.get("error"):
            return True
        
        # Check for unusual patterns
        if findings.get("scenario") == "STRUCTURING":
            # Complex structuring cases
            if findings.get("linked_accounts_aggregate", 0) > 0 and findings.get("is_legitimate_business"):
                return True
        
        # Check for missing or incomplete data
        if len([k for k, v in findings.items() if v is None]) > 2:
            return True
        
        return False
    
    def _evaluate_sop_condition(self, sop: Dict, scenario_code: str, condition_logic: str,
                               findings: Dict, context: Dict) -> bool:
        """
        Evaluate specific SOP condition logic
        First tries to evaluate based on rule_id for precise matching, falls back to general logic
        """
        rule_id = sop.get("rule_id", "")
        
        # VELOCITY_SPIKE - Specific SOP matching
        if rule_id == "SOP-A001-01":
            # High Velocity High Risk Escalation
            # Condition: transaction_count >= 5 AND total_amount > 25000 AND kyc_risk == HIGH
            return (findings.get("transaction_count", 0) >= 5 and 
                    findings.get("total_amount", 0) > 25000 and 
                    context.get("kyc_risk") == "HIGH")
        elif rule_id == "SOP-A001-02":
            # Known Business Cycle Close
            # Condition: is_business_cycle == True
            return findings.get("is_business_cycle") == True
        
        # STRUCTURING - Specific SOP matching
        elif rule_id == "SOP-A002-01":
            # Linked Accounts Aggregate Escalation - only match if linked_accounts_aggregate > 28000
            return findings.get("linked_accounts_aggregate", 0) > 28000
        elif rule_id == "SOP-A002-02":
            # Legitimate Business RFI - match if is_legitimate_business is True
            return findings.get("is_legitimate_business") == True
        
        # KYC_INCONSISTENCY - Specific SOP matching
        elif rule_id == "SOP-A003-01":
            # Jeweler/Precious Metals Trader Close
            return (context.get("occupation") in ["Jeweler", "Precious Metals Trader", "Jeweler/Goldsmith"] and
                    findings.get("is_precious_metals") == True)
        elif rule_id == "SOP-A003-02":
            # Teacher/Student Escalation
            return (context.get("occupation") in ["Teacher", "Student", "Government Employee"] and
                    findings.get("is_precious_metals") == True)
        
        # SANCTIONS_HIT - Specific SOP matching
        elif rule_id == "SOP-A004-01":
            # High Match Score Escalation
            return (findings.get("match_score", 0) >= 0.90 or
                    context.get("jurisdiction") == "HIGH_RISK")
        elif rule_id == "SOP-A004-02":
            # Proven False Positive Close
            return findings.get("is_false_positive") == True
        
        # DORMANT_ACTIVATION - Specific SOP matching
        elif rule_id == "SOP-A005-01":
            # Low Risk IVR
            return context.get("kyc_risk") == "LOW"
        elif rule_id == "SOP-A005-02":
            # High Risk International Escalation
            return (context.get("kyc_risk") == "HIGH" and
                    findings.get("is_international_withdrawal") == True)
        
        # Fall back to general scenario evaluation for other SOPs
        return self._evaluate_condition(scenario_code, condition_logic, findings, context)
    
    def _evaluate_condition(self, scenario_code: str, condition_logic: str,
                           findings: Dict, context: Dict) -> bool:
        """
        Evaluate SOP condition logic (fallback for non-specific SOPs)
        Implements specific logic for each alert scenario
        """
        
        # A-001: Velocity Spike
        if scenario_code == "VELOCITY_SPIKE":
            # High Velocity + High Risk = ESCALATE
            if (findings.get("transaction_count", 0) >= 5 and 
                findings.get("total_amount", 0) > 25000 and 
                context.get("kyc_risk") == "HIGH"):
                return True
            # Known business cycle = CLOSE
            if findings.get("is_business_cycle") == True:
                return True
            return False
        
        # A-002: Structuring (fallback - specific SOPs handled in _evaluate_sop_condition)
        elif scenario_code == "STRUCTURING":
            # This is a fallback - specific SOP evaluation is done in _evaluate_sop_condition
            # For general structuring pattern detection
            if findings.get("linked_accounts_aggregate", 0) > 28000:
                return True
            if findings.get("is_legitimate_business") == True:
                return True
            return False
        
        # A-003: KYC Inconsistency
        elif scenario_code == "KYC_INCONSISTENCY":
            # Jeweler with Precious Metals transaction = CLOSE
            if (context.get("occupation") in ["Jeweler", "Precious Metals Trader", "Jeweler/Goldsmith"] and
                findings.get("is_precious_metals") == True):
                return True
            # Teacher with Precious Metals = ESCALATE
            if (context.get("occupation") in ["Teacher", "Student", "Government Employee"] and
                findings.get("is_precious_metals") == True):
                return True
            return False
        
        # A-004: Sanctions Hit
        elif scenario_code == "SANCTIONS_HIT":
            # High match score or high-risk jurisdiction = ESCALATE
            if (findings.get("match_score", 0) >= 0.80 or
                context.get("jurisdiction") == "HIGH_RISK"):
                return True
            # Proven false positive = CLOSE
            if findings.get("is_false_positive") == True:
                return True
            return False
        
        # A-005: Dormant Activation
        elif scenario_code == "DORMANT_ACTIVATION":
            # Low risk = RFI
            if context.get("kyc_risk") == "LOW":
                return True
            # High risk + international withdrawal = ESCALATE
            if (context.get("kyc_risk") == "HIGH" and
                findings.get("is_international_withdrawal") == True):
                return True
            return False
        
        return False
    
    async def _create_resolution(self, alert_id: str, scenario_code: str,
                                recommendation: str, rationale: str,
                                confidence: float, findings: Dict,
                                context: Dict, matched_sop: Optional[str]) -> str:
        """Create resolution node in Neo4j"""
        import json
        resolution_id = f"res-{uuid.uuid4().hex[:8]}"
        
        # Build query with optional SOP relationship
        if matched_sop:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})
            CREATE (r:Resolution {
                resolution_id: $resolution_id,
                recommendation: $recommendation,
                rationale: $rationale,
                confidence_score: $confidence,
                sop_matched: $sop_matched,
                investigator_findings: $findings_str,
                context_data: $context_str,
                created_at: $timestamp
            })
            CREATE (a)-[:HAS_RESOLUTION]->(r)
            WITH r
            MATCH (s:SOP {rule_id: $sop_id})
            CREATE (r)-[:MATCHED_SOP]->(s)
            RETURN r.resolution_id as resolution_id
            """
        else:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})
            CREATE (r:Resolution {
                resolution_id: $resolution_id,
                recommendation: $recommendation,
                rationale: $rationale,
                confidence_score: $confidence,
                sop_matched: $sop_matched,
                investigator_findings: $findings_str,
                context_data: $context_str,
                created_at: $timestamp
            })
            CREATE (a)-[:HAS_RESOLUTION]->(r)
            RETURN r.resolution_id as resolution_id
            """
        
        # Convert findings and context to JSON strings
        try:
            findings_json = json.dumps(findings) if findings else "{}"
        except (TypeError, ValueError):
            findings_json = str(findings)
        
        try:
            context_json = json.dumps(context) if context else "{}"
        except (TypeError, ValueError):
            context_json = str(context)
        
        params = {
            "alert_id": alert_id,
            "resolution_id": resolution_id,
            "recommendation": recommendation,
            "rationale": rationale,
            "confidence": confidence,
            "sop_matched": matched_sop,
            "findings_str": findings_json,
            "context_str": context_json,
            "timestamp": datetime.now().isoformat()
        }
        
        # Only add sop_id if matched_sop is provided
        if matched_sop:
            params["sop_id"] = matched_sop
        
        try:
            # Use execute_write for write operations
            result = await self.write_to_database(query, params)
            self.logger.debug(f"Resolution created: {resolution_id}")
            return resolution_id
        except Exception as e:
            self.logger.error(f"Failed to create resolution: {e}")
            # Still return the ID so the investigation can continue
            return resolution_id

