"""
NEO4J CYPHER SCRIPTS - SCHEMA CREATION

Run these Cypher commands in Neo4j Browser to create the database schema.
These scripts are organized by node type and relationship.
"""

# ============================================================================
# STEP 1: CREATE CONSTRAINTS (Execute in order)
# ============================================================================

# Customer Constraints
CREATE CONSTRAINT customer_id ON (c:Customer) ASSERT c.customer_id IS UNIQUE;
CREATE CONSTRAINT customer_email ON (c:Customer) ASSERT c.email IS UNIQUE;
CREATE INDEX ON :Customer(kyc_risk);
CREATE INDEX ON :Customer(created_at);

# Account Constraints
CREATE CONSTRAINT account_id ON (a:Account) ASSERT a.account_id IS UNIQUE;
CREATE INDEX ON :Account(status);
CREATE INDEX ON :Account(created_date);

# Transaction Constraints
CREATE CONSTRAINT txn_id ON (t:Transaction) ASSERT t.txn_id IS UNIQUE;
CREATE INDEX ON :Transaction(timestamp);
CREATE INDEX ON :Transaction(transaction_type);

# Alert Constraints
CREATE CONSTRAINT alert_id ON (a:Alert) ASSERT a.alert_id IS UNIQUE;
CREATE INDEX ON :Alert(status);
CREATE INDEX ON :Alert(scenario_code);
CREATE INDEX ON :Alert(created_at);

# Resolution Constraints
CREATE CONSTRAINT resolution_id ON (r:Resolution) ASSERT r.resolution_id IS UNIQUE;
CREATE INDEX ON :Resolution(recommendation);

# SOP Constraints
CREATE CONSTRAINT sop_rule_id ON (s:SOP) ASSERT s.rule_id IS UNIQUE;
CREATE INDEX ON :SOP(scenario_code);
CREATE INDEX ON :SOP(active);

# SanctionsEntity Constraints
CREATE CONSTRAINT entity_id ON (s:SanctionsEntity) ASSERT s.entity_id IS UNIQUE;
CREATE INDEX ON :SanctionsEntity(entity_name);

# Event Constraints
CREATE CONSTRAINT event_id ON (e:Event) ASSERT e.event_id IS UNIQUE;
CREATE INDEX ON :Event(alert_id);
CREATE INDEX ON :Event(timestamp);
CREATE INDEX ON :Event(event_type);

# ============================================================================
# STEP 2: VERIFY SCHEMA (Run query to verify)
# ============================================================================

# To verify all constraints and indexes were created:
# CALL db.constraints()
# CALL db.indexes()

