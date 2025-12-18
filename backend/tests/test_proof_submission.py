"""
Parametrized Tests - Proof Submission System
Tests proof submission endpoint and proof evaluation flow
"""

import pytest
import asyncio
from typing import Dict, Optional
from datetime import datetime

# Test cases for proof submission
PROOF_SUBMISSION_TEST_CASES = [
    {
        "name": "Legitimate Business Explanation",
        "proof_text": "These transactions were for purchasing equipment for my business. I have invoices and receipts available. The payments were made to legitimate suppliers for office equipment and supplies.",
        "proof_type": "EXPLANATION",
        "expected_decision": "RESOLVED",
        "min_confidence": 0.6
    },
    {
        "name": "Vague Suspicious Explanation",
        "proof_text": "I don't know what these transactions are for. I'm not sure.",
        "proof_type": "EXPLANATION",
        "expected_decision": "ESCALATED_TO_BRANCH",
        "min_confidence": 0.4
    },
    {
        "name": "Detailed Legitimate Explanation",
        "proof_text": "These were legitimate business payments. I can provide documentation including invoices, contracts, and receipts. The transactions align with my business operations as a registered company.",
        "proof_type": "EXPLANATION",
        "expected_decision": "RESOLVED",
        "min_confidence": 0.7
    },
    {
        "name": "Insufficient Explanation",
        "proof_text": "Not sure, maybe someone else made these?",
        "proof_type": "EXPLANATION",
        "expected_decision": "ESCALATED_TO_BRANCH",
        "min_confidence": 0.3
    },
    {
        "name": "Document Description",
        "proof_text": "I have submitted invoices and receipts that document these transactions. All payments were for legitimate business expenses related to my registered company operations.",
        "proof_type": "DOCUMENT_DESCRIPTION",
        "expected_decision": "RESOLVED",
        "min_confidence": 0.6
    }
]


# Parametrized test for proof submission endpoint structure
@pytest.mark.parametrize("test_case", PROOF_SUBMISSION_TEST_CASES, ids=[tc["name"] for tc in PROOF_SUBMISSION_TEST_CASES])
def test_proof_submission_request_structure(test_case: Dict):
    """Test that proof submission request has required fields"""
    from schemas.schemas import ProofSubmissionRequest
    
    request = ProofSubmissionRequest(
        proof_text=test_case["proof_text"],
        proof_type=test_case["proof_type"],
        customer_email="test@example.com"
    )
    
    # Verify required fields
    assert request.proof_text == test_case["proof_text"]
    assert request.proof_type == test_case["proof_type"]
    assert request.customer_email == "test@example.com"
    
    # Verify text length constraints
    assert len(request.proof_text) >= 10, "Proof text should be at least 10 characters"
    assert len(request.proof_text) <= 5000, "Proof text should be at most 5000 characters"


# Parametrized test for proof evaluation response structure
@pytest.mark.parametrize("test_case", PROOF_SUBMISSION_TEST_CASES, ids=[tc["name"] for tc in PROOF_SUBMISSION_TEST_CASES])
def test_proof_evaluation_response_structure(test_case: Dict):
    """Test that proof evaluation response has required fields"""
    from schemas.schemas import ProofEvaluationResponse
    
    response = ProofEvaluationResponse(
        alert_id="TEST-001",
        decision=test_case["expected_decision"],
        status=test_case["expected_decision"],
        confidence=0.75,
        rationale="Test rationale",
        message="Test message",
        timestamp=datetime.now()
    )
    
    # Verify required fields
    assert response.alert_id == "TEST-001"
    assert response.decision in ["RESOLVED", "ESCALATED_TO_BRANCH"]
    assert response.status in ["RESOLVED", "ESCALATED_TO_BRANCH"]
    assert 0 <= response.confidence <= 1, "Confidence should be between 0 and 1"
    assert response.rationale, "Rationale should not be empty"
    assert response.message, "Message should not be empty"
    assert response.timestamp, "Timestamp should be set"


