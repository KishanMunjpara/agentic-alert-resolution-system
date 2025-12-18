"""
NEO4J CYPHER SCRIPTS - SEED DATA

Run these Cypher commands to populate initial test data.
Execute after schema_creation.cypher
"""

# ============================================================================
# STEP 1: CREATE TEST CUSTOMERS (5 customers for 5 alert scenarios)
# ============================================================================

# Customer 1 - For A-001 (Velocity Spike)
CREATE (c1:Customer {
  customer_id: 'CUST-101',
  first_name: 'John',
  last_name: 'Doe',
  email: 'kishanmunjpara2710@gmail.com',
  phone: '+1-555-0101',
  kyc_risk: 'HIGH',
  occupation: 'Teacher',
  employer: 'Lincoln High School',
  declared_income: 50000.0,
  profile_age_days: 365,
  created_at: datetime(),
  updated_at: datetime()
});

# Customer 2 - For A-002 (Structuring)
CREATE (c2:Customer {
  customer_id: 'CUST-102',
  first_name: 'Jane',
  last_name: 'Smith',
  email: 'kishanmunjpara2710@gmail.com',
  phone: '+1-555-0102',
  kyc_risk: 'MEDIUM',
  occupation: 'Engineer',
  employer: 'Tech Corp',
  declared_income: 100000.0,
  profile_age_days: 730,
  created_at: datetime(),
  updated_at: datetime()
});

# Customer 3 - For A-003 (KYC Inconsistency)
CREATE (c3:Customer {
  customer_id: 'CUST-103',
  first_name: 'Michael',
  last_name: 'Johnson',
  email: 'kishanmunjpara2710@gmail.com',
  phone: '+1-555-0103',
  kyc_risk: 'LOW',
  occupation: 'Jeweler',
  employer: 'Johnson Jewelry Store',
  declared_income: 75000.0,
  profile_age_days: 500,
  created_at: datetime(),
  updated_at: datetime()
});

# Customer 4 - For A-004 (Sanctions Hit)
CREATE (c4:Customer {
  customer_id: 'CUST-104',
  first_name: 'Sarah',
  last_name: 'Williams',
  email: 'kishanmunjpara2710@gmail.com',
  phone: '+1-555-0104',
  kyc_risk: 'HIGH',
  occupation: 'Consultant',
  employer: 'Global Consulting LLC',
  declared_income: 120000.0,
  profile_age_days: 1000,
  created_at: datetime(),
  updated_at: datetime()
});

# Customer 5 - For A-005 (Dormant Account Activation)
CREATE (c5:Customer {
  customer_id: 'CUST-105',
  first_name: 'Robert',
  last_name: 'Brown',
  email: 'kishanmunjpara2710@gmail.com',
  phone: '+1-555-0105',
  kyc_risk: 'LOW',
  occupation: 'Retired',
  employer: 'Self',
  declared_income: 30000.0,
  profile_age_days: 1825,
  created_at: datetime()-duration({years: 5}),
  updated_at: datetime()-duration({years: 5})
});

# ============================================================================
# STEP 2: CREATE TEST ACCOUNTS
# ============================================================================

MATCH (c1:Customer {customer_id: 'CUST-101'})
CREATE (c1)-[:OWNS {created_at: datetime()}]->(a1:Account {
  account_id: 'ACC-001',
  account_type: 'CHECKING',
  status: 'ACTIVE',
  currency: 'USD',
  balance: 50000.0,
  created_date: datetime()-duration({days: 365}),
  last_activity_date: datetime(),
  dormant_days: 0,
  created_at: datetime()
});

MATCH (c2:Customer {customer_id: 'CUST-102'})
CREATE (c2)-[:OWNS {created_at: datetime()}]->(a2:Account {
  account_id: 'ACC-002',
  account_type: 'CHECKING',
  status: 'ACTIVE',
  currency: 'USD',
  balance: 100000.0,
  created_date: datetime()-duration({days: 730}),
  last_activity_date: datetime(),
  dormant_days: 0,
  created_at: datetime()
});

MATCH (c3:Customer {customer_id: 'CUST-103'})
CREATE (c3)-[:OWNS {created_at: datetime()}]->(a3:Account {
  account_id: 'ACC-003',
  account_type: 'BUSINESS',
  status: 'ACTIVE',
  currency: 'USD',
  balance: 75000.0,
  created_date: datetime()-duration({days: 500}),
  last_activity_date: datetime(),
  dormant_days: 0,
  created_at: datetime()
});

