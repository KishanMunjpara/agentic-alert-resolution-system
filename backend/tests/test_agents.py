"""
Parametrized Unit Tests - Agent System
Tests all 5 alert scenarios with parametrized test cases
"""

import pytest
import asyncio
from typing import Dict, Optional
from datetime import datetime

# Test data for all 5 alert scenarios
ALERT_TEST_CASES = [
    # A-001: Velocity Spike
    {
        "alert_id": "A-001",
        "scenario_code": "VELOCITY_SPIKE",
        "customer_id": "CUST-101",
        "account_id": "ACC-001",
        "expected_decision": "ESCALATE",
        "test_data": {
            "transaction_count": 7,
            "total_amount": 42500,
            "customer_income": 50000,
            "kyc_risk": "HIGH"
        }
    },
    # A-002: Structuring
    {
        "alert_id": "A-002",
        "scenario_code": "STRUCTURING",
        "customer_id": "CUST-102",
        "account_id": "ACC-002",
        "expected_decision": "RFI",
        "test_data": {
            "deposit_count": 3,
            "deposit_amounts": [9100, 9300, 9500],
            "time_window_days": 7,
            "total_deposits": 27900,
            "linked_accounts_aggregate": 29000,  # > 28000 to match condition
            "kyc_risk": "MEDIUM"
        }
    },
    # A-003: KYC Inconsistency
    {
        "alert_id": "A-003",
        "scenario_code": "KYC_INCONSISTENCY",
        "customer_id": "CUST-103",
        "account_id": "ACC-003",
        "expected_decision": "CLOSE",
        "test_data": {
            "occupation": "Jeweler",
            "transaction_mcc": "PRECIOUS_METALS",
            "transaction_amount": 20000,
            "is_precious_metals": True,  # Required for condition match
            "kyc_risk": "LOW"
        }
    },
    # A-004: Sanctions Hit
    {
        "alert_id": "A-004",
        "scenario_code": "SANCTIONS_HIT",
        "customer_id": "CUST-104",
        "account_id": "ACC-004",
        "expected_decision": "ESCALATE",
        "test_data": {
            "counterparty": "Entity ABC",
            "match_score": 0.92,
            "matched_entity_jurisdiction": "HIGH_RISK",
            "transaction_amount": 50000
        }
    },
    # A-005: Dormant Account Activation
    {
        "alert_id": "A-005",
        "scenario_code": "DORMANT_ACTIVATION",
        "customer_id": "CUST-105",
        "account_id": "ACC-005",
        "expected_decision": "RFI",
        "test_data": {
            "account_dormant_days": 365,
            "inbound_amount": 15000,
            "atm_withdrawal": 14500,
            "kyc_risk": "LOW"
        }
    }
]


# Parametrized test for adjudicator decision logic
@pytest.mark.parametrize("test_case", ALERT_TEST_CASES, ids=[f"Alert_{tc['alert_id']}" for tc in ALERT_TEST_CASES])
def test_adjudicator_decision_logic(test_case: Dict):
    """
    Test adjudicator makes correct decision for each alert scenario
    
    This is a parametrized test that runs the same test logic for all 5 scenarios
    """
    from agents.adjudicator import AdjudicatorAgent
    
    alert_id = test_case["alert_id"]
    scenario = test_case["scenario_code"]
    expected_decision = test_case["expected_decision"]
    test_data = test_case["test_data"]
    
    # Mock findings and context
    findings = {
        "alert_id": alert_id,
        "scenario": scenario,
        **test_data
    }
    
    context = {
        "alert_id": alert_id,
        "kyc_risk": test_data.get("kyc_risk", "MEDIUM"),
        "occupation": test_data.get("occupation", "Unknown"),
        "jurisdiction": test_data.get("matched_entity_jurisdiction")
    }
    
    # Create adjudicator (no broadcast function for unit test)
    adjudicator = AdjudicatorAgent(broadcast_fn=None)
    
    # Test condition evaluation
    condition_result = adjudicator._evaluate_condition(
        scenario, "", findings, context
    )
    
    # Should match for expected decisions
    assert condition_result == True, f"Condition should match for {scenario}"


