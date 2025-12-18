"""
Investigator Agent - Spoke
Queries transaction history and calculates risk metrics
"""

import logging
from typing import Dict, Optional, Callable
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class InvestigatorAgent(BaseAgent):
    """
    Investigator Agent (Spoke)
    
    Responsibilities:
    - Query transaction history (90 days)
    - Calculate velocity metrics
    - Check linked accounts
    - Identify transaction patterns
    - Emit findings to WebSocket
    """
    
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """Initialize Investigator Agent"""
        super().__init__("Investigator", broadcast_fn)
    
    async def execute(self, alert_id: str, scenario_code: str) -> Dict:
        """
        Execute investigation based on scenario
        
        Args:
            alert_id: Alert to investigate
            scenario_code: Alert scenario type
            
        Returns:
            Investigation findings
        """
        self.reset_chain_of_thought()
        
        self.logger.info(f"🔍 Investigator analyzing {scenario_code}")
        
        findings = {
            "alert_id": alert_id,
            "scenario": scenario_code,
            "timestamp": None
        }
        
        try:
            if scenario_code == "VELOCITY_SPIKE":
                findings = await self._check_velocity_spike(alert_id)
            elif scenario_code == "STRUCTURING":
                findings = await self._check_structuring(alert_id)
            elif scenario_code == "KYC_INCONSISTENCY":
                findings = await self._check_kyc_inconsistency(alert_id)
            elif scenario_code == "SANCTIONS_HIT":
                findings = await self._check_sanctions_hit(alert_id)
            elif scenario_code == "DORMANT_ACTIVATION":
                findings = await self._check_dormant_activation(alert_id)
            else:
                self.logger.warning(f"Unknown scenario: {scenario_code}")
            
            # Emit findings event
            await self.emit_event("investigator_finding", {
                "alert_id": alert_id,
                "findings": findings
            })
            
            return findings
            
        except Exception as e:
            error_details = self.handle_error(e, "Investigation")
            return {"error": str(e), **error_details}
    
    async def _check_velocity_spike(self, alert_id: str) -> Dict:
        """Check for velocity spike (layering)"""
        self.log_chain_of_thought(
            "Checking Velocity Spike",
            {"alert_id": alert_id}
        )
        
        # Query: Get account linked to alert (try relationship first, then property)
        query1 = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_ACCOUNT]->(acc:Account)
        WITH a, acc, COALESCE(acc.account_id, a.account_id) as account_id
        WHERE account_id IS NOT NULL
        RETURN account_id
        LIMIT 1
        """
        
        accounts = await self.query_database(query1, {"alert_id": alert_id})
        if not accounts or not accounts[0].get("account_id"):
            self.logger.warning(f"No account found for alert {alert_id}")
            return {"error": "No account linked"}
        
        account_id = accounts[0]["account_id"]
        self.log_chain_of_thought(
            "Account Identified",
            {"account_id": account_id}
        )
        
        # Query: Get transactions in 48-hour window
        query2 = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({hours: 48})
          AND t.transaction_type = 'OUTBOUND'
          AND t.amount > 5000
        RETURN COUNT(t) as transaction_count, SUM(t.amount) as total_amount
        """
        
        results = await self.query_database(query2, {"account_id": account_id})
        
        if results:
            transaction_count = results[0].get("transaction_count") or 0
            total_amount = results[0].get("total_amount") or 0
        else:
            transaction_count = 0
            total_amount = 0
        
        self.logger.info(f"Velocity query for {account_id}: found {transaction_count} transactions, total={total_amount}")
        
        self.log_chain_of_thought(
            "Velocity Calculated",
            {
                "transaction_count": transaction_count,
                "total_amount": total_amount,
                "threshold_met": transaction_count >= 5
            }
        )
        
        findings = {
            "alert_id": alert_id,
            "account_id": account_id,
            "transaction_count": transaction_count,
            "total_amount": total_amount,
            "threshold_exceeded": transaction_count >= 5 and total_amount > 25000,
            "scenario": "VELOCITY_SPIKE"
        }
        
        self.logger.info(f"✓ Velocity check: {transaction_count} txns, "
                        f"${total_amount} total")
        
        return findings
    
    async def _check_structuring(self, alert_id: str) -> Dict:
        """Check for structuring pattern"""
        self.log_chain_of_thought(
            "Checking Structuring",
            {"alert_id": alert_id}
        )
        
        # Get account (try relationship first, then property)
        query1 = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_ACCOUNT]->(acc:Account)
        WITH a, acc, COALESCE(acc.account_id, a.account_id) as account_id
        WHERE account_id IS NOT NULL
        RETURN account_id
        LIMIT 1
        """
        
        accounts = await self.query_database(query1, {"alert_id": alert_id})
        account_id = accounts[0].get("account_id") if accounts else None
        
        if not account_id:
            self.logger.warning(f"No account found for alert {alert_id}")
            return {"error": "No account linked"}
        
        # Get deposits in 7-day window
        query2 = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({days: 7})
          AND t.transaction_type = 'INBOUND'
          AND t.amount > 9000 AND t.amount < 10000
        RETURN COUNT(t) as deposit_count, COLLECT(t.amount) as amounts
        """
        
        results = await self.query_database(query2, {"account_id": account_id})
        
        if results:
            deposit_count = results[0]["deposit_count"] or 0
            amounts = results[0]["amounts"] or []
        else:
            deposit_count = 0
            amounts = []
        
        self.log_chain_of_thought(
            "Structuring Check Complete",
            {
                "deposit_count": deposit_count,
                "amounts": amounts
            }
        )
        
        # For structuring, check if it's a legitimate business pattern
        # If 3+ deposits just under 10k from single account, treat as potential legitimate business
        is_legitimate_business = False
        if deposit_count >= 3:
            # Check if deposits are from diverse sources (would indicate legitimate business)
            # For now, if we have 3+ deposits, assume it could be legitimate business
            # This can be enhanced with actual counterparty analysis
            is_legitimate_business = True
        
        return {
            "alert_id": alert_id,
            "account_id": account_id,
            "deposit_count": deposit_count,
            "total_deposits": sum(amounts),
            "linked_accounts_aggregate": 0,  # Single account, no linked accounts
            "threshold_met": deposit_count >= 3,
            "is_legitimate_business": is_legitimate_business,
            "scenario": "STRUCTURING"
        }
    
    async def _check_kyc_inconsistency(self, alert_id: str) -> Dict:
        """Check for KYC inconsistency"""
        self.log_chain_of_thought(
            "Checking KYC Inconsistency",
            {"alert_id": alert_id}
        )
        
        # Get account first (try relationship, then property)
        account_query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_ACCOUNT]->(acc:Account)
        WITH a, acc, COALESCE(acc.account_id, a.account_id) as account_id
        WHERE account_id IS NOT NULL
        RETURN account_id
        LIMIT 1
        """
        
        account_results = await self.query_database(account_query, {"alert_id": alert_id})
        account_id = account_results[0].get("account_id") if account_results else None
        
        if not account_id:
            return {"error": "No account linked"}
        
        # Get transaction details
        query = """
        MATCH (acc:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        RETURN t.counterparty_mcc as mcc, t.amount as amount, 
               t.counterparty as counterparty
        ORDER BY t.timestamp DESC
        LIMIT 1
        """
        
        results = await self.query_database(query, {"account_id": account_id})
        
        if results:
            mcc = results[0].get("mcc")
            amount = results[0].get("amount")
            counterparty = results[0].get("counterparty")
        else:
            return {"error": "No transaction found"}
        
        self.log_chain_of_thought(
            "Transaction Details Retrieved",
            {"mcc": mcc, "amount": amount}
        )
        
        return {
            "alert_id": alert_id,
            "transaction_mcc": mcc,
            "transaction_amount": amount,
            "counterparty": counterparty,
            "is_precious_metals": mcc in ["PRECIOUS_METALS", "JEWELRY"],
            "scenario": "KYC_INCONSISTENCY"
        }
    
    async def _check_sanctions_hit(self, alert_id: str) -> Dict:
        """Check sanctions match details"""
        self.log_chain_of_thought(
            "Checking Sanctions Match",
            {"alert_id": alert_id}
        )
        
        # Get account first (try relationship, then property)
        account_query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_ACCOUNT]->(acc:Account)
        WITH a, acc, COALESCE(acc.account_id, a.account_id) as account_id
        WHERE account_id IS NOT NULL
        RETURN account_id
        LIMIT 1
        """
        
        account_results = await self.query_database(account_query, {"alert_id": alert_id})
        account_id = account_results[0].get("account_id") if account_results else None
        
        if not account_id:
            return {"error": "No account linked"}
        
        # Get transaction with sanctions entity
        query = """
        MATCH (acc:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        OPTIONAL MATCH (t)-[rel:TO_SANCTIONED_ENTITY]->(se:SanctionsEntity)
        RETURN t.counterparty as counterparty, t.amount as amount,
               COALESCE(rel.match_score, 0) as match_score,
               se.entity_id as entity_id, se.entity_name as entity_name
        ORDER BY t.timestamp DESC
        LIMIT 1
        """
        
        results = await self.query_database(query, {"account_id": account_id})
        
        if results:
            counterparty = results[0].get("counterparty")
            amount = results[0].get("amount")
            match_score = results[0].get("match_score") or 0
            entity_id = results[0].get("entity_id")
            entity_name = results[0].get("entity_name")
        else:
            return {"error": "No transaction found"}
        
        self.log_chain_of_thought(
            "Sanctions Check Complete",
            {
                "match_score": match_score,
                "entity_id": entity_id
            }
        )
        
        return {
            "alert_id": alert_id,
            "counterparty": counterparty,
            "amount": amount,
            "match_score": match_score,
            "is_match": match_score >= 0.80,
            "matched_entity_id": entity_id,
            "matched_entity_name": entity_name,
            "scenario": "SANCTIONS_HIT"
        }
    
    async def _check_dormant_activation(self, alert_id: str) -> Dict:
        """Check dormant account activation"""
        self.log_chain_of_thought(
            "Checking Dormant Activation",
            {"alert_id": alert_id}
        )
        
        # Get account dormant status (try relationship, then property)
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_ACCOUNT]->(acc:Account)
        WITH a, acc, COALESCE(acc.account_id, a.account_id) as account_id
        WHERE account_id IS NOT NULL
        MATCH (acc2:Account {account_id: account_id})
        RETURN acc2.account_id as account_id, COALESCE(acc2.dormant_days, 0) as dormant_days
        LIMIT 1
        """
        
        results = await self.query_database(query, {"alert_id": alert_id})
        
        if results:
            account_id = results[0].get("account_id")
            dormant_days = results[0].get("dormant_days") or 0
            if account_id is None:
                return {"error": "No account found"}
        else:
            return {"error": "No account found"}
        
        # Get recent transactions
        query2 = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({days: 1})
        RETURN COUNT(t) as recent_txn_count, COLLECT(t.amount) as amounts
        """
        
        txn_results = await self.query_database(query2, {"account_id": account_id})
        
        if txn_results:
            recent_txns = txn_results[0]["recent_txn_count"] or 0
            amounts = txn_results[0]["amounts"] or []
        else:
            recent_txns = 0
            amounts = []
        
        self.log_chain_of_thought(
            "Dormant Activation Check Complete",
            {
                "dormant_days": dormant_days,
                "recent_transactions": recent_txns
            }
        )
        
        return {
            "alert_id": alert_id,
            "account_id": account_id,
            "dormant_days": dormant_days or 0,
            "is_long_dormant": (dormant_days or 0) >= 365,
            "recent_transaction_count": recent_txns,
            "total_amount": sum(amounts) if amounts else 0,
            "scenario": "DORMANT_ACTIVATION"
        }

