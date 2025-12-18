"""
Context Gatherer Agent - Spoke
Gathers KYC profile data, risk ratings, and customer context
"""

import logging
from typing import Dict, Optional, Callable
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContextGathererAgent(BaseAgent):
    """
    Context Gatherer Agent (Spoke)
    
    Responsibilities:
    - Retrieve KYC profile
    - Get risk rating
    - Check validation flags
    - Gather customer context
    - Emit context to WebSocket
    """
    
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """Initialize Context Gatherer Agent"""
        super().__init__("ContextGatherer", broadcast_fn)
    
    async def execute(self, alert_id: str) -> Dict:
        """
        Gather context for an alert
        
        Args:
            alert_id: Alert to gather context for
            
        Returns:
            Context data
        """
        self.reset_chain_of_thought()
        
        self.logger.info("📋 Context Gatherer gathering customer data...")
        
        try:
            # Get customer linked to alert
            customer = await self._get_customer(alert_id)
            if not customer:
                self.logger.warning(f"No customer found for alert {alert_id}")
                return {"error": "No customer linked"}
            
            self.log_chain_of_thought(
                "Customer Retrieved",
                {"customer_id": customer.get("customer_id")}
            )
            
            # Get KYC profile
            kyc_profile = await self._get_kyc_profile(customer["customer_id"])
            
            self.log_chain_of_thought(
                "KYC Profile Retrieved",
                {
                    "kyc_risk": kyc_profile.get("kyc_risk"),
                    "occupation": kyc_profile.get("occupation")
                }
            )
            
            # Get linked accounts
            linked_accounts = await self._get_linked_accounts(customer["customer_id"])
            
            self.log_chain_of_thought(
                "Linked Accounts Retrieved",
                {"linked_account_count": len(linked_accounts)}
            )
            
            # Compile context
            context = {
                "alert_id": alert_id,
                "customer_id": customer["customer_id"],
                "customer_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}",
                "kyc_risk": kyc_profile.get("kyc_risk"),
                "occupation": kyc_profile.get("occupation"),
                "employer": kyc_profile.get("employer"),
                "declared_income": kyc_profile.get("declared_income"),
                "profile_age_days": kyc_profile.get("profile_age_days"),
                "linked_accounts": linked_accounts,
                "linked_account_count": len(linked_accounts)
            }
            
            # Emit context event
            await self.emit_event("context_found", {
                "alert_id": alert_id,
                "context": context
            })
            
            self.logger.info(f"✓ Context gathered: Risk={context['kyc_risk']}, "
                           f"Occupation={context['occupation']}")
            
            return context
            
        except Exception as e:
            error_details = self.handle_error(e, "Context gathering")
            return {"error": str(e), **error_details}
    
    async def _get_customer(self, alert_id: str) -> Optional[Dict]:
        """Get customer linked to alert (try relationship first, then property)"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_CUSTOMER]->(c:Customer)
        WITH a, c, COALESCE(c.customer_id, a.customer_id) as customer_id
        WHERE customer_id IS NOT NULL
        MATCH (c2:Customer {customer_id: customer_id})
        RETURN c2 as c
        LIMIT 1
        """
        
        try:
            results = await self.query_database(query, {"alert_id": alert_id})
            if results and results[0].get("c"):
                return dict(results[0]["c"])
            return None
        except Exception as e:
            self.logger.error(f"Failed to get customer: {e}")
            return None
    
    async def _get_kyc_profile(self, customer_id: str) -> Dict:
        """Get KYC profile for customer"""
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        RETURN {
            kyc_risk: c.kyc_risk,
            occupation: c.occupation,
            employer: c.employer,
            declared_income: c.declared_income,
            profile_age_days: c.profile_age_days
        } as profile
        """
        
        try:
            results = await self.query_database(query, {"customer_id": customer_id})
            if results and results[0].get("profile"):
                profile = results[0]["profile"]
                self.logger.info(f"KYC profile for {customer_id}: {profile}")
                return profile
            self.logger.warning(f"No KYC profile found for customer {customer_id}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get KYC profile: {e}")
            return {}
    
    async def _get_linked_accounts(self, customer_id: str) -> list:
        """Get accounts linked to customer"""
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        OPTIONAL MATCH (c)-[:LINKED_TO]->(c2:Customer)-[:OWNS]->(a:Account)
        RETURN COLLECT(DISTINCT a.account_id) as linked_accounts
        """
        
        try:
            results = await self.query_database(query, {"customer_id": customer_id})
            if results and results[0]["linked_accounts"]:
                return results[0]["linked_accounts"]
            return []
        except Exception as e:
            self.logger.error(f"Failed to get linked accounts: {e}")
            return []
    
    async def validate_occupation(self, occupation: str, 
                                 transaction_mcc: str) -> Dict:
        """
        Validate if occupation matches transaction MCC
        
        Args:
            occupation: Customer occupation
            transaction_mcc: Transaction merchant category code
            
        Returns:
            Validation result
        """
        # Define occupation-to-MCC mappings
        occupation_mcc_map = {
            "Jeweler": ["PRECIOUS_METALS", "JEWELRY", "GEMS"],
            "Jeweler/Goldsmith": ["PRECIOUS_METALS", "JEWELRY"],
            "Precious Metals Trader": ["PRECIOUS_METALS"],
            "Teacher": ["EDUCATION", "BOOKS"],
            "Engineer": ["ENGINEERING", "CONSTRUCTION", "MANUFACTURING"],
            "Consultant": ["CONSULTING", "PROFESSIONAL_SERVICES"],
            "Retired": ["HEALTHCARE", "UTILITIES", "INSURANCE"]
        }
        
        # Check if occupation matches MCC
        valid_mccs = occupation_mcc_map.get(occupation, [])
        is_match = transaction_mcc in valid_mccs
        
        return {
            "occupation": occupation,
            "transaction_mcc": transaction_mcc,
            "is_match": is_match,
            "confidence": 0.95 if is_match else 0.1
        }

