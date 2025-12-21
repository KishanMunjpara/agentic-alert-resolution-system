"""
Create seed data in Neo4j using MERGE (idempotent)
This ensures data exists even if run multiple times
"""

import logging
from datetime import datetime, timedelta
from database.neo4j_connector import Neo4jConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_seed_data():
    """Create all seed data using MERGE for idempotency"""
    db = Neo4jConnector()
    
    if not db.test_connection():
        logger.error("Failed to connect to Neo4j. Check your .env configuration.")
        return False
    
    logger.info("✓ Connected to Neo4j")
    logger.info("Creating seed data (idempotent - safe to run multiple times)...")
    
    try:
        # ========================================================================
        # STEP 0: UPDATE CUSTOMER EMAILS FOR TESTING (if needed)
        # ========================================================================
        test_email = "kishanmunjpara2710@gmail.com"
        logger.info("\n[0/6] Updating customer emails for testing...")
        
        try:
            # Drop unique constraint on email (for testing - allows same email for all customers)
            drop_constraint_query = "DROP CONSTRAINT customer_email IF EXISTS"
            db.execute_write(drop_constraint_query, {})
            logger.info("  ✓ Unique email constraint dropped (for testing)")
        except Exception as e:
            logger.debug(f"  Constraint drop (may not exist): {e}")
        
        # Update all existing customers to test email
        update_email_query = """
        MATCH (c:Customer)
        SET c.email = $email
        RETURN count(c) as updated_count
        """
        try:
            result = db.execute_query(update_email_query, {"email": test_email})
            if result:
                count = result[0].get("updated_count", 0)
                if count > 0:
                    logger.info(f"  ✓ Updated {count} existing customer(s) to test email: {test_email}")
        except Exception as e:
            logger.debug(f"  Email update (may be no existing customers): {e}")
        
        logger.info("  ✓ Email configuration ready for testing")
        # ========================================================================
        # STEP 1: CREATE CUSTOMERS
        # ========================================================================
        logger.info("\n[1/6] Creating customers...")
        
        customers = [
            {
                'customer_id': 'CUST-101',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'kishanmunjpara2710@gmail.com',
                'phone': '+1-555-0101',
                'kyc_risk': 'HIGH',
                'occupation': 'Teacher',
                'employer': 'Lincoln High School',
                'declared_income': 50000.0,
                'profile_age_days': 365
            },
            {
                'customer_id': 'CUST-102',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'kishanmunjpara2710@gmail.com',
                'phone': '+1-555-0102',
                'kyc_risk': 'MEDIUM',
                'occupation': 'Engineer',
                'employer': 'Tech Corp',
                'declared_income': 100000.0,
                'profile_age_days': 730
            },
            {
                'customer_id': 'CUST-103',
                'first_name': 'Michael',
                'last_name': 'Johnson',
                'email': 'kishanmunjpara2710@gmail.com',
                'phone': '+1-555-0103',
                'kyc_risk': 'LOW',
                'occupation': 'Jeweler',
                'employer': 'Johnson Jewelry Store',
                'declared_income': 75000.0,
                'profile_age_days': 500
            },
            {
                'customer_id': 'CUST-104',
                'first_name': 'Sarah',
                'last_name': 'Williams',
                'email': 'kishanmunjpara2710@gmail.com',
                'phone': '+1-555-0104',
                'kyc_risk': 'HIGH',
                'occupation': 'Consultant',
                'employer': 'Global Consulting LLC',
                'declared_income': 120000.0,
                'profile_age_days': 1000
            },
            {
                'customer_id': 'CUST-105',
                'first_name': 'Robert',
                'last_name': 'Brown',
                'email': 'kishanmunjpara2710@gmail.com',
                'phone': '+1-555-0105',
                'kyc_risk': 'LOW',
                'occupation': 'Retired',
                'employer': 'Self',
                'declared_income': 30000.0,
                'profile_age_days': 1825
            }
        ]
        
        for cust in customers:
            query = """
            MERGE (c:Customer {customer_id: $customer_id})
            SET c.first_name = $first_name,
                c.last_name = $last_name,
                c.email = $email,
                c.phone = $phone,
                c.kyc_risk = $kyc_risk,
                c.occupation = $occupation,
                c.employer = $employer,
                c.declared_income = $declared_income,
                c.profile_age_days = $profile_age_days,
                c.created_at = COALESCE(c.created_at, datetime()),
                c.updated_at = datetime()
            """
            db.execute_write(query, cust)
        logger.info(f"  ✓ Created/updated {len(customers)} customers")
        
        # ========================================================================
        # STEP 2: CREATE ACCOUNTS
        # ========================================================================
        logger.info("\n[2/6] Creating accounts...")
        
        accounts = [
            {
                'customer_id': 'CUST-101',
                'account_id': 'ACC-001',
                'account_type': 'CHECKING',
                'status': 'ACTIVE',
                'currency': 'USD',
                'balance': 50000.0,
                'dormant_days': 0
            },
            {
                'customer_id': 'CUST-102',
                'account_id': 'ACC-002',
                'account_type': 'CHECKING',
                'status': 'ACTIVE',
                'currency': 'USD',
                'balance': 100000.0,
                'dormant_days': 0
            },
            {
                'customer_id': 'CUST-103',
                'account_id': 'ACC-003',
                'account_type': 'BUSINESS',
                'status': 'ACTIVE',
                'currency': 'USD',
                'balance': 75000.0,
                'dormant_days': 0
            },
            {
                'customer_id': 'CUST-104',
                'account_id': 'ACC-004',
                'account_type': 'CHECKING',
                'status': 'ACTIVE',
                'currency': 'USD',
                'balance': 120000.0,
                'dormant_days': 0
            },
            {
                'customer_id': 'CUST-105',
                'account_id': 'ACC-005',
                'account_type': 'SAVINGS',
                'status': 'DORMANT',
                'currency': 'USD',
                'balance': 50000.0,
                'dormant_days': 365
            }
        ]
        
        for acc in accounts:
            query = """
            MATCH (c:Customer {customer_id: $customer_id})
            MERGE (a:Account {account_id: $account_id})
            SET a.account_type = $account_type,
                a.status = $status,
                a.currency = $currency,
                a.balance = $balance,
                a.dormant_days = $dormant_days,
                a.created_date = COALESCE(a.created_date, datetime() - duration({days: 365})),
                a.last_activity_date = datetime(),
                a.created_at = COALESCE(a.created_at, datetime())
            MERGE (c)-[:OWNS]->(a)
            """
            db.execute_write(query, acc)
        logger.info(f"  ✓ Created/updated {len(accounts)} accounts")
        
        # ========================================================================
        # STEP 3: CREATE TRANSACTIONS FOR A-001 (Velocity Spike)
        # ========================================================================
        logger.info("\n[3/6] Creating transactions...")
        
        # Transactions for ACC-001 (6 transactions, total 33,400)
        transactions_a001 = [
            {'txn_id': 'TXN-001', 'amount': 6000.0, 'hours_ago': 40},
            {'txn_id': 'TXN-002', 'amount': 5500.0, 'hours_ago': 35},
            {'txn_id': 'TXN-003', 'amount': 5200.0, 'hours_ago': 30},
            {'txn_id': 'TXN-004', 'amount': 6000.0, 'hours_ago': 25},
            {'txn_id': 'TXN-005', 'amount': 5500.0, 'hours_ago': 20},
            {'txn_id': 'TXN-006', 'amount': 5200.0, 'hours_ago': 15},
        ]
        
        for txn in transactions_a001:
            query = """
            MATCH (a:Account {account_id: 'ACC-001'})
            MERGE (t:Transaction {txn_id: $txn_id})
            SET t.amount = $amount,
                t.currency = 'USD',
                t.transaction_type = 'OUTBOUND',
                t.timestamp = datetime() - duration({hours: $hours_ago}),
                t.description = 'Transfer',
                t.counterparty = 'Unknown Entity',
                t.counterparty_mcc = 'GENERAL',
                t.reference = $txn_id,
                t.created_at = datetime()
            MERGE (a)-[:HAS_TRANSACTION]->(t)
            """
            db.execute_write(query, txn)
        
        # Transactions for ACC-002 (Structuring - 3 deposits just under 10k)
        transactions_a002 = [
            {'txn_id': 'TXN-101', 'amount': 9500.0, 'hours_ago': 48},
            {'txn_id': 'TXN-102', 'amount': 9800.0, 'hours_ago': 36},
            {'txn_id': 'TXN-103', 'amount': 9700.0, 'hours_ago': 24},
        ]
        
        # Add geographic locations for structuring scenario (geographically diverse)
        geographic_locations = ['New York, NY', 'Los Angeles, CA', 'Chicago, IL']
        branch_locations = ['Branch-A', 'Branch-B', 'Branch-C']
        
        for i, txn in enumerate(transactions_a002):
            query = """
            MATCH (a:Account {account_id: 'ACC-002'})
            MERGE (t:Transaction {txn_id: $txn_id})
            SET t.amount = $amount,
                t.currency = 'USD',
                t.transaction_type = 'INBOUND',
                t.timestamp = datetime() - duration({hours: $hours_ago}),
                t.description = 'Deposit',
                t.counterparty = 'Unknown',
                t.counterparty_mcc = 'GENERAL',
                t.branch_location = $branch_location,
                t.geographic_location = $geographic_location,
                t.reference = $txn_id,
                t.created_at = datetime()
            MERGE (a)-[:HAS_TRANSACTION]->(t)
            """
            txn['branch_location'] = branch_locations[i % len(branch_locations)]
            txn['geographic_location'] = geographic_locations[i % len(geographic_locations)]
            db.execute_write(query, txn)
        
        # Transaction for ACC-003 (KYC Inconsistency - Precious Metals)
        query = """
        MATCH (a:Account {account_id: 'ACC-003'})
        MERGE (t:Transaction {txn_id: 'TXN-201'})
        SET t.amount = 15000.0,
            t.currency = 'USD',
            t.transaction_type = 'OUTBOUND',
            t.timestamp = datetime() - duration({hours: 12}),
            t.description = 'Precious Metals Purchase',
            t.counterparty = 'Gold & Silver Exchange',
            t.counterparty_mcc = 'PRECIOUS_METALS',
            t.reference = 'TXN-201',
            t.created_at = datetime()
        MERGE (a)-[:HAS_TRANSACTION]->(t)
        """
        db.execute_write(query, {})
        
        # Transaction for ACC-004 (Sanctions Hit)
        query = """
        MATCH (a:Account {account_id: 'ACC-004'})
        MERGE (t:Transaction {txn_id: 'TXN-301'})
        SET t.amount = 50000.0,
            t.currency = 'USD',
            t.transaction_type = 'OUTBOUND',
            t.timestamp = datetime() - duration({hours: 5}),
            t.description = 'Wire Transfer',
            t.counterparty = 'Entity ABC',
            t.counterparty_mcc = 'WIRE_TRANSFER',
            t.reference = 'TXN-301',
            t.created_at = datetime()
        MERGE (a)-[:HAS_TRANSACTION]->(t)
        """
        db.execute_write(query, {})
        
        # Transactions for ACC-005 (Dormant Activation)
        transactions_a005 = [
            {'txn_id': 'TXN-401', 'amount': 15000.0, 'hours_ago': 1, 'type': 'INBOUND'},
            {'txn_id': 'TXN-402', 'amount': 14500.0, 'hours_ago': 0, 'type': 'OUTBOUND'},
        ]
        
        for txn in transactions_a005:
            query = """
            MATCH (a:Account {account_id: 'ACC-005'})
            MERGE (t:Transaction {txn_id: $txn_id})
            SET t.amount = $amount,
                t.currency = 'USD',
                t.transaction_type = $type,
                t.timestamp = datetime() - duration({hours: $hours_ago}),
                t.description = 'Wire Transfer',
                t.counterparty = 'External Source',
                t.counterparty_mcc = 'WIRE_TRANSFER',
                t.reference = $txn_id,
                t.created_at = datetime()
            MERGE (a)-[:HAS_TRANSACTION]->(t)
            """
            db.execute_write(query, txn)
        
        logger.info("  ✓ Created/updated transactions")
        
        # ========================================================================
        # STEP 4: CREATE SANCTIONS ENTITIES
        # ========================================================================
        logger.info("\n[4/6] Creating sanctions entities...")
        
        query = """
        MERGE (se:SanctionsEntity {entity_id: 'SANC-001'})
        SET se.entity_name = 'Entity ABC',
            se.entity_type = 'ORGANIZATION',
            se.country = 'HIGH_RISK',
            se.created_at = datetime()
        WITH se
        MATCH (t:Transaction {txn_id: 'TXN-301'})
        MERGE (t)-[r:TO_SANCTIONED_ENTITY]->(se)
        SET r.match_score = 92
        """
        db.execute_write(query, {})
        
        logger.info("  ✓ Created/updated sanctions entities")
        
        # ========================================================================
        # STEP 5: CREATE SOPs
        # ========================================================================
        logger.info("\n[5/6] Creating SOPs...")
        
        sops = [
            {
                'rule_id': 'SOP-A001-01',
                'scenario_code': 'VELOCITY_SPIKE',
                'rule_name': 'High Velocity High Risk Escalation',
                'condition_description': 'Transaction count >= 5 AND total amount > 25000 AND kyc_risk = HIGH',
                'condition_logic': 'findings.get("transaction_count", 0) >= 5 and findings.get("total_amount", 0) > 25000 and context.get("kyc_risk") == "HIGH"',
                'action': 'ESCALATE',
                'priority': 1
            },
            {
                'rule_id': 'SOP-A001-02',
                'scenario_code': 'VELOCITY_SPIKE',
                'rule_name': 'Known Business Cycle Close',
                'condition_description': 'Velocity spike explained by known business cycle',
                'condition_logic': 'findings.get("is_business_cycle") == true',
                'action': 'CLOSE',
                'priority': 2
            },
            {
                'rule_id': 'SOP-A002-01',
                'scenario_code': 'STRUCTURING',
                'rule_name': 'Linked Accounts Aggregate Escalation',
                'condition_description': 'Linked accounts aggregate > 28000',
                'condition_logic': 'findings.get("linked_accounts_aggregate", 0) > 28000',
                'action': 'ESCALATE',
                'priority': 1
            },
            {
                'rule_id': 'SOP-A002-02',
                'scenario_code': 'STRUCTURING',
                'rule_name': 'Legitimate Business RFI',
                'condition_description': 'Geographically diverse and legitimate business receipts',
                'condition_logic': 'findings.get("is_legitimate_business") == true',
                'action': 'RFI',
                'priority': 2
            },
            {
                'rule_id': 'SOP-A003-01',
                'scenario_code': 'KYC_INCONSISTENCY',
                'rule_name': 'Matching Occupation Close',
                'condition_description': 'Occupation confirmed as Jeweler or Trader',
                'condition_logic': 'context.get("occupation") in ["Jeweler", "Precious Metals Trader", "Jeweler/Goldsmith"]',
                'action': 'CLOSE',
                'priority': 1
            },
            {
                'rule_id': 'SOP-A003-02',
                'scenario_code': 'KYC_INCONSISTENCY',
                'rule_name': 'Mismatched Profile Escalation',
                'condition_description': 'Profile is Teacher/Student sending to Precious Metals',
                'condition_logic': 'context.get("occupation") in ["Teacher", "Student", "Government Employee"]',
                'action': 'ESCALATE',
                'priority': 2
            },
            {
                'rule_id': 'SOP-A004-01',
                'scenario_code': 'SANCTIONS_HIT',
                'rule_name': 'High Risk Jurisdiction Escalation',
                'condition_description': 'True match or high-risk jurisdiction',
                'condition_logic': 'findings.get("match_score", 0) >= 0.90 or context.get("jurisdiction") == "HIGH_RISK"',
                'action': 'ESCALATE',
                'priority': 1
            },
            {
                'rule_id': 'SOP-A004-02',
                'scenario_code': 'SANCTIONS_HIT',
                'rule_name': 'False Positive Close',
                'condition_description': 'Proven false positive (common name)',
                'condition_logic': 'findings.get("is_false_positive") == true',
                'action': 'CLOSE',
                'priority': 2
            },
            {
                'rule_id': 'SOP-A005-01',
                'scenario_code': 'DORMANT_ACTIVATION',
                'rule_name': 'Low Risk IVR',
                'condition_description': 'Low KYC risk with IVR tool available',
                'condition_logic': 'context.get("kyc_risk") == "LOW"',
                'action': 'IVR',
                'priority': 1
            },
            {
                'rule_id': 'SOP-A005-02',
                'scenario_code': 'DORMANT_ACTIVATION',
                'rule_name': 'High Risk International Escalation',
                'condition_description': 'High KYC risk and international withdrawal',
                'condition_logic': 'context.get("kyc_risk") == "HIGH" and findings.get("is_international_withdrawal") == true',
                'action': 'ESCALATE',
                'priority': 2
            }
        ]
        
        for sop in sops:
            query = """
            MERGE (s:SOP {rule_id: $rule_id})
            SET s.scenario_code = $scenario_code,
                s.rule_name = $rule_name,
                s.condition_description = $condition_description,
                s.condition_logic = $condition_logic,
                s.action = $action,
                s.priority = $priority,
                s.version = 1,
                s.active = true,
                s.created_at = COALESCE(s.created_at, datetime())
            """
            db.execute_write(query, sop)
        
        logger.info(f"  ✓ Created/updated {len(sops)} SOPs")
        
        # ========================================================================
        # VERIFY DATA
        # ========================================================================
        logger.info("\n" + "="*60)
        logger.info("Verifying seed data...")
        
        # Check customers
        result = db.execute_query("MATCH (c:Customer) RETURN COUNT(c) as count", {})
        customer_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ Customers: {customer_count}")
        
        # Check accounts
        result = db.execute_query("MATCH (a:Account) RETURN COUNT(a) as count", {})
        account_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ Accounts: {account_count}")
        
        # Check transactions
        result = db.execute_query("MATCH (t:Transaction) RETURN COUNT(t) as count", {})
        txn_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ Transactions: {txn_count}")
        
        # Check SOPs
        result = db.execute_query("MATCH (s:SOP) RETURN COUNT(s) as count", {})
        sop_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ SOPs: {sop_count}")
        
        # Verify specific data
        result = db.execute_query(
            "MATCH (c:Customer {customer_id: 'CUST-101'}) RETURN c.kyc_risk as risk, c.email as email",
            {}
        )
        if result:
            logger.info(f"  ✓ CUST-101 kyc_risk: {result[0].get('risk')}, email: {result[0].get('email')}")
        
        # Verify all customers have test email
        result = db.execute_query(
            "MATCH (c:Customer) RETURN c.email as email, COUNT(c) as count",
            {}
        )
        if result:
            email = result[0].get('email')
            count = result[0].get('count', 0)
            logger.info(f"  ✓ All {count} customers configured with email: {email}")
        
        result = db.execute_query(
            "MATCH (a:Account {account_id: 'ACC-001'})-[:HAS_TRANSACTION]->(t:Transaction) RETURN COUNT(t) as count",
            {}
        )
        if result:
            logger.info(f"  ✓ ACC-001 transactions: {result[0].get('count')}")
        
        logger.info("="*60)
        logger.info("✓ Seed data creation complete!")
        logger.info("  You can now run the backend server and test scenarios.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating seed data: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Creating Neo4j Seed Data (Idempotent)")
    logger.info("="*60)
    
    success = create_seed_data()
    
    if not success:
        exit(1)