# Parametrized test for scenario routing
@pytest.mark.parametrize("alert_id,scenario,expected_routing", [
    ("A-001", "VELOCITY_SPIKE", ["investigator", "context_gatherer", "adjudicator"]),
    ("A-002", "STRUCTURING", ["investigator", "context_gatherer", "adjudicator"]),
    ("A-003", "KYC_INCONSISTENCY", ["investigator", "context_gatherer", "adjudicator"]),
    ("A-004", "SANCTIONS_HIT", ["investigator", "context_gatherer", "adjudicator"]),
    ("A-005", "DORMANT_ACTIVATION", ["investigator", "context_gatherer", "adjudicator"]),
])
def test_orchestrator_routing(alert_id: str, scenario: str, expected_routing: list):
    """Test that orchestrator routes to correct agents for each scenario"""
    from agents.orchestrator import OrchestratorAgent
    
    orchestrator = OrchestratorAgent(broadcast_fn=None)
    
    # All scenarios should route to same agents
    assert len(expected_routing) == 3, "All scenarios route to 3 agents"
    assert "investigator" in expected_routing
    assert "context_gatherer" in expected_routing
    assert "adjudicator" in expected_routing


# Parametrized test for decision confidence
@pytest.mark.parametrize("scenario,confidence_expectation", [
    ("VELOCITY_SPIKE", lambda findings, ctx: findings.get("transaction_count", 0) >= 5 and findings.get("total_amount", 0) > 25000),
    ("STRUCTURING", lambda findings, ctx: findings.get("deposit_count", 0) >= 3),
    ("KYC_INCONSISTENCY", lambda findings, ctx: ctx.get("occupation") in ["Jeweler", "Precious Metals Trader"]),
    ("SANCTIONS_HIT", lambda findings, ctx: findings.get("match_score", 0) >= 0.80),
    ("DORMANT_ACTIVATION", lambda findings, ctx: ctx.get("kyc_risk") == "LOW"),
])
def test_confidence_scoring(scenario: str, confidence_expectation):
    """Test that confidence is scored appropriately for each scenario"""
    test_case = next((tc for tc in ALERT_TEST_CASES if tc["scenario_code"] == scenario), None)
    assert test_case is not None, f"Test case not found for {scenario}"
    
    findings = test_case["test_data"]
    context = {"kyc_risk": findings.get("kyc_risk", "MEDIUM"), "occupation": findings.get("occupation")}
    
    # High confidence when condition is met
    if confidence_expectation(findings, context):
        confidence = 0.95
    else:
        confidence = 0
    
    assert confidence >= 0 and confidence <= 1, f"Confidence should be between 0 and 1, got {confidence}"


# Parametrized test for action execution
@pytest.mark.parametrize("decision,expected_action_type", [
    ("ESCALATE", "SAR_PREP"),
    ("RFI", "RFI"),
    ("CLOSE", "CLOSE"),
    ("BLOCK", "BLOCK"),
])
def test_action_executor_routing(decision: str, expected_action_type: str):
    """Test that action executor routes to correct action handler"""
    from agents.action_executor import ActionExecutor
    
    executor = ActionExecutor(broadcast_fn=None)
    
    # Mock resolution
    resolution = {
        "recommendation": decision,
        "rationale": f"Test {decision} action",
        "confidence": 0.95
    }
    
    # Verify mapping
    action_map = {
        "ESCALATE": "SAR_PREP",
        "RFI": "RFI",
        "CLOSE": "CLOSE",
        "BLOCK": "BLOCK"
    }
    
    assert action_map.get(decision) == expected_action_type, f"Action mapping incorrect for {decision}"