MATCH (c4:Customer {customer_id: 'CUST-104'})
CREATE (c4)-[:OWNS {created_at: datetime()}]->(a4:Account {
  account_id: 'ACC-004',
  account_type: 'CHECKING',
  status: 'ACTIVE',
  currency: 'USD',
  balance: 120000.0,
  created_date: datetime()-duration({days: 1000}),
  last_activity_date: datetime(),
  dormant_days: 0,
  created_at: datetime()
});

MATCH (c5:Customer {customer_id: 'CUST-105'})
CREATE (c5)-[:OWNS {created_at: datetime()}]->(a5:Account {
  account_id: 'ACC-005',
  account_type: 'SAVINGS',
  status: 'DORMANT',
  currency: 'USD',
  balance: 50000.0,
  created_date: datetime()-duration({years: 5}),
  last_activity_date: datetime()-duration({days: 365}),
  dormant_days: 365,
  created_at: datetime()-duration({years: 5})
});

# ============================================================================
# STEP 3: CREATE SAMPLE TRANSACTIONS (for velocity check - A-001)
# ============================================================================

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t1:Transaction {
  txn_id: 'TXN-001',
  amount: 6000.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 40}),
  description: 'Transfer',
  counterparty: 'Unknown Entity A',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-001',
  created_at: datetime()
});

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t2:Transaction {
  txn_id: 'TXN-002',
  amount: 5500.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 35}),
  description: 'Transfer',
  counterparty: 'Unknown Entity B',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-002',
  created_at: datetime()
});

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t3:Transaction {
  txn_id: 'TXN-003',
  amount: 5200.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 30}),
  description: 'Transfer',
  counterparty: 'Unknown Entity C',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-003',
  created_at: datetime()
});

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t4:Transaction {
  txn_id: 'TXN-004',
  amount: 6000.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 25}),
  description: 'Transfer',
  counterparty: 'Unknown Entity D',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-004',
  created_at: datetime()
});

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t5:Transaction {
  txn_id: 'TXN-005',
  amount: 5500.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 20}),
  description: 'Transfer',
  counterparty: 'Unknown Entity E',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-005',
  created_at: datetime()
});

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t6:Transaction {
  txn_id: 'TXN-006',
  amount: 5200.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 15}),
  description: 'Transfer',
  counterparty: 'Unknown Entity F',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-006',
  created_at: datetime()
});

MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t7:Transaction {
  txn_id: 'TXN-007',
  amount: 5200.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 10}),
  description: 'Transfer',
  counterparty: 'Unknown Entity G',
  counterparty_mcc: 'GENERAL',
  reference: 'REF-007',
  created_at: datetime()
});

# Large inbound credit 2 hours prior to first outbound
MATCH (a1:Account {account_id: 'ACC-001'})
CREATE (a1)-[:HAS_TRANSACTION {added_at: datetime()}]->(t8:Transaction {
  txn_id: 'TXN-008',
  amount: 50000.0,
  currency: 'USD',
  transaction_type: 'INBOUND',
  timestamp: datetime()-duration({hours: 42}),
  description: 'Deposit',
  counterparty: 'Unknown Source',
  counterparty_mcc: 'DEPOSITS',
  reference: 'REF-008',
  created_at: datetime()
});

# ============================================================================
# STEP 4: CREATE SAMPLE TRANSACTIONS (for structuring - A-002)
# ============================================================================

MATCH (a2:Account {account_id: 'ACC-002'})
CREATE (a2)-[:HAS_TRANSACTION {added_at: datetime()}]->(s1:Transaction {
  txn_id: 'TXN-101',
  amount: 9100.0,
  currency: 'USD',
  transaction_type: 'INBOUND',
  timestamp: datetime()-duration({days: 7}),
  description: 'Deposit',
  counterparty: 'Cash Deposit',
  counterparty_mcc: 'CASH_DEPOSIT',
  reference: 'REF-101',
  created_at: datetime()
});

MATCH (a2:Account {account_id: 'ACC-002'})
CREATE (a2)-[:HAS_TRANSACTION {added_at: datetime()}]->(s2:Transaction {
  txn_id: 'TXN-102',
  amount: 9300.0,
  currency: 'USD',
  transaction_type: 'INBOUND',
  timestamp: datetime()-duration({days: 5}),
  description: 'Deposit',
  counterparty: 'Cash Deposit',
  counterparty_mcc: 'CASH_DEPOSIT',
  reference: 'REF-102',
  created_at: datetime()
});

MATCH (a2:Account {account_id: 'ACC-002'})
CREATE (a2)-[:HAS_TRANSACTION {added_at: datetime()}]->(s3:Transaction {
  txn_id: 'TXN-103',
  amount: 9500.0,
  currency: 'USD',
  transaction_type: 'INBOUND',
  timestamp: datetime()-duration({days: 3}),
  description: 'Deposit',
  counterparty: 'Cash Deposit',
  counterparty_mcc: 'CASH_DEPOSIT',
  reference: 'REF-103',
  created_at: datetime()
});

