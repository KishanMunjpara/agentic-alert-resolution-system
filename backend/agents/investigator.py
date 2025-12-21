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
        """Check for velocity spike (layering) with 90-day historical lookback"""
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
        
        # Query: Get transactions in 48-hour window (current spike)
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
        
        # Query: Historical Transaction Lookback (90 days) - DB Tool requirement
        query3 = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({days: 90})
          AND t.transaction_type = 'OUTBOUND'
          AND t.amount > 5000
        RETURN COUNT(t) as historical_count, 
               SUM(t.amount) as historical_total,
               MAX(t.amount) as historical_max_txn,
               COLLECT(DISTINCT date(t.timestamp)) as transaction_dates
        """
        
        historical_results = await self.query_database(query3, {"account_id": account_id})
        
        if historical_results:
            historical_count = historical_results[0].get("historical_count") or 0
            historical_total = historical_results[0].get("historical_total") or 0
            historical_max_txn = historical_results[0].get("historical_max_txn") or 0
            transaction_dates = historical_results[0].get("transaction_dates") or []
        else:
            historical_count = 0
            historical_total = 0
            historical_max_txn = 0
            transaction_dates = []
        
        # Assignment Requirement: DB Query Simulation - Console Output
        # "Executes a simulated db_query_history method, returning a calculated fact (e.g., 'Historical Max Txn: $1,200')"
        print(f"[DB Tool Simulation] db_query_history(account_id='{account_id}', lookback_days=90)")
        print(f"[DB Tool Result] Historical Max Txn: ${historical_max_txn:,.2f}")
        print(f"[DB Tool Result] Historical Transaction Count (90d): {historical_count}")
        print(f"[DB Tool Result] Historical Total Amount (90d): ${historical_total:,.2f}")
        self.logger.info(f"[DB Tool] Historical Max Txn: ${historical_max_txn:,.2f}, Count: {historical_count}, Total: ${historical_total:,.2f}")
        
        # Determine if this is a known business cycle or new pattern
        # If historical data shows similar patterns, it might be a business cycle
        is_business_cycle = False
        if historical_count > 0:
            # Check if there are regular patterns in the 90-day history
            # If velocity spike is isolated (only in last 48h), it's suspicious
            # If similar patterns exist in history, it might be a business cycle
            days_with_transactions = len(set(transaction_dates))
            if days_with_transactions > 10:  # Regular activity over 90 days
                is_business_cycle = True
        
        self.logger.info(f"Velocity query for {account_id}: found {transaction_count} transactions in 48h, "
                        f"{historical_count} in 90 days, total={total_amount}")
        
        self.log_chain_of_thought(
            "Velocity Calculated with 90-day Lookback",
            {
                "transaction_count": transaction_count,
                "total_amount": total_amount,
                "historical_count_90d": historical_count,
                "historical_total_90d": historical_total,
                "is_business_cycle": is_business_cycle,
                "threshold_met": transaction_count >= 5
            }
        )
        
        findings = {
            "alert_id": alert_id,
            "account_id": account_id,
            "transaction_count": transaction_count,
            "total_amount": total_amount,
            "historical_count_90d": historical_count,
            "historical_total_90d": historical_total,
            "is_business_cycle": is_business_cycle,
            "has_prior_high_velocity": historical_count > 0,
            "threshold_exceeded": transaction_count >= 5 and total_amount > 25000,
            "scenario": "VELOCITY_SPIKE"
        }
        
        self.logger.info(f"✓ Velocity check: {transaction_count} txns in 48h, "
                        f"{historical_count} in 90d, ${total_amount} total, "
                        f"business_cycle={is_business_cycle}")
        
        return findings
    
    async def _check_structuring(self, alert_id: str) -> Dict:
        """Check for structuring pattern with geographic/branch proximity analysis"""
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
        
        # Get deposits in 7-day window with geographic data
        query2 = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({days: 7})
          AND t.transaction_type = 'INBOUND'
          AND t.amount > 9000 AND t.amount < 10000
        RETURN COUNT(t) as deposit_count, 
               COLLECT(t.amount) as amounts,
               COLLECT(t.branch_location) as branch_locations,
               COLLECT(t.geographic_location) as geographic_locations,
               COLLECT(t.counterparty) as counterparties
        """
        
        results = await self.query_database(query2, {"account_id": account_id})
        
        if results:
            deposit_count = results[0]["deposit_count"] or 0
            amounts = results[0]["amounts"] or []
            branch_locations = results[0]["branch_locations"] or []
            geographic_locations = results[0]["geographic_locations"] or []
            counterparties = results[0]["counterparties"] or []
        else:
            deposit_count = 0
            amounts = []
            branch_locations = []
            geographic_locations = []
            counterparties = []
        
        # Geographic/Branch Proximity Analysis - Context Tool requirement
        is_geographically_diverse = False
        unique_branches = len(set([loc for loc in branch_locations if loc]))
        unique_geographic = len(set([loc for loc in geographic_locations if loc]))
        
        # If deposits are from multiple branches/geographic locations, it's diverse
        if unique_branches > 1 or unique_geographic > 1:
            is_geographically_diverse = True
        
        # Check linked accounts aggregate - DB Tool requirement
        query3 = """
        MATCH (a:Account {account_id: $account_id})<-[:OWNS]-(c:Customer)
        OPTIONAL MATCH (c)-[:OWNS]->(other:Account)
        WHERE other.account_id <> $account_id
        WITH COLLECT(DISTINCT other.account_id) as linked_account_ids
        UNWIND linked_account_ids as linked_id
        MATCH (linked:Account {account_id: linked_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({days: 7})
          AND t.transaction_type = 'INBOUND'
          AND t.amount > 9000 AND t.amount < 10000
        RETURN SUM(t.amount) as linked_aggregate
        """
        
        linked_results = await self.query_database(query3, {"account_id": account_id})
        linked_accounts_aggregate = linked_results[0].get("linked_aggregate", 0) if linked_results else 0
        
        self.log_chain_of_thought(
            "Structuring Check Complete",
            {
                "deposit_count": deposit_count,
                "amounts": amounts,
                "unique_branches": unique_branches,
                "unique_geographic": unique_geographic,
                "linked_accounts_aggregate": linked_accounts_aggregate
            }
        )
        
        # Determine if it's legitimate business based on geographic diversity
        # If deposits are geographically diverse, it suggests legitimate business receipts
        is_legitimate_business = False
        if deposit_count >= 3:
            # Geographically diverse deposits suggest legitimate business
            if is_geographically_diverse:
                is_legitimate_business = True
            # If all from same location, more suspicious
            else:
                is_legitimate_business = False
        
        return {
            "alert_id": alert_id,
            "account_id": account_id,
            "deposit_count": deposit_count,
            "total_deposits": sum(amounts),
            "linked_accounts_aggregate": linked_accounts_aggregate or 0,
            "unique_branches": unique_branches,
            "unique_geographic_locations": unique_geographic,
            "is_geographically_diverse": is_geographically_diverse,
            "threshold_met": deposit_count >= 3,
            "is_legitimate_business": is_legitimate_business,
            "scenario": "STRUCTURING"
        }
    
    async def _check_kyc_inconsistency(self, alert_id: str) -> Dict:
        """Check for KYC inconsistency with OSINT adverse media search"""
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
        
        # Get customer information for OSINT search
        customer_query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:INVESTIGATES_CUSTOMER]->(c:Customer)
        WITH a, c, COALESCE(c.customer_id, a.customer_id) as customer_id
        WHERE customer_id IS NOT NULL
        MATCH (c2:Customer {customer_id: customer_id})
        RETURN c2.first_name as first_name, c2.last_name as last_name,
               c2.occupation as occupation, c2.employer as employer
        LIMIT 1
        """
        
        customer_results = await self.query_database(customer_query, {"alert_id": alert_id})
        customer_name = ""
        occupation = None
        employer = None
        
        if customer_results:
            first_name = customer_results[0].get("first_name", "")
            last_name = customer_results[0].get("last_name", "")
            customer_name = f"{first_name} {last_name}".strip()
            occupation = customer_results[0].get("occupation")
            employer = customer_results[0].get("employer")
        
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
        
        # OSINT Adverse Media Search - Context Tool requirement
        osint_result = None
        try:
            from services.osint_service import OSINTService
            osint_service = OSINTService()
            if osint_service.is_enabled():
                osint_result = await osint_service.search_adverse_media(
                    customer_name=customer_name,
                    customer_id=account_id,  # Using account_id as identifier
                    occupation=occupation,
                    employer=employer
                )
                self.log_chain_of_thought(
                    "OSINT Search Complete",
                    {
                        "has_adverse_media": osint_result.get("has_adverse_media", False),
                        "risk_level": osint_result.get("risk_level", "LOW")
                    }
                )
        except Exception as e:
            self.logger.warning(f"OSINT search failed: {e}")
        
        return {
            "alert_id": alert_id,
            "transaction_mcc": mcc,
            "transaction_amount": amount,
            "counterparty": counterparty,
            "is_precious_metals": mcc in ["PRECIOUS_METALS", "JEWELRY"],
            "osint_search": osint_result,
            "has_adverse_media": osint_result.get("has_adverse_media", False) if osint_result else False,
            "osint_risk_level": osint_result.get("risk_level", "LOW") if osint_result else "LOW",
            "scenario": "KYC_INCONSISTENCY"
        }
    
    async def _check_sanctions_hit(self, alert_id: str) -> Dict:
        """Check sanctions match details with counterparty historical relationship and banking jurisdiction analysis"""
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
               se.entity_id as entity_id, se.entity_name as entity_name,
               se.jurisdiction as jurisdiction, se.risk_level as risk_level
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
            jurisdiction = results[0].get("jurisdiction")
            risk_level = results[0].get("risk_level")
        else:
            return {"error": "No transaction found"}
        
        # Counterparty's Historical Relationship Analysis - DB Tool requirement
        historical_query = """
        MATCH (acc:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.counterparty = $counterparty
        RETURN COUNT(t) as transaction_count,
               SUM(t.amount) as total_amount,
               MIN(t.timestamp) as first_transaction_date,
               MAX(t.timestamp) as last_transaction_date,
               COLLECT(DISTINCT t.transaction_type) as transaction_types
        """
        
        historical_results = await self.query_database(historical_query, {
            "account_id": account_id,
            "counterparty": counterparty
        })
        
        if historical_results:
            historical_count = historical_results[0].get("transaction_count") or 0
            historical_total = historical_results[0].get("total_amount") or 0
            first_transaction = historical_results[0].get("first_transaction_date")
            last_transaction = historical_results[0].get("last_transaction_date")
            transaction_types = historical_results[0].get("transaction_types") or []
        else:
            historical_count = 0
            historical_total = 0
            first_transaction = None
            last_transaction = None
            transaction_types = []
        
        # Determine if this is a new relationship or established
        is_established_relationship = historical_count > 1
        relationship_duration_days = None
        if first_transaction and last_transaction:
            # Calculate relationship duration (simplified)
            try:
                from datetime import datetime
                if isinstance(first_transaction, str):
                    first_dt = datetime.fromisoformat(first_transaction.replace('Z', '+00:00'))
                else:
                    first_dt = first_transaction
                if isinstance(last_transaction, str):
                    last_dt = datetime.fromisoformat(last_transaction.replace('Z', '+00:00'))
                else:
                    last_dt = last_transaction
                relationship_duration_days = (last_dt - first_dt).days
            except:
                relationship_duration_days = None
        
        # Banking Jurisdiction Analysis - DB Tool requirement
        is_high_risk_jurisdiction = False
        if jurisdiction:
            high_risk_jurisdictions = ["HIGH_RISK_COUNTRY", "RESTRICTED_REGION", "SANCTIONS_LIST_COUNTRY"]
            is_high_risk_jurisdiction = jurisdiction in high_risk_jurisdictions
        
        # Determine if this is a false positive (common name scenario)
        is_false_positive = False
        if match_score < 0.90:  # Fuzzy match (80% similarity as per requirement)
            # If it's a common name and no high-risk indicators, likely false positive
            common_names = ["ABC", "XYZ", "Corp", "Inc", "LLC"]
            if any(name.lower() in counterparty.lower() for name in common_names):
                if not is_high_risk_jurisdiction and historical_count == 0:
                    is_false_positive = True
        
        self.log_chain_of_thought(
            "Sanctions Check Complete with Historical Analysis",
            {
                "match_score": match_score,
                "entity_id": entity_id,
                "jurisdiction": jurisdiction,
                "historical_count": historical_count,
                "is_high_risk_jurisdiction": is_high_risk_jurisdiction,
                "is_false_positive": is_false_positive
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
            "jurisdiction": jurisdiction,
            "risk_level": risk_level,
            "is_high_risk_jurisdiction": is_high_risk_jurisdiction,
            "historical_transaction_count": historical_count,
            "historical_total_amount": historical_total,
            "is_established_relationship": is_established_relationship,
            "relationship_duration_days": relationship_duration_days,
            "is_false_positive": is_false_positive,
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