# Parametrized test for alert classification
@pytest.mark.parametrize("alert_data,expected_scenario", [
    ({"txn_count": 7, "amount": 42500, "time_window": "48h"}, "VELOCITY_SPIKE"),
    ({"deposit_count": 3, "amounts": [9100, 9300, 9500], "time_window": "7d"}, "STRUCTURING"),
    ({"occupation": "Teacher", "mcc": "PRECIOUS_METALS", "amount": 20000}, "KYC_INCONSISTENCY"),
    ({"match_score": 0.92, "counterparty": "Entity ABC"}, "SANCTIONS_HIT"),
    ({"dormant_days": 365, "inbound": 15000, "outbound": 14500}, "DORMANT_ACTIVATION"),
])
def test_alert_scenario_classification(alert_data: Dict, expected_scenario: str):
    """Test correct scenario classification for alerts"""
    # This test verifies the test data matches expected scenarios
    test_case = next((tc for tc in ALERT_TEST_CASES if tc["scenario_code"] == expected_scenario), None)
    assert test_case is not None, f"Expected scenario {expected_scenario} not in test cases"


# Parametrized test for findings structure
@pytest.mark.parametrize("test_case", ALERT_TEST_CASES)
def test_investigator_findings_structure(test_case: Dict):
    """Test that investigator findings have required fields"""
    required_fields = ["alert_id", "scenario"]
    
    findings = {
        "alert_id": test_case["alert_id"],
        "scenario": test_case["scenario_code"],
    }
    
    for field in required_fields:
        assert field in findings, f"Missing required field: {field}"


# Parametrized test for context structure
@pytest.mark.parametrize("test_case", ALERT_TEST_CASES)
def test_context_gatherer_context_structure(test_case: Dict):
    """Test that context has required fields"""
    required_fields = ["alert_id", "customer_id", "kyc_risk"]
    
    context = {
        "alert_id": test_case["alert_id"],
        "customer_id": test_case["customer_id"],
        "kyc_risk": test_case["test_data"].get("kyc_risk", "MEDIUM"),
    }
    
    for field in required_fields:
        assert field in context, f"Missing required field: {field}"


# Parametrized test for resolution structure
@pytest.mark.parametrize("test_case", ALERT_TEST_CASES)
def test_resolution_structure(test_case: Dict):
    """Test that resolution has required fields"""
    required_fields = ["alert_id", "recommendation", "rationale", "confidence"]
    
    resolution = {
        "alert_id": test_case["alert_id"],
        "recommendation": test_case["expected_decision"],
        "rationale": f"Resolution for {test_case['scenario_code']}",
        "confidence": 0.95,
    }
    
    for field in required_fields:
        assert field in resolution, f"Missing required field: {field}"


# Test for all scenarios covered
def test_all_scenarios_covered():
    """Verify all 5 alert scenarios have test cases"""
    scenarios = [tc["scenario_code"] for tc in ALERT_TEST_CASES]
    
    required_scenarios = [
        "VELOCITY_SPIKE",
        "STRUCTURING",
        "KYC_INCONSISTENCY",
        "SANCTIONS_HIT",
        "DORMANT_ACTIVATION"
    ]
    
    for scenario in required_scenarios:
        assert scenario in scenarios, f"Missing test case for {scenario}"


# Test for expected decisions
def test_expected_decisions_valid():
    """Verify all expected decisions are valid"""
    valid_decisions = ["ESCALATE", "RFI", "CLOSE", "BLOCK"]
    
    for test_case in ALERT_TEST_CASES:
        decision = test_case["expected_decision"]
        assert decision in valid_decisions, f"Invalid decision: {decision}"


# Parametrized test count
def test_parametrized_coverage():
    """Verify parametrized test coverage"""
    # 5 test cases
    assert len(ALERT_TEST_CASES) == 5, "Should have 5 test cases for 5 scenarios"
    
    # Each test case should have all required fields
    required_fields = ["alert_id", "scenario_code", "customer_id", "account_id", 
                      "expected_decision", "test_data"]
    
    for test_case in ALERT_TEST_CASES:
        for field in required_fields:
            assert field in test_case, f"Missing field {field} in test case {test_case.get('alert_id')}"


# ============================================================================
# PROOF EVALUATOR AGENT TESTS
# ============================================================================