# ============================================================================
# STEP 5: CREATE SAMPLE TRANSACTIONS (for KYC Inconsistency - A-003)
# ============================================================================

MATCH (a3:Account {account_id: 'ACC-003'})
CREATE (a3)-[:HAS_TRANSACTION {added_at: datetime()}]->(k1:Transaction {
  txn_id: 'TXN-201',
  amount: 20000.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime(),
  description: 'Wire Transfer',
  counterparty: 'Precious Metals Trader Inc',
  counterparty_mcc: 'PRECIOUS_METALS',
  reference: 'REF-201',
  created_at: datetime()
});

# ============================================================================
# STEP 6: CREATE SANCTIONS ENTITIES
# ============================================================================

CREATE (se1:SanctionsEntity {
  entity_id: 'SANC-001',
  entity_name: 'Entity ABC',
  entity_type: 'ORGANIZATION',
  jurisdiction: 'HIGH_RISK_COUNTRY',
  list_type: 'SDN',
  risk_level: 'HIGH',
  created_at: datetime(),
  last_updated: datetime()
});

CREATE (se2:SanctionsEntity {
  entity_id: 'SANC-002',
  entity_name: 'Entity XYZ Corp',
  entity_type: 'ORGANIZATION',
  jurisdiction: 'RESTRICTED_REGION',
  list_type: 'CONSOLIDATED_LIST',
  risk_level: 'MEDIUM',
  created_at: datetime(),
  last_updated: datetime()
});

# ============================================================================
# STEP 7: CREATE SAMPLE TRANSACTIONS (for Sanctions Hit - A-004)
# ============================================================================

MATCH (a4:Account {account_id: 'ACC-004'}), (se:SanctionsEntity {entity_id: 'SANC-001'})
CREATE (a4)-[:HAS_TRANSACTION {added_at: datetime()}]->(sn1:Transaction {
  txn_id: 'TXN-301',
  amount: 50000.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 5}),
  description: 'Wire Transfer',
  counterparty: 'Entity ABC',
  counterparty_mcc: 'WIRE_TRANSFER',
  reference: 'REF-301',
  created_at: datetime()
})
CREATE (sn1)-[:TO_SANCTIONED_ENTITY {match_score: 92}]->(se);

# ============================================================================
# STEP 8: CREATE SAMPLE TRANSACTIONS (for Dormant Account Activation - A-005)
# ============================================================================

MATCH (a5:Account {account_id: 'ACC-005'})
CREATE (a5)-[:HAS_TRANSACTION {added_at: datetime()}]->(d1:Transaction {
  txn_id: 'TXN-401',
  amount: 15000.0,
  currency: 'USD',
  transaction_type: 'INBOUND',
  timestamp: datetime(),
  description: 'Wire Deposit',
  counterparty: 'External Source',
  counterparty_mcc: 'WIRE_TRANSFER',
  reference: 'REF-401',
  created_at: datetime()
});

MATCH (a5:Account {account_id: 'ACC-005'})
CREATE (a5)-[:HAS_TRANSACTION {added_at: datetime()}]->(d2:Transaction {
  txn_id: 'TXN-402',
  amount: 14500.0,
  currency: 'USD',
  transaction_type: 'OUTBOUND',
  timestamp: datetime()-duration({hours: 1}),
  description: 'ATM Withdrawal',
  counterparty: 'ATM Network',
  counterparty_mcc: 'ATM_WITHDRAWAL',
  reference: 'REF-402',
  created_at: datetime()
});

# ============================================================================
# STEP 9: CREATE STANDARD OPERATING PROCEDURES (SOPs)
# ============================================================================

# SOP for A-001 (Velocity Spike)
CREATE (sop1:SOP {
  rule_id: 'SOP-A001-01',
  scenario_code: 'VELOCITY_SPIKE',
  rule_name: 'High Velocity High Risk Escalation',
  condition_description: 'Transaction count >= 5 AND total amount > 25000 AND kyc_risk = HIGH',
  condition_logic: 'findings.get("transaction_count", 0) >= 5 and findings.get("total_amount", 0) > 25000 and context.get("kyc_risk") == "HIGH"',
  action: 'ESCALATE',
  priority: 1,
  version: 1,
  active: true,
  created_at: datetime()
});

CREATE (sop2:SOP {
  rule_id: 'SOP-A001-02',
  scenario_code: 'VELOCITY_SPIKE',
  rule_name: 'Known Business Cycle Close',
  condition_description: 'Velocity spike explained by known business cycle',
  condition_logic: 'findings.get("is_business_cycle") == true',
  action: 'CLOSE',
  priority: 2,
  version: 1,
  active: true,
  created_at: datetime()
});