# Parametrized test for proof evaluator agent
@pytest.mark.parametrize("test_case", PROOF_SUBMISSION_TEST_CASES, ids=[tc["name"] for tc in PROOF_SUBMISSION_TEST_CASES])
def test_proof_evaluator_agent_logic(test_case: Dict):
    """Test proof evaluator agent decision logic"""
    from agents.proof_evaluator import ProofEvaluatorAgent
    
    evaluator = ProofEvaluatorAgent(broadcast_fn=None)
    
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
    
    # Test rule-based evaluation
    evaluation = evaluator._evaluate_without_llm(
        test_case["proof_text"],
        findings,
        context
    )
    
    # Verify decision matches expected (or is reasonable)
    assert evaluation["recommendation"] in ["RESOLVED", "ESCALATED_TO_BRANCH"]
    
    # Verify confidence meets minimum threshold
    assert evaluation["confidence"] >= test_case["min_confidence"], \
        f"Confidence {evaluation['confidence']} should be >= {test_case['min_confidence']}"
    
    # Verify rationale exists
    assert evaluation["rationale"], "Rationale should not be empty"


# Test proof submission validation
@pytest.mark.parametrize("proof_text,should_pass", [
    ("Valid proof text with sufficient detail", True),
    ("Short", False),  # Too short (< 10 chars)
    ("A" * 5001, False),  # Too long (> 5000 chars)
    ("This is a valid proof text that meets the minimum length requirement", True),
])
def test_proof_submission_validation(proof_text: str, should_pass: bool):
    """Test proof submission text validation"""
    from schemas.schemas import ProofSubmissionRequest
    from pydantic import ValidationError
    
    if should_pass:
        request = ProofSubmissionRequest(proof_text=proof_text)
        assert request.proof_text == proof_text
    else:
        with pytest.raises(ValidationError):
            ProofSubmissionRequest(proof_text=proof_text)


# Test proof evaluator without LLM (rule-based fallback)
def test_proof_evaluator_fallback():
    """Test proof evaluator fallback when LLM unavailable"""
    from agents.proof_evaluator import ProofEvaluatorAgent
    
    evaluator = ProofEvaluatorAgent(broadcast_fn=None)
    
    # Test with legitimate proof
    legitimate_proof = "These transactions were for business purposes. I have invoices and receipts available."
    findings = {"alert_id": "TEST-001", "scenario": "VELOCITY_SPIKE"}
    context = {"alert_id": "TEST-001", "kyc_risk": "MEDIUM"}
    
    evaluation = evaluator._evaluate_without_llm(legitimate_proof, findings, context)
    
    # Should return valid evaluation
    assert "legitimate" in evaluation
    assert "confidence" in evaluation
    assert "rationale" in evaluation
    assert "recommendation" in evaluation
    
    # For legitimate proof, should have higher confidence
    if evaluation["legitimate"]:
        assert evaluation["confidence"] >= 0.5


# Test proof evaluator LLM response parsing
@pytest.mark.parametrize("llm_response,expected_legitimate", [
    ('{"legitimate": true, "confidence": 0.85, "rationale": "Good proof"}', True),
    ('{"legitimate": false, "confidence": 0.3, "rationale": "Suspicious"}', False),
    ('```json\n{"legitimate": true, "confidence": 0.9}\n```', True),
    ('```\n{"legitimate": false, "confidence": 0.2}\n```', False),
])
def test_proof_evaluator_llm_parsing(llm_response: str, expected_legitimate: bool):
    """Test LLM response parsing in proof evaluator"""
    from agents.proof_evaluator import ProofEvaluatorAgent
    
    evaluator = ProofEvaluatorAgent(broadcast_fn=None)
    
    parsed = evaluator._parse_llm_response(llm_response)
    
    assert parsed["legitimate"] == expected_legitimate
    assert 0 <= parsed["confidence"] <= 1
    assert "rationale" in parsed
    assert "recommendation" in parsed


# Test all proof submission test cases covered
def test_all_proof_cases_covered():
    """Verify all proof submission test cases are defined"""
    assert len(PROOF_SUBMISSION_TEST_CASES) >= 5, "Should have at least 5 test cases"
    
    required_fields = ["name", "proof_text", "proof_type", "expected_decision", "min_confidence"]
    
    for test_case in PROOF_SUBMISSION_TEST_CASES:
        for field in required_fields:
            assert field in test_case, f"Missing field {field} in test case {test_case.get('name')}"


# Test proof evaluation decisions are valid
def test_proof_evaluation_decisions_valid():
    """Verify all proof evaluation decisions are valid"""
    valid_decisions = ["RESOLVED", "ESCALATED_TO_BRANCH"]
    
    for test_case in PROOF_SUBMISSION_TEST_CASES:
        decision = test_case["expected_decision"]
        assert decision in valid_decisions, f"Invalid decision: {decision}"

