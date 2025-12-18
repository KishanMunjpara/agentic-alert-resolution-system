"""
Quick Test Script for All 5 Alert Scenarios
Run this to test all scenarios via the API
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test scenarios with proper customer/account IDs from seed data
SCENARIOS = [
    {
        "name": "A-001: Velocity Spike",
        "alert_id": f"TEST-A-001-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "scenario_code": "VELOCITY_SPIKE",
        "customer_id": "CUST-101",
        "account_id": "ACC-001",
        "severity": "HIGH",
        "description": "Multiple transactions over threshold in 48 hours"
    },
    {
        "name": "A-002: Structuring",
        "alert_id": f"TEST-A-002-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "scenario_code": "STRUCTURING",
        "customer_id": "CUST-102",
        "account_id": "ACC-002",
        "severity": "HIGH",
        "description": "Multiple deposits just under $10k threshold"
    },
    {
        "name": "A-003: KYC Inconsistency",
        "alert_id": f"TEST-A-003-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "scenario_code": "KYC_INCONSISTENCY",
        "customer_id": "CUST-103",
        "account_id": "ACC-003",
        "severity": "MEDIUM",
        "description": "Transaction pattern inconsistent with declared occupation"
    },
    {
        "name": "A-004: Sanctions Hit",
        "alert_id": f"TEST-A-004-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "scenario_code": "SANCTIONS_HIT",
        "customer_id": "CUST-104",
        "account_id": "ACC-004",
        "severity": "CRITICAL",
        "description": "Transaction with entity matching sanctions list"
    },
    {
        "name": "A-005: Dormant Account Activation",
        "alert_id": f"TEST-A-005-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "scenario_code": "DORMANT_ACTIVATION",
        "customer_id": "CUST-105",
        "account_id": "ACC-005",
        "severity": "HIGH",
        "description": "Dormant account activated with large transaction"
    }
]

def test_scenario(scenario):
    """Test a single scenario"""
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {scenario['name']}")
    print(f"{'='*60}")
    
    # Step 1: Ingest alert
    print(f"📥 Step 1: Ingesting alert...")
    try:
        response = requests.post(
            f"{BASE_URL}/alerts/ingest",
            json={
                "alert_id": scenario["alert_id"],
                "scenario_code": scenario["scenario_code"],
                "customer_id": scenario["customer_id"],
                "account_id": scenario["account_id"],
                "severity": scenario["severity"],
                "description": scenario["description"]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            alert = response.json()
            print(f"   ✅ Alert created: {alert['alert_id']}")
            print(f"   📊 Status: {alert['status']}")
            print(f"   🔴 Severity: {alert['severity']}")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Step 2: Trigger investigation
    print(f"\n🔍 Step 2: Starting investigation...")
    try:
        investigate_response = requests.post(
            f"{BASE_URL}/alerts/{scenario['alert_id']}/investigate",
            json={"force": False},
            timeout=10
        )
        
        if investigate_response.status_code == 200:
            inv_result = investigate_response.json()
            print(f"   ✅ Investigation started")
            print(f"   📅 Started at: {inv_result.get('investigation_started_at', 'N/A')}")
        else:
            print(f"   ⚠️  Investigation response: {investigate_response.status_code}")
            print(f"   Response: {investigate_response.text}")
    except Exception as e:
        print(f"   ⚠️  Investigation error: {e}")
    
    # Step 3: Wait for investigation to complete
    print(f"\n⏳ Step 3: Waiting for investigation to complete (15 seconds)...")
    time.sleep(15)
    
    # Step 4: Get resolution
    print(f"\n📋 Step 4: Checking resolution...")
    try:
        resolution_response = requests.get(
            f"{BASE_URL}/resolutions/{scenario['alert_id']}",
            timeout=10
        )
        
        if resolution_response.status_code == 200:
            resolution = resolution_response.json()
            print(f"   ✅ Resolution received:")
            print(f"   💡 Recommendation: {resolution['recommendation']}")
            print(f"   📊 Confidence: {resolution['confidence']}")
            print(f"   📝 Rationale: {resolution['rationale'][:100]}...")
            return True
        elif resolution_response.status_code == 404:
            print(f"   ⏳ Resolution not yet available (investigation may still be running)")
            print(f"   💡 Try checking again in a few seconds")
            return False
        else:
            print(f"   ⚠️  Status: {resolution_response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠️  Error getting resolution: {e}")
        return False

def main():
    """Run all scenario tests"""
    print("\n" + "="*60)
    print("🚀 AGENTIC ALERT RESOLUTION SYSTEM - SCENARIO TESTING")
    print("="*60)
    print(f"\n📍 Backend URL: {BASE_URL}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if backend is running
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Backend is running and healthy\n")
        else:
            print("⚠️  Backend responded but health check failed\n")
    except Exception as e:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        print(f"   Error: {e}")
        print(f"\n💡 Make sure the backend is running: python app.py")
        return
    
    results = []
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n\n[{i}/{len(SCENARIOS)}]")
        success = test_scenario(scenario)
        results.append({
            "scenario": scenario["name"],
            "success": success
        })
        
        # Small delay between tests
        if i < len(SCENARIOS):
            time.sleep(2)
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED/INCOMPLETE"
        print(f"   {status}: {result['scenario']}")
    
    print(f"\n📈 Results: {passed}/{len(results)} passed, {failed} failed/incomplete")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