# SOP for A-002 (Structuring)
CREATE (sop3:SOP {
  rule_id: 'SOP-A002-01',
  scenario_code: 'STRUCTURING',
  rule_name: 'Linked Accounts Aggregate Escalation',
  condition_description: 'Linked accounts aggregate > 28000',
  condition_logic: 'findings.get("linked_accounts_aggregate", 0) > 28000',
  action: 'ESCALATE',
  priority: 1,
  version: 1,
  active: true,
  created_at: datetime()
});

CREATE (sop4:SOP {
  rule_id: 'SOP-A002-02',
  scenario_code: 'STRUCTURING',
  rule_name: 'Legitimate Business RFI',
  condition_description: 'Geographically diverse and legitimate business receipts',
  condition_logic: 'findings.get("is_legitimate_business") == true',
  action: 'RFI',
  priority: 2,
  version: 1,
  active: true,
  created_at: datetime()
});

# SOP for A-003 (KYC Inconsistency)
CREATE (sop5:SOP {
  rule_id: 'SOP-A003-01',
  scenario_code: 'KYC_INCONSISTENCY',
  rule_name: 'Matching Occupation Close',
  condition_description: 'Occupation confirmed as Jeweler or Trader',
  condition_logic: 'context.get("occupation") in ["Jeweler", "Precious Metals Trader", "Jeweler/Goldsmith"]',
  action: 'CLOSE',
  priority: 1,
  version: 1,
  active: true,
  created_at: datetime()
});

CREATE (sop6:SOP {
  rule_id: 'SOP-A003-02',
  scenario_code: 'KYC_INCONSISTENCY',
  rule_name: 'Mismatched Profile Escalation',
  condition_description: 'Profile is Teacher/Student sending to Precious Metals',
  condition_logic: 'context.get("occupation") in ["Teacher", "Student", "Government Employee"]',
  action: 'ESCALATE',
  priority: 2,
  version: 1,
  active: true,
  created_at: datetime()
});

# SOP for A-004 (Sanctions Hit)
CREATE (sop7:SOP {
  rule_id: 'SOP-A004-01',
  scenario_code: 'SANCTIONS_HIT',
  rule_name: 'High Risk Jurisdiction Escalation',
  condition_description: 'True match or high-risk jurisdiction',
  condition_logic: 'findings.get("match_score", 0) >= 0.90 or context.get("jurisdiction") == "HIGH_RISK"',
  action: 'ESCALATE',
  priority: 1,
  version: 1,
  active: true,
  created_at: datetime()
});

CREATE (sop8:SOP {
  rule_id: 'SOP-A004-02',
  scenario_code: 'SANCTIONS_HIT',
  rule_name: 'False Positive Close',
  condition_description: 'Proven false positive (common name)',
  condition_logic: 'findings.get("is_false_positive") == true',
  action: 'CLOSE',
  priority: 2,
  version: 1,
  active: true,
  created_at: datetime()
});

# SOP for A-005 (Dormant Account Activation)
CREATE (sop9:SOP {
  rule_id: 'SOP-A005-01',
  scenario_code: 'DORMANT_ACTIVATION',
  rule_name: 'Low Risk IVR',
  condition_description: 'Low KYC risk with IVR tool available',
  condition_logic: 'context.get("kyc_risk") == "LOW"',
  action: 'IVR',
  priority: 1,
  version: 1,
  active: true,
  created_at: datetime()
});

CREATE (sop10:SOP {
  rule_id: 'SOP-A005-02',
  scenario_code: 'DORMANT_ACTIVATION',
  rule_name: 'High Risk International Escalation',
  condition_description: 'High KYC risk and international withdrawal',
  condition_logic: 'context.get("kyc_risk") == "HIGH" and findings.get("is_international_withdrawal") == true',
  action: 'ESCALATE',
  priority: 2,
  version: 1,
  active: true,
  created_at: datetime()
});

# ============================================================================
# VERIFICATION QUERIES (Run these to verify data was created)
# ============================================================================

# Count nodes by type
# MATCH (n:Customer) RETURN COUNT(n) as customer_count;
# MATCH (n:Account) RETURN COUNT(n) as account_count;
# MATCH (n:Transaction) RETURN COUNT(n) as transaction_count;
# MATCH (n:SOP) RETURN COUNT(n) as sop_count;

# View all customers
# MATCH (c:Customer) RETURN c;

# View customer with accounts
# MATCH (c:Customer)-[:OWNS]->(a:Account) RETURN c, a LIMIT 10;

# View all SOPs
# MATCH (s:SOP) RETURN s;

