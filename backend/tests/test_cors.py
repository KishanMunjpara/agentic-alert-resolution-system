"""
CORS OPTIONS Request Test
Tests the OPTIONS preflight request for /alerts/ingest endpoint
"""

import pytest
import httpx
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))


@pytest.fixture(scope="module")
def server_url():
    """Get server URL - test against actual server"""
    return "http://localhost:8000"


@pytest.fixture(scope="module")
def check_server_running(server_url):
    """Check if server is running"""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{server_url}/health")
            if response.status_code == 200:
                return True
    except Exception:
        pass
    pytest.skip("Server not running - start server with 'python app.py' to run CORS tests")


@pytest.mark.parametrize("origin", [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
])
def test_options_request_cors_headers(server_url, check_server_running, origin):
    """Test OPTIONS request returns correct CORS headers"""
    with httpx.Client(timeout=5.0) as client:
        response = client.options(
            f"{server_url}/alerts/ingest",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
    
    print(f"\n=== OPTIONS Request Test ===")
    print(f"Origin: {origin}")
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print(f"Response Body: {response.text}")
    print(f"===========================\n")
    
    # Should return 200 OK
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    # Check CORS headers
    assert "access-control-allow-origin" in response.headers, "Missing access-control-allow-origin header"
    assert "access-control-allow-methods" in response.headers, "Missing access-control-allow-methods header"
    assert "access-control-allow-headers" in response.headers, "Missing access-control-allow-headers header"
    
    # Verify origin is allowed
    allowed_origin = response.headers.get("access-control-allow-origin")
    assert allowed_origin == origin or allowed_origin == "*", f"Origin mismatch: {allowed_origin} != {origin}"
    
    # Verify methods include POST
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allowed_methods, f"POST not in allowed methods: {allowed_methods}"


def test_options_request_without_origin(server_url, check_server_running):
    """Test OPTIONS request without origin header"""
    with httpx.Client(timeout=5.0) as client:
        response = client.options(f"{server_url}/alerts/ingest")
    
    print(f"\n=== OPTIONS Request (No Origin) ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print(f"Response Body: {response.text}")
    print(f"===================================\n")
    
    # Should still return 200 (OPTIONS handler should work)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"


def test_debug_cors_config():
    """Check what CORS configuration the server is using"""
    import httpx
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:8000/debug/cors")
            
            print(f"\n=== Server CORS Configuration ===")
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                import json
                config_data = response.json()
                print(f"CORS Origins: {config_data.get('cors_origins')}")
                print(f"CORS Origins Type: {config_data.get('cors_origins_type')}")
                print(f"CORS Origins Length: {config_data.get('cors_origins_length')}")
                print(f"CORS Origins Env: {config_data.get('cors_origins_env')}")
                print(f"CORS Origins List: {config_data.get('cors_origins_list')}")
            else:
                print(f"Response: {response.text}")
            print(f"==================================\n")
            
    except httpx.ConnectError:
        pytest.skip("Server not running at http://localhost:8000")


def test_options_request_actual_server():
    """Test OPTIONS request against actual running server"""
    import httpx
    
    try:
        with httpx.Client(timeout=5.0) as client:
            # First check the CORS config
            debug_response = client.get("http://localhost:8000/debug/cors")
            if debug_response.status_code == 200:
                config_data = debug_response.json()
                print(f"\nServer CORS Origins: {config_data.get('cors_origins_list')}")
            
            response = client.options(
                "http://localhost:8000/alerts/ingest",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type"
                }
            )
            
            print(f"\n=== Actual Server OPTIONS Request ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            print(f"Response Body: {response.text}")
            print(f"=====================================\n")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
            
    except httpx.ConnectError:
        pytest.skip("Server not running at http://localhost:8000")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])