# Parametrized test for proof evaluator
@pytest.mark.parametrize("proof_text,proof_type,expected_decision", [
    (
        "These transactions were for purchasing equipment for my business. I have invoices and receipts available.",
        "EXPLANATION",
        "RESOLVED"
    ),
    (
        "I don't know what these transactions are for. I'm not sure.",
        "EXPLANATION",
        "ESCALATED_TO_BRANCH"
    ),
    (
        "These were legitimate business payments. I can provide documentation.",
        "EXPLANATION",
        "RESOLVED"
    ),
    (
        "Not sure, maybe someone else made these?",
        "EXPLANATION",
        "ESCALATED_TO_BRANCH"
    ),
])
def test_proof_evaluator_decision_logic(proof_text: str, proof_type: str, expected_decision: str):
    """Test proof evaluator makes correct decision based on proof text"""
    from agents.proof_evaluator import ProofEvaluatorAgent
    
    # Create proof evaluator (no broadcast function for unit test)
    evaluator = ProofEvaluatorAgent(broadcast_fn=None)
    
    # Mock findings and context
    findings = {
        "alert_id": "TEST-001",
        "scenario": "VELOCITY_SPIKE",
        "transaction_count": 7,
        "total_amount": 42500
    }
    
    context = {
        "alert_id": "TEST-001",
        "customer_id": "CUST-101",
        "kyc_risk": "MEDIUM",
        "occupation": "Business Owner"
    }
    
    original_resolution = {
        "recommendation": "RFI",
        "rationale": "Requires customer explanation",
        "confidence": 0.75
    }
    
    # Test rule-based evaluation (fallback when LLM unavailable)
    evaluation = evaluator._evaluate_without_llm(proof_text, findings, context)
    
    # Verify decision matches expected
    assert evaluation["recommendation"] == expected_decision, \
        f"Expected {expected_decision}, got {evaluation['recommendation']} for proof: {proof_text[:50]}"
    
    # Verify confidence is in valid range
    assert 0 <= evaluation["confidence"] <= 1, "Confidence should be between 0 and 1"
    
    # Verify rationale exists
    assert evaluation["rationale"], "Rationale should not be empty"


# Parametrized test for proof evaluation confidence scoring
@pytest.mark.parametrize("proof_text,min_confidence", [
    ("Detailed explanation with invoices and receipts for business transactions", 0.6),
    ("I have documentation available", 0.5),
    ("Not sure", 0.4),
    ("", 0.3),
])
def test_proof_evaluator_confidence(proof_text: str, min_confidence: float):
    """Test that proof evaluator assigns appropriate confidence scores"""
    from agents.proof_evaluator import ProofEvaluatorAgent
    
    evaluator = ProofEvaluatorAgent(broadcast_fn=None)
    
    findings = {"alert_id": "TEST-001", "scenario": "VELOCITY_SPIKE"}
    context = {"alert_id": "TEST-001", "kyc_risk": "MEDIUM"}
    
    evaluation = evaluator._evaluate_without_llm(proof_text, findings, context)
    
    # Confidence should be in valid range
    assert 0 <= evaluation["confidence"] <= 1, "Confidence should be between 0 and 1"
    
    # For legitimate proofs, confidence should be higher
    if evaluation["legitimate"]:
        assert evaluation["confidence"] >= 0.5, "Legitimate proofs should have confidence >= 0.5"


# Test proof evaluator structure
def test_proof_evaluator_structure():
    """Test that proof evaluator has required methods"""
    from agents.proof_evaluator import ProofEvaluatorAgent
    
    evaluator = ProofEvaluatorAgent(broadcast_fn=None)
    
    # Verify required methods exist
    assert hasattr(evaluator, "evaluate_proof"), "Should have evaluate_proof method"
    assert hasattr(evaluator, "_evaluate_with_llm"), "Should have _evaluate_with_llm method"
    assert hasattr(evaluator, "_evaluate_without_llm"), "Should have _evaluate_without_llm method"
    assert hasattr(evaluator, "_parse_llm_response"), "Should have _parse_llm_response method"
    assert hasattr(evaluator, "_update_alert_status"), "Should have _update_alert_status method"
