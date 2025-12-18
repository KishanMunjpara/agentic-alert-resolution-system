"""
Pytest Configuration and Fixtures
"""

import pytest
import sys
import os
from typing import Generator

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))


@pytest.fixture
def sample_alert_data():
    """Provide sample alert data for testing"""
    return {
        "alert_id": "TEST-001",
        "scenario_code": "VELOCITY_SPIKE",
        "customer_id": "CUST-TEST",
        "account_id": "ACC-TEST",
        "severity": "HIGH",
        "created_at": "2024-01-15T10:30:00Z"
    }


@pytest.fixture
def sample_findings():
    """Provide sample investigation findings"""
    return {
        "alert_id": "TEST-001",
        "transaction_count": 7,
        "total_amount": 42500,
        "scenario": "VELOCITY_SPIKE",
        "threshold_exceeded": True
    }


@pytest.fixture
def sample_context():
    """Provide sample context data"""
    return {
        "alert_id": "TEST-001",
        "customer_id": "CUST-TEST",
        "customer_name": "Test User",
        "kyc_risk": "HIGH",
        "occupation": "Teacher",
        "declared_income": 50000,
        "profile_age_days": 365
    }


@pytest.fixture
def sample_resolution():
    """Provide sample resolution"""
    return {
        "alert_id": "TEST-001",
        "recommendation": "ESCALATE",
        "rationale": "Velocity spike with high KYC risk",
        "confidence": 0.95,
        "findings": {
            "transaction_count": 7,
            "total_amount": 42500
        }
    }


@pytest.fixture
def test_scenarios():
    """Provide all 5 test scenarios"""
    return [
        {
            "alert_id": "A-001",
            "scenario": "VELOCITY_SPIKE",
            "expected_decision": "ESCALATE"
        },
        {
            "alert_id": "A-002",
            "scenario": "STRUCTURING",
            "expected_decision": "RFI"
        },
        {
            "alert_id": "A-003",
            "scenario": "KYC_INCONSISTENCY",
            "expected_decision": "CLOSE"
        },
        {
            "alert_id": "A-004",
            "scenario": "SANCTIONS_HIT",
            "expected_decision": "ESCALATE"
        },
        {
            "alert_id": "A-005",
            "scenario": "DORMANT_ACTIVATION",
            "expected_decision": "RFI"
        }
    ]


@pytest.fixture
def mock_broadcast_function():
    """Provide mock broadcast function for WebSocket events"""
    async def mock_broadcast(event_type: str, data: dict):
        # Mock implementation - just logs
        return {"event": event_type, "data": data}
    return mock_broadcast


@pytest.fixture
def sample_proof_submission():
    """Provide sample proof submission data for testing"""
    return {
        "proof_text": "These transactions were for purchasing equipment for my business. I have invoices and receipts available.",
        "proof_type": "EXPLANATION",
        "customer_email": "test@example.com"
    }


@pytest.fixture
def sample_proof_evaluation():
    """Provide sample proof evaluation response for testing"""
    return {
        "alert_id": "TEST-001",
        "decision": "RESOLVED",
        "status": "RESOLVED",
        "confidence": 0.85,
        "rationale": "Proof accepted - explanation aligns with transaction patterns",
        "message": "Your proof has been accepted. The alert has been resolved.",
        "timestamp": "2024-01-15T10:30:00Z"
    }


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", 
        "parametrize: mark test as parametrized for multiple scenarios"
    )


# pytest command suggestions
pytest_plugins = ['pytest_asyncio']

