"""
LLM Service
Integrates OpenAI Large Language Models for enhanced reasoning and decision-making
Uses LangChain for OpenAI integration
"""

import logging
import os
from typing import Dict, Optional, List, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Try to import LangChain components
LANGCHAIN_AVAILABLE = False
LANGCHAIN_VERSION = None

try:
    # Try newer LangChain imports (0.1.0+) - langchain-openai package
    try:
        from langchain_openai import ChatOpenAI
        # Newer versions use langchain_core.messages instead of langchain.schema
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        except ImportError:
            # Fallback to old schema location
            from langchain.schema import HumanMessage, SystemMessage, AIMessage
        LANGCHAIN_AVAILABLE = True
        LANGCHAIN_VERSION = "new"
        logger.debug("✓ Detected LangChain 'new' version (langchain-openai)")
    except ImportError as e1:
        # Try older LangChain imports (0.0.350) - built-in chat_models
        try:
            from langchain.chat_models import ChatOpenAI
            from langchain.schema import HumanMessage, SystemMessage, AIMessage
            LANGCHAIN_AVAILABLE = True
            LANGCHAIN_VERSION = "old"
            logger.debug("✓ Detected LangChain 'old' version (langchain.chat_models)")
        except ImportError as e2:
            # Try alternative imports (very old versions)
            try:
                from langchain.llms import OpenAI
                from langchain.schema import HumanMessage, SystemMessage
                LANGCHAIN_AVAILABLE = True
                LANGCHAIN_VERSION = "legacy"
                logger.debug("✓ Detected LangChain 'legacy' version (langchain.llms)")
            except ImportError as e3:
                LANGCHAIN_AVAILABLE = False
                logger.debug(f"LangChain imports failed: new={e1}, old={e2}, legacy={e3}")
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    logger.debug(f"LangChain import error: {e}")

if not LANGCHAIN_AVAILABLE:
    logger.warning("LangChain not available. LLM features will be disabled.")


class LLMService:
    """
    LLM Service for Enhanced Reasoning using OpenAI
    
    Features:
    - OpenAI integration via LangChain
    - Chain-of-thought reasoning
    - SOP interpretation and evaluation
    - Rationale generation
    - Edge case handling
    - Cost tracking
    """
    
    def __init__(self):
        """Initialize LLM Service with OpenAI"""
        self.model_name = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))
        self.enabled = os.getenv("LLM_ENABLED", "false").lower() == "true"
        
        # OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Initialize LLM
        self.chat_model = None
        
        if self.enabled:
            if LANGCHAIN_AVAILABLE and LANGCHAIN_VERSION:
                try:
                    self._initialize_llm()
                    logger.info(f"✓ LLM Service initialized: OpenAI/{self.model_name} (LangChain: {LANGCHAIN_VERSION})")
                except Exception as e:
                    logger.error(f"✗ Failed to initialize LLM: {e}")
                    logger.error(f"  LangChain available: {LANGCHAIN_AVAILABLE}, Version: {LANGCHAIN_VERSION}")
                    self.enabled = False
            else:
                logger.warning(f"LangChain not properly configured. Available: {LANGCHAIN_AVAILABLE}, Version: {LANGCHAIN_VERSION}")
                logger.warning("LLM features disabled. Please install LangChain: pip install langchain>=0.0.350")
                self.enabled = False
        else:
            logger.info("LLM Service disabled (LLM_ENABLED=false)")
    
    def _initialize_llm(self):
        """Initialize OpenAI LLM"""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set. Please set OPENAI_API_KEY in your .env file.")
        
        if not LANGCHAIN_AVAILABLE or LANGCHAIN_VERSION is None:
            raise ValueError("LangChain is not available or version could not be detected. Please install LangChain: pip install langchain>=0.0.350")
        
        try:
            if LANGCHAIN_VERSION == "new":
                # Newer LangChain (0.1.0+) - uses 'model' parameter
                self.chat_model = ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    openai_api_key=self.openai_api_key
                )
            elif LANGCHAIN_VERSION == "old":
                # Older LangChain (0.0.350) - uses 'model_name' parameter
                self.chat_model = ChatOpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    openai_api_key=self.openai_api_key
                )
            elif LANGCHAIN_VERSION == "legacy":
                # Legacy LangChain - different API
                from langchain.llms import OpenAI
                self.chat_model = OpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    openai_api_key=self.openai_api_key
                )
            else:
                raise ValueError(f"Unsupported LangChain version detected: {LANGCHAIN_VERSION}. Please use LangChain 0.0.350 or newer.")
        except Exception as e:
            raise ValueError(f"Failed to initialize LangChain ChatOpenAI: {e}. Please check your LangChain installation and version.")
    
    async def evaluate_sop_with_llm(
        self,
        sop: Dict,
        findings: Dict,
        context: Dict,
        scenario_code: str,
        rule_based_match: Optional[bool] = None
    ) -> Dict:
        """
        Use LLM to evaluate SOP with enhanced reasoning and confidence scoring
        
        Args:
            sop: SOP rule to evaluate
            findings: Investigation findings
            context: Customer context
            scenario_code: Alert scenario
            rule_based_match: Result from rule-based evaluation (if available)
            
        Returns:
            Evaluation result with LLM reasoning and confidence score
        """
        if not self.enabled or not self.chat_model:
            return {"llm_used": False, "reason": "LLM not enabled"}
        
        try:
            # Build prompt for SOP evaluation with emphasis on confidence scoring
            prompt = self._build_sop_evaluation_prompt(
                sop, findings, context, scenario_code, rule_based_match
            )
            
            # Call LLM
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            
            # LangChain 1.x: use .ainvoke() for async calls
            response = await self.chat_model.ainvoke(messages)
            llm_response = response.content
            
            # Parse LLM response
            evaluation = self._parse_llm_response(llm_response)
            
            logger.info(f"LLM evaluated SOP {sop.get('rule_id')}: matched={evaluation.get('matched')}, confidence={evaluation.get('confidence', 0.5):.2f}")
            
            return {
                "llm_used": True,
                "matched": evaluation.get("matched", False),
                "confidence": evaluation.get("confidence", 0.5),
                "rationale": evaluation.get("rationale", ""),
                "llm_reasoning": evaluation.get("reasoning", ""),
                "raw_response": llm_response
            }
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}", exc_info=True)
            return {
                "llm_used": False,
                "error": str(e),
                "matched": False
            }
    
    async def generate_enhanced_rationale(
        self,
        decision: str,
        findings: Dict,
        context: Dict,
        matched_sop: Optional[Dict] = None
    ) -> str:
        """
        Generate enhanced rationale using LLM
        
        Args:
            decision: Decision made (ESCALATE, RFI, etc.)
            findings: Investigation findings
            context: Customer context
            matched_sop: Matched SOP (if any)
            
        Returns:
            Enhanced rationale text
        """
        if not self.enabled or not self.chat_model:
            return f"Decision: {decision} based on findings and context."
        
        try:
            prompt = f"""
Generate a clear, professional rationale for the following compliance decision.

Decision: {decision}
Scenario: {findings.get('scenario', 'Unknown')}

Findings:
{json.dumps(findings, indent=2)}

Context:
{json.dumps(context, indent=2)}

{"Matched SOP: " + matched_sop.get('rule_name', '') if matched_sop else "No SOP matched"}

Requirements:
- Be concise but comprehensive
- Explain the reasoning clearly
- Use professional compliance language
- Reference specific findings that led to the decision
- Maximum 200 words

Rationale:
            """
            
            messages = [
                SystemMessage(content="You are a compliance analyst explaining regulatory decisions."),
                HumanMessage(content=prompt)
            ]
            
            # LangChain 1.x: use .ainvoke() for async calls
            response = await self.chat_model.ainvoke(messages)
            rationale = response.content.strip()
            
            logger.info(f"Generated enhanced rationale using LLM")
            return rationale
            
        except Exception as e:
            logger.error(f"LLM rationale generation failed: {e}")
            return f"Decision: {decision} based on findings and context."
    
    async def handle_edge_case(
        self,
        scenario_code: str,
        findings: Dict,
        context: Dict,
        available_sops: List[Dict]
    ) -> Optional[Dict]:
        """
        Use LLM to handle edge cases where no SOP matches
        
        Args:
            scenario_code: Alert scenario
            findings: Investigation findings
            context: Customer context
            available_sops: List of available SOPs
            
        Returns:
            Decision recommendation or None
        """
        if not self.enabled or not self.chat_model:
            return None
        
        try:
            prompt = f"""
You are a compliance analyst evaluating a banking alert where no standard SOP matches.

Alert Scenario: {scenario_code}

Findings:
{json.dumps(findings, indent=2)}

Customer Context:
{json.dumps(context, indent=2)}

Available SOPs (none matched):
{json.dumps([s.get('rule_name') for s in available_sops], indent=2)}

Based on the findings and context, recommend the best course of action.

Options:
- ESCALATE: For suspicious activity requiring immediate attention
- RFI: Request for Information from customer
- CLOSE: False positive, no action needed
- BLOCK: Immediate account blocking required

Respond in JSON format:
{{
    "recommendation": "ESCALATE|RFI|CLOSE|BLOCK",
    "confidence": 0.0-1.0,
    "rationale": "Brief explanation",
    "reasoning": "Detailed chain of thought"
}}
            """
            
            messages = [
                SystemMessage(content="You are an expert compliance analyst making regulatory decisions."),
                HumanMessage(content=prompt)
            ]
            
            # LangChain 1.x: use .ainvoke() for async calls
            response = await self.chat_model.ainvoke(messages)
            llm_response = response.content.strip()
            
            # Parse JSON response
            try:
                # Extract JSON from response (might have markdown code blocks)
                if "```json" in llm_response:
                    json_start = llm_response.find("```json") + 7
                    json_end = llm_response.find("```", json_start)
                    llm_response = llm_response[json_start:json_end].strip()
                elif "```" in llm_response:
                    json_start = llm_response.find("```") + 3
                    json_end = llm_response.find("```", json_start)
                    llm_response = llm_response[json_start:json_end].strip()
                
                decision = json.loads(llm_response)
                
                logger.info(f"LLM edge case handling: {decision.get('recommendation')}")
                
                return {
                    "recommendation": decision.get("recommendation", "RFI"),
                    "confidence": float(decision.get("confidence", 0.5)),
                    "rationale": decision.get("rationale", ""),
                    "llm_reasoning": decision.get("reasoning", ""),
                    "llm_used": True
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                return None
                
        except Exception as e:
            logger.error(f"LLM edge case handling failed: {e}")
            return None
    
    def _build_sop_evaluation_prompt(
        self,
        sop: Dict,
        findings: Dict,
        context: Dict,
        scenario_code: str,
        rule_based_match: Optional[bool] = None
    ) -> str:
        """Build prompt for SOP evaluation with emphasis on confidence scoring"""
        rule_based_info = ""
        if rule_based_match is not None:
            rule_based_info = f"\n\nRule-Based Evaluation Result: {'MATCHED' if rule_based_match else 'NOT MATCHED'}\n(Use this as reference, but provide your own independent assessment)"
        
        return f"""
Evaluate whether the following SOP rule applies to this alert and calculate a precise confidence score.

SOP Rule:
- Rule ID: {sop.get('rule_id')}
- Rule Name: {sop.get('rule_name')}
- Condition: {sop.get('condition_description')}
- Action: {sop.get('action')}

Alert Scenario: {scenario_code}

Investigation Findings:
{json.dumps(findings, indent=2)}

Customer Context:
{json.dumps(context, indent=2)}
{rule_based_info}

Task:
1. Analyze if the SOP condition is met based on findings and context
2. Calculate a PRECISE confidence score (0.0 to 1.0) based on:
   - Strength of evidence supporting the match
   - Completeness of available data
   - Clarity of the pattern/indicator
   - Risk level of the scenario
   - Quality and reliability of findings
3. Provide clear reasoning for your confidence score
4. Generate a professional rationale

Confidence Score Guidelines:
- 0.90-1.00: Very strong evidence, clear pattern, high certainty
- 0.75-0.89: Strong evidence, mostly clear pattern, good certainty
- 0.60-0.74: Moderate evidence, some ambiguity, moderate certainty
- 0.40-0.59: Weak evidence, significant ambiguity, low certainty
- 0.00-0.39: Very weak or no evidence, high ambiguity, very low certainty

Respond in JSON format:
{{
    "matched": true/false,
    "confidence": 0.0-1.0,
    "rationale": "Brief professional explanation",
    "reasoning": "Detailed analysis explaining the confidence score calculation"
}}
        """
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        return """You are an expert compliance analyst evaluating banking transaction monitoring alerts.

Your role:
- Evaluate SOP rules against investigation findings
- Calculate precise confidence scores (0.0 to 1.0) based on evidence quality
- Make regulatory compliance decisions
- Provide clear, auditable rationales
- Consider all relevant context and findings

Guidelines:
- Be precise and evidence-based in your confidence scoring
- Confidence scores should reflect the strength and quality of evidence
- Higher confidence (0.8+) for clear patterns with strong evidence
- Lower confidence (0.3-) for ambiguous cases with weak evidence
- Consider regulatory requirements
- Prioritize customer safety and compliance
- Provide clear reasoning for all decisions and confidence scores
- Use professional compliance terminology
- Be conservative with confidence scores when data is incomplete or ambiguous"""
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
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
                "matched": parsed.get("matched", False),
                "confidence": float(parsed.get("confidence", 0.5)),
                "rationale": parsed.get("rationale", ""),
                "reasoning": parsed.get("reasoning", "")
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}. Response: {response[:200]}")
            # Fallback: try to extract key information
            matched = "matched" in response.lower() and "true" in response.lower()
            return {
                "matched": matched,
                "confidence": 0.5,
                "rationale": "LLM evaluation completed",
                "reasoning": response[:500]
            }
    
    def is_enabled(self) -> bool:
        """Check if LLM service is enabled"""
        return self.enabled and self.chat_model is not None


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get singleton LLMService instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

