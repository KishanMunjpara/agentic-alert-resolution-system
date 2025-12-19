"""
Agentic Alert Resolution System - FastAPI Application
Main application entry point with all endpoints
"""

import logging
import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid

from config import config
from schemas.schemas import (
    UserRegisterRequest, UserRegisterResponse,
    UserLoginRequest, UserLoginResponse,
    AlertCreateRequest, AlertResponse, AlertListResponse,
    AlertInvestigateRequest, AlertInvestigateResponse,
    ResolutionResponse, DashboardMetricsResponse,
    ErrorResponse, TokenRefreshRequest, TokenRefreshResponse,
    ProofSubmissionRequest, ProofEvaluationResponse,
    EvaluationReportResponse
)
from auth.auth_service import AuthService
from auth.jwt_handler import JWTHandler
from database.neo4j_connector import Neo4jConnector
from agents.orchestrator import OrchestratorAgent
from websocket.manager import get_connection_manager

logger = logging.getLogger(__name__)


# ============================================================================
# SEED DATA INITIALIZATION
# ============================================================================

def ensure_seed_data_exists():
    """
    Check if seed data exists and create it if missing
    Runs automatically on startup (can be disabled via AUTO_CREATE_SEED_DATA=false)
    """
    # Check if auto-creation is disabled
    auto_create = os.getenv("AUTO_CREATE_SEED_DATA", "true").lower() == "true"
    if not auto_create:
        logger.info("⏭️  Auto seed data creation is disabled (AUTO_CREATE_SEED_DATA=false)")
        return
    
    try:
        db = Neo4jConnector()
        
        # Check if customers exist
        result = db.execute_query("MATCH (c:Customer) RETURN COUNT(c) as count", {})
        customer_count = result[0]["count"] if result else 0
        
        # Check if SOPs exist
        result = db.execute_query("MATCH (s:SOP) RETURN COUNT(s) as count", {})
        sop_count = result[0]["count"] if result else 0
        
        # If we have less than expected data, create seed data
        if customer_count < 5 or sop_count < 10:
            logger.info("📦 Seed data missing or incomplete. Creating seed data...")
            
            # Import and run seed data creation
            try:
                from create_seed_data import create_seed_data
                if create_seed_data():
                    logger.info("✓ Seed data created successfully")
                else:
                    logger.warning("⚠ Seed data creation had issues - check logs above")
            except ImportError as e:
                logger.warning(f"⚠ Could not import seed data creator: {e}")
                logger.warning("⚠ Run 'python create_seed_data.py' manually to create seed data")
        else:
            logger.info(f"✓ Seed data verified ({customer_count} customers, {sop_count} SOPs)")
    
    except Exception as e:
        logger.warning(f"⚠ Could not verify/create seed data: {e}")
        logger.warning("⚠ App will continue - you may need to run 'python create_seed_data.py' manually")


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("🚀 Agentic Alert Resolution System starting...")
    logger.info(f"📊 Database: {config.NEO4J_URI}")
    logger.info(f"👤 Database User: {config.NEO4J_USER}")
    logger.info(f"🔒 JWT Algorithm: {config.JWT_ALGORITHM}")
    
    # Test database connection (non-blocking)
    db = None
    try:
        db = Neo4jConnector()
        if db.test_connection():
            logger.info("✓ Database connection successful")
            
            # Ensure seed data exists
            ensure_seed_data_exists()
        else:
            logger.warning("⚠ Database connection test failed - app will continue but database operations may fail")
    except Exception as e:
        logger.warning(f"⚠ Database connection error during startup: {e}")
        logger.warning("⚠ App will continue - ensure Neo4j is running and credentials are correct")
    
    try:
        yield
    except asyncio.CancelledError:
        # Normal during uvicorn reload - just log and re-raise
        logger.debug("Lifespan cancelled (likely due to file reload)")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down...")
        if db:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Agentic Alert Resolution System",
    description="Multi-agent banking transaction monitoring alert resolution system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable Swagger UI
    redoc_url=None  # Disable ReDoc
)

# CORS Configuration
# For development: Allow all origins
# In production, use specific origins from config.CORS_ORIGINS
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"

# Custom middleware to allow all origins (for development)
class AllowAllCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Handle OPTIONS preflight requests
        if request.method == "OPTIONS":
            origin = request.headers.get("origin", "*")
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = request.headers.get("access-control-request-headers", "*")
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "600"
            return response
        
        # Handle actual requests - add CORS headers to response
        response = await call_next(request)
        origin = request.headers.get("origin", "*")
        
        # Add CORS headers - response should already be a Response object from FastAPI
        if hasattr(response, "headers"):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response

if CORS_ALLOW_ALL:
    logger.info("🌐 CORS: Allowing ALL origins (development mode)")
    # Use ONLY custom middleware - no CORSMiddleware to avoid conflicts
    app.add_middleware(AllowAllCORSMiddleware)
else:
    # Production mode: Use specific origins
    logger.info(f"🌐 CORS Origins: {config.CORS_ORIGINS}")
    logger.info(f"🌐 CORS Origins Type: {type(config.CORS_ORIGINS)}")
    logger.info(f"🌐 CORS Origins Length: {len(config.CORS_ORIGINS) if config.CORS_ORIGINS else 0}")
    
    # Debug: Print each origin
    for i, origin in enumerate(config.CORS_ORIGINS):
        logger.info(f"🌐 CORS Origin[{i}]: '{origin}' (type: {type(origin)})")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )

# Services
auth_service = AuthService()
jwt_handler = JWTHandler()
db = Neo4jConnector()
connection_manager = get_connection_manager()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_user(token: str = None):
    """Dependency to get current user from JWT token"""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = jwt_handler.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "aars",
        "ws_connections": connection_manager.get_connection_count()
    }


@app.get("/debug/cors")
async def debug_cors():
    """Debug endpoint to check CORS configuration"""
    import os
    return {
        "cors_origins": config.CORS_ORIGINS,
        "cors_origins_type": str(type(config.CORS_ORIGINS)),
        "cors_origins_length": len(config.CORS_ORIGINS) if config.CORS_ORIGINS else 0,
        "cors_origins_env": os.getenv("CORS_ORIGINS", "NOT_SET"),
        "cors_origins_list": list(config.CORS_ORIGINS) if config.CORS_ORIGINS else []
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=UserRegisterResponse)
async def register(request: UserRegisterRequest):
    """Register new user"""
    logger.info(f"Registration request: {request.username}")
    
    result = await auth_service.register_user(
        request.username,
        request.email,
        request.password
    )
    
    return UserRegisterResponse(**result)


@app.post("/auth/login", response_model=UserLoginResponse)
async def login(request: UserLoginRequest):
    """Login user and get tokens"""
    logger.info(f"Login request: {request.username}")
    
    result = await auth_service.login_user(
        request.username,
        request.password
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error"))
    
    return UserLoginResponse(**result)


@app.post("/auth/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest):
    """Refresh access token"""
    logger.info("Token refresh request")
    
    result = await auth_service.refresh_access_token(request.refresh_token)
    
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error"))
    
    return TokenRefreshResponse(**result)


# ============================================================================
# ALERT ENDPOINTS
# ============================================================================

@app.options("/alerts/ingest")
async def options_ingest_alert():
    """Handle OPTIONS preflight requests for alert ingestion"""
    return Response(status_code=200)

def _create_scenario_test_data(alert_id: str, scenario_code: str, account_id: str, customer_id: str, timestamp: str) -> None:
    """
    Create test transaction and customer data based on scenario
    This ensures the investigator can find relevant data for testing
    """
    from datetime import datetime, timedelta
    import json
    
    # Parse timestamp
    alert_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    if scenario_code == "VELOCITY_SPIKE":
        # Create 6 transactions totaling $33,400 in last 48 hours
        transactions = []
        amounts = [6000, 5500, 6200, 5800, 5100, 4800]  # Total: 33,400
        for i, amount in enumerate(amounts):
            txn_time = alert_time - timedelta(hours=40 - (i * 6))
            transactions.append({
                "txn_id": f"TXN-{alert_id}-{i+1}",
                "amount": float(amount),
                "transaction_type": "OUTBOUND",
                "timestamp": txn_time.isoformat(),
                "counterparty": f"Entity-{i+1}",
                "description": "Transfer"
            })
        
        # Create transactions
        for txn in transactions:
            query = """
            MATCH (acc:Account {account_id: $account_id})
            MERGE (t:Transaction {txn_id: $txn_id})
            SET t.amount = $amount,
                t.transaction_type = $transaction_type,
                t.timestamp = datetime($timestamp),
                t.counterparty = $counterparty,
                t.description = $description
            MERGE (acc)-[:HAS_TRANSACTION]->(t)
            """
            # Add account_id to transaction parameters
            txn_params = {**txn, "account_id": account_id, "timestamp": txn["timestamp"]}
            db.execute_write(query, txn_params)
        
        # Set customer KYC risk to HIGH
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        SET c.kyc_risk = 'HIGH',
            c.occupation = 'Teacher',
            c.declared_income = 50000.0,
            c.profile_age_days = 365
        """
        db.execute_write(query, {"customer_id": customer_id})
        
    elif scenario_code == "STRUCTURING":
        # Create 3 deposits just under $10k each
        transactions = []
        amounts = [9500, 9800, 9700]  # All under 10k
        for i, amount in enumerate(amounts):
            txn_time = alert_time - timedelta(days=2 - i)
            transactions.append({
                "txn_id": f"TXN-{alert_id}-{i+1}",
                "amount": float(amount),
                "transaction_type": "INBOUND",
                "timestamp": txn_time.isoformat(),
                "counterparty": f"Source-{i+1}",
                "description": "Deposit"
            })
        
        for txn in transactions:
            query = """
            MATCH (acc:Account {account_id: $account_id})
            MERGE (t:Transaction {txn_id: $txn_id})
            SET t.amount = $amount,
                t.transaction_type = $transaction_type,
                t.timestamp = datetime($timestamp),
                t.counterparty = $counterparty,
                t.description = $description
            MERGE (acc)-[:HAS_TRANSACTION]->(t)
            """
            # Add account_id to transaction parameters
            txn_params = {**txn, "account_id": account_id}
            db.execute_write(query, txn_params)
        
        # Set customer KYC risk to MEDIUM
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        SET c.kyc_risk = 'MEDIUM',
            c.occupation = 'Engineer',
            c.declared_income = 100000.0,
            c.profile_age_days = 730
        """
        db.execute_write(query, {"customer_id": customer_id})
        
    elif scenario_code == "KYC_INCONSISTENCY":
        # Create transaction with precious metals MCC
        query = """
        MATCH (acc:Account {account_id: $account_id})
        MERGE (t:Transaction {txn_id: $txn_id})
        SET t.amount = 15000.0,
            t.transaction_type = 'OUTBOUND',
            t.timestamp = datetime($timestamp),
            t.counterparty = 'Precious Metals Dealer',
            t.counterparty_mcc = 'PRECIOUS_METALS',
            t.description = 'Precious metals purchase'
        MERGE (acc)-[:HAS_TRANSACTION]->(t)
        """
        db.execute_write(query, {
            "account_id": account_id,
            "txn_id": f"TXN-{alert_id}-1",
            "timestamp": (alert_time - timedelta(days=1)).isoformat()
        })
        
        # Set customer occupation to Jeweler (consistent with precious metals - should CLOSE)
        # This matches SOP-A003-01 which should result in CLOSE decision
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        SET c.kyc_risk = 'MEDIUM',
            c.occupation = 'Jeweler',
            c.declared_income = 75000.0,
            c.profile_age_days = 365
        """
        db.execute_write(query, {"customer_id": customer_id})
        
    elif scenario_code == "SANCTIONS_HIT":
        # Create transaction with sanctions entity
        query = """
        MATCH (acc:Account {account_id: $account_id})
        MERGE (t:Transaction {txn_id: $txn_id})
        SET t.amount = 50000.0,
            t.transaction_type = 'OUTBOUND',
            t.timestamp = datetime($timestamp),
            t.counterparty = 'Sanctioned Entity XYZ',
            t.description = 'Transfer to sanctioned entity'
        MERGE (acc)-[:HAS_TRANSACTION]->(t)
        
        WITH t
        MERGE (se:SanctionsEntity {entity_id: 'SANCT-001'})
        SET se.entity_name = 'Sanctioned Entity XYZ',
            se.entity_type = 'ORGANIZATION',
            se.jurisdiction = 'IR',
            se.list_type = 'OFAC',
            se.risk_level = 'HIGH'
        MERGE (t)-[:TO_SANCTIONED_ENTITY {match_score: 0.95}]->(se)
        """
        db.execute_write(query, {
            "account_id": account_id,
            "txn_id": f"TXN-{alert_id}-1",
            "timestamp": (alert_time - timedelta(hours=12)).isoformat()
        })
        
        # Set customer data
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        SET c.kyc_risk = 'HIGH',
            c.occupation = 'Business Owner',
            c.declared_income = 200000.0,
            c.profile_age_days = 180
        """
        db.execute_write(query, {"customer_id": customer_id})
        
    elif scenario_code == "DORMANT_ACTIVATION":
        # Set account as dormant (365+ days)
        query = """
        MATCH (acc:Account {account_id: $account_id})
        SET acc.dormant_days = 400,
            acc.last_activity_date = datetime($last_activity)
        """
        db.execute_write(query, {
            "account_id": account_id,
            "last_activity": (alert_time - timedelta(days=400)).isoformat()
        })
        
        # Create recent large transaction
        query = """
        MATCH (acc:Account {account_id: $account_id})
        MERGE (t:Transaction {txn_id: $txn_id})
        SET t.amount = 25000.0,
            t.transaction_type = 'INBOUND',
            t.timestamp = datetime($timestamp),
            t.counterparty = 'Unknown Source',
            t.description = 'Large deposit after dormancy'
        MERGE (acc)-[:HAS_TRANSACTION]->(t)
        """
        db.execute_write(query, {
            "account_id": account_id,
            "txn_id": f"TXN-{alert_id}-1",
            "timestamp": (alert_time - timedelta(hours=6)).isoformat()
        })
        
        # Set customer data
        query = """
        MATCH (c:Customer {customer_id: $customer_id})
        SET c.kyc_risk = 'MEDIUM',
            c.occupation = 'Retired',
            c.declared_income = 60000.0,
            c.profile_age_days = 1200
        """
        db.execute_write(query, {"customer_id": customer_id})


@app.post("/alerts/ingest", response_model=AlertResponse)
async def ingest_alert(request: AlertCreateRequest):
    """
    Ingest a new alert
    Immediately starts investigation
    Creates test transaction data based on scenario
    """
    logger.info(f"📥 Alert ingested: {request.alert_id} ({request.scenario_code})")
    
    timestamp = datetime.now().isoformat()
    
    # Create alert in Neo4j with relationships to Customer and Account
    query = """
    // Create or match Customer
    MERGE (c:Customer {customer_id: $customer_id})
    ON CREATE SET c.created_at = $timestamp
    
    // Create or match Account
    MERGE (acc:Account {account_id: $account_id})
    ON CREATE SET acc.created_at = $timestamp
    
    // Create Alert
    CREATE (a:Alert {
        alert_id: $alert_id,
        scenario_code: $scenario_code,
        customer_id: $customer_id,
        account_id: $account_id,
        status: 'OPEN',
        severity: $severity,
        description: $description,
        risk_score: 0,
        created_at: $timestamp
    })
    
    // Create relationships
    CREATE (a)-[:INVESTIGATES_CUSTOMER]->(c)
    CREATE (a)-[:INVESTIGATES_ACCOUNT]->(acc)
    
    // Also link Customer to Account if not already linked
    MERGE (c)-[:OWNS]->(acc)
    
    RETURN a
    """
    
    params = {
        "alert_id": request.alert_id,
        "scenario_code": request.scenario_code,
        "customer_id": request.customer_id,
        "account_id": request.account_id,
        "severity": request.severity,
        "description": request.description,
        "timestamp": timestamp
    }
    
    try:
        db.execute_write(query, params)
        
        # Create scenario-specific test data (transactions, customer KYC data, etc.)
        try:
            _create_scenario_test_data(
                request.alert_id,
                request.scenario_code,
                request.account_id,
                request.customer_id,
                timestamp
            )
            logger.info(f"✓ Created test data for scenario {request.scenario_code}")
        except Exception as e:
            logger.warning(f"Failed to create test data: {e}")
            # Don't fail alert ingestion if test data creation fails
        
        # Broadcast alert created event
        await connection_manager.broadcast("alert_created", {
            "alert_id": request.alert_id,
            "scenario_code": request.scenario_code,
            "status": "OPEN"
        })
        
        return AlertResponse(
            alert_id=request.alert_id,
            scenario_code=request.scenario_code,
            customer_id=request.customer_id,
            account_id=request.account_id,
            status="OPEN",
            severity=request.severity,
            created_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"Failed to ingest alert: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/alerts/list", response_model=AlertListResponse)
async def list_alerts(
    status: str = None,
    scenario: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all alerts with optional filtering
    """
    logger.info(f"List alerts: status={status}, scenario={scenario}")
    
    query = "MATCH (a:Alert) WHERE 1=1"
    params = {}
    
    if status:
        query += " AND a.status = $status"
        params["status"] = status
    
    if scenario:
        query += " AND a.scenario_code = $scenario"
        params["scenario"] = scenario
    
    query += f" RETURN a ORDER BY a.created_at DESC SKIP $offset LIMIT $limit"
    params["offset"] = offset
    params["limit"] = limit
    
    try:
        results = db.execute_query(query, params)
        alerts = [AlertResponse(**dict(r["a"])) for r in results]
        
        # Get total count
        count_query = "MATCH (a:Alert) RETURN COUNT(a) as total"
        count_result = db.execute_query(count_query)
        total = count_result[0]["total"] if count_result else len(alerts)
        
        return AlertListResponse(total=total, alerts=alerts)
    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get alert details"""
    logger.info(f"Get alert: {alert_id}")
    
    query = "MATCH (a:Alert {alert_id: $alert_id}) RETURN a"
    
    try:
        results = db.execute_query(query, {"alert_id": alert_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = dict(results[0]["a"])
        return AlertResponse(**alert_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/alerts/{alert_id}/investigate", response_model=AlertInvestigateResponse)
async def investigate_alert(
    alert_id: str,
    request: AlertInvestigateRequest
):
    """
    Start investigation for an alert
    Triggers multi-agent system
    Skips investigation if resolution already exists (unless force=True)
    """
    logger.info(f"🔍 Starting investigation: {alert_id}")
    
    # Check if resolution already exists
    check_query = """
    MATCH (a:Alert {alert_id: $alert_id})-[:HAS_RESOLUTION]->(r:Resolution)
    RETURN r.resolution_id as resolution_id, r.recommendation as recommendation, r.created_at as created_at
    ORDER BY r.created_at DESC
    LIMIT 1
    """
    
    existing_resolution = db.execute_query(check_query, {"alert_id": alert_id})
    
    if existing_resolution and not request.force:
        resolution_data = existing_resolution[0]
        logger.info(f"✓ Resolution already exists for alert {alert_id}: {resolution_data.get('recommendation')}")
        return AlertInvestigateResponse(
            alert_id=alert_id,
            status="ALREADY_RESOLVED",
            investigation_started_at=datetime.now(),
            message=f"Investigation already completed. Resolution: {resolution_data.get('recommendation')}"
        )
    
    # Update alert status
    update_query = """
    MATCH (a:Alert {alert_id: $alert_id})
    SET a.status = 'INVESTIGATING',
        a.started_investigating_at = $timestamp
    RETURN a
    """
    
    try:
        db.execute_write(update_query, {
            "alert_id": alert_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Create orchestrator and start investigation
        orchestrator = OrchestratorAgent(broadcast_fn=connection_manager.broadcast)
        await orchestrator.initialize_spokes(connection_manager.broadcast)
        
        # Get alert details for scenario
        query = "MATCH (a:Alert {alert_id: $alert_id}) RETURN a.scenario_code as scenario"
        results = db.execute_query(query, {"alert_id": alert_id})
        scenario = results[0]["scenario"] if results else "UNKNOWN"
        
        # Start investigation (async, non-blocking)
        import asyncio
        asyncio.create_task(orchestrator.execute(alert_id, scenario, force=request.force))
        
        return AlertInvestigateResponse(
            alert_id=alert_id,
            status="INVESTIGATING",
            investigation_started_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"Failed to investigate alert: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# PROOF SUBMISSION ENDPOINTS
# ============================================================================

@app.post("/alerts/{alert_id}/submit-proof", response_model=ProofEvaluationResponse)
async def submit_proof(
    alert_id: str,
    request: ProofSubmissionRequest
):
    """
    Submit proof/explanation for an alert
    Agentic system evaluates and updates alert status
    """
    logger.info(f"📝 Proof submission received for alert {alert_id}")
    
    try:
        # Get alert and resolution details
        alert_query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:HAS_RESOLUTION]->(r:Resolution)
        RETURN a, r
        """
        
        results = db.execute_query(alert_query, {"alert_id": alert_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = dict(results[0]["a"])
        resolution_data = dict(results[0].get("r", {}))
        
        # Check if alert is in correct status
        if alert_data.get("status") not in ["INVESTIGATING", "AWAITING_PROOF"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Alert is in {alert_data.get('status')} status. Proof can only be submitted for alerts under investigation."
            )
        
        # Parse findings and context from resolution
        import json
        import ast
        
        findings = {}
        context = {}
        
        if resolution_data:
            findings_str = resolution_data.get("investigator_findings")
            if findings_str:
                try:
                    findings = json.loads(findings_str)
                except (json.JSONDecodeError, TypeError):
                    try:
                        findings = ast.literal_eval(findings_str)
                    except:
                        findings = {}
            
            context_str = resolution_data.get("context_data")
            if context_str:
                try:
                    context = json.loads(context_str)
                except (json.JSONDecodeError, TypeError):
                    try:
                        context = ast.literal_eval(context_str)
                    except:
                        context = {}
        
        # Create proof evaluator
        from agents.proof_evaluator import ProofEvaluatorAgent
        proof_evaluator = ProofEvaluatorAgent(broadcast_fn=connection_manager.broadcast)
        
        # Evaluate proof
        evaluation = await proof_evaluator.evaluate_proof(
            alert_id=alert_id,
            proof_text=request.proof_text,
            proof_type=request.proof_type,
            original_resolution={
                "recommendation": resolution_data.get("recommendation", "RFI"),
                "rationale": resolution_data.get("rationale", ""),
                "confidence": resolution_data.get("confidence_score", 0.5)
            },
            findings=findings,
            context=context
        )
        
        # Send follow-up email based on decision
        await _send_proof_evaluation_email(alert_id, evaluation, request.customer_email)
        
        # Prepare response message
        if evaluation["decision"] == "RESOLVED":
            message = "Your proof has been accepted. The alert has been resolved. Thank you for your cooperation."
        else:
            message = "Your proof requires further verification. Please visit your nearest branch or contact customer care for assistance."
        
        return ProofEvaluationResponse(
            alert_id=alert_id,
            decision=evaluation["decision"],
            status=evaluation["status"],
            confidence=evaluation["confidence"],
            rationale=evaluation["rationale"],
            message=message,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process proof submission: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


async def _send_proof_evaluation_email(alert_id: str, evaluation: Dict, customer_email: Optional[str] = None):
    """Send follow-up email based on proof evaluation"""
    try:
        from services.email_service import get_email_service
        from database.neo4j_connector import Neo4jConnector
        
        db_instance = Neo4jConnector()
        
        # Get customer email if not provided
        if not customer_email:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})-[:INVESTIGATES_CUSTOMER]->(c:Customer)
            RETURN c.email as email, c.customer_id as customer_id, 
                   c.first_name as first_name, c.last_name as last_name
            """
            results = db_instance.execute_query(query, {"alert_id": alert_id})
            if results:
                customer_email = results[0].get("email")
                customer = {
                    "id": results[0].get("customer_id"),
                    "email": customer_email,
                    "first_name": results[0].get("first_name", ""),
                    "last_name": results[0].get("last_name", ""),
                    "name": f"{results[0].get('first_name', '')} {results[0].get('last_name', '')}".strip()
                }
            else:
                logger.warning(f"Could not find customer for alert {alert_id}")
                return
        else:
            customer = {"email": customer_email, "name": "Customer"}
        
        email_service = get_email_service()
        
        if evaluation["decision"] == "RESOLVED":
            # Send resolution confirmation email
            await email_service.send_resolution_email(customer, alert_id, evaluation)
        else:
            # Send branch escalation email
            await email_service.send_branch_escalation_email(customer, alert_id, evaluation)
            
    except Exception as e:
        logger.error(f"Failed to send proof evaluation email: {e}")


# ============================================================================
# EMAIL TEST ENDPOINT
# ============================================================================

@app.post("/test/email")
async def test_email(email: Optional[str] = None):
    """
    Test email configuration and send a test email
    """
    logger.info("🧪 Testing email configuration...")
    
    try:
        from services.email_service import get_email_service
        import os
        
        email_service = get_email_service()
        
        # Use provided email or default test email
        test_email = email or os.getenv("SMTP_USER", "test@example.com")
        
        # Check configuration
        config_status = {
            "smtp_host": email_service.smtp_host,
            "smtp_port": email_service.smtp_port,
            "smtp_user": email_service.smtp_user,
            "from_email": email_service.from_email,
            "has_password": "✓" if email_service.smtp_password else "✗",
            "test_email": test_email
        }
        
        # Try to send test email
        test_customer = {
            "id": "TEST",
            "email": test_email,
            "first_name": "Test",
            "last_name": "User"
        }
        
        test_resolution = {
            "recommendation": "RFI",
            "rationale": "This is a test email",
            "confidence": 0.5,
            "findings": {},
            "context": {}
        }
        
        result = await email_service.send_rfi_email(
            test_customer,
            "TEST-ALERT-001",
            test_resolution
        )
        
        return {
            "success": result.get("success", False),
            "config": config_status,
            "result": result,
            "message": "Test email sent successfully" if result.get("success") else f"Test email failed: {result.get('reason', result.get('error', 'Unknown error'))}"
        }
        
    except Exception as e:
        logger.error(f"Email test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Email test failed. Check SMTP configuration."
        }


# ============================================================================
# RESOLUTION ENDPOINTS
# ============================================================================

@app.get("/resolutions/{alert_id}", response_model=ResolutionResponse)
async def get_resolution(alert_id: str):
    """Get resolution for an alert"""
    logger.info(f"Get resolution: {alert_id}")
    
    query = """
    MATCH (a:Alert {alert_id: $alert_id})-[:HAS_RESOLUTION]->(r:Resolution)
    RETURN r
    """
    
    try:
        results = db.execute_query(query, {"alert_id": alert_id})
        
        if not results:
            logger.warning(f"Resolution not found for alert {alert_id}")
            raise HTTPException(status_code=404, detail="Resolution not found. Investigation may still be in progress.")
        
        resolution_data = dict(results[0]["r"])
        
        # Parse findings and context - they might be stored as JSON strings or Python dict strings
        import json
        import ast
        
        # Handle findings
        findings_str = resolution_data.get("investigator_findings")
        if findings_str:
            try:
                # Try JSON first
                resolution_data["findings"] = json.loads(findings_str)
            except (json.JSONDecodeError, TypeError):
                try:
                    # Try Python dict string (ast.literal_eval)
                    resolution_data["findings"] = ast.literal_eval(findings_str)
                except (ValueError, SyntaxError):
                    logger.warning(f"Failed to parse findings: {findings_str}")
                    resolution_data["findings"] = {}
        else:
            resolution_data["findings"] = {}
        
        # Handle context
        context_str = resolution_data.get("context_data")
        if context_str:
            try:
                # Try JSON first
                resolution_data["context"] = json.loads(context_str)
            except (json.JSONDecodeError, TypeError):
                try:
                    # Try Python dict string (ast.literal_eval)
                    resolution_data["context"] = ast.literal_eval(context_str)
                except (ValueError, SyntaxError):
                    logger.warning(f"Failed to parse context: {context_str}")
                    resolution_data["context"] = {}
        else:
            resolution_data["context"] = {}
        
        # Map Neo4j field names to schema field names
        # Neo4j uses snake_case, schema might use different names
        created_at_str = resolution_data.get("created_at")
        if isinstance(created_at_str, str):
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.now()
        else:
            created_at = datetime.now()
        
        mapped_data = {
            "resolution_id": resolution_data.get("resolution_id", ""),
            "alert_id": alert_id,
            "recommendation": resolution_data.get("recommendation", "PENDING"),
            "rationale": resolution_data.get("rationale", "Investigation in progress"),
            "confidence": float(resolution_data.get("confidence_score", resolution_data.get("confidence", 0.0))),
            "created_at": created_at,
            "findings": resolution_data.get("findings", {}),
            "context": resolution_data.get("context", {})
        }
        
        logger.debug(f"Resolution mapped data: {mapped_data}")
        
        try:
            return ResolutionResponse(**mapped_data)
        except Exception as e:
            logger.error(f"Failed to create ResolutionResponse: {e}", exc_info=True)
            logger.error(f"Resolution data keys: {list(resolution_data.keys())}")
            logger.error(f"Mapped data: {mapped_data}")
            raise HTTPException(status_code=500, detail=f"Failed to format resolution: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resolution: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to get resolution: {str(e)}")


# ============================================================================
# EVALUATION REPORT ENDPOINTS
# ============================================================================

@app.get("/alerts/{alert_id}/evaluation-report", response_model=EvaluationReportResponse)
async def get_evaluation_report(alert_id: str):
    """
    Get or generate evaluation report for an alert
    Report is generated on-demand from resolution data
    """
    logger.info(f"📄 Getting evaluation report for alert {alert_id}")
    
    try:
        # Get alert and resolution
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:HAS_RESOLUTION]->(r:Resolution)
        OPTIONAL MATCH (a)-[:INVESTIGATES_CUSTOMER]->(c:Customer)
        RETURN a, r, c
        """
        
        results = db.execute_query(query, {"alert_id": alert_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = dict(results[0]["a"])
        resolution_data = dict(results[0].get("r", {}))
        customer_data = dict(results[0].get("c", {}))
        
        if not resolution_data:
            raise HTTPException(
                status_code=404, 
                detail="Resolution not found. Investigation may still be in progress."
            )
        
        # Parse findings and context
        import json
        import ast
        
        findings = {}
        context = {}
        
        findings_str = resolution_data.get("investigator_findings")
        if findings_str:
            try:
                findings = json.loads(findings_str)
            except (json.JSONDecodeError, TypeError):
                try:
                    findings = ast.literal_eval(findings_str)
                except:
                    findings = {}
        
        context_str = resolution_data.get("context_data")
        if context_str:
            try:
                context = json.loads(context_str)
            except (json.JSONDecodeError, TypeError):
                try:
                    context = ast.literal_eval(context_str)
                except:
                    context = {}
        
        # Prepare customer info
        customer = {
            "id": customer_data.get("customer_id", "UNKNOWN"),
            "email": customer_data.get("email", ""),
            "first_name": customer_data.get("first_name", ""),
            "last_name": customer_data.get("last_name", ""),
            "name": f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip() or "Customer"
        }
        
        # Prepare resolution
        resolution = {
            "recommendation": resolution_data.get("recommendation", "RFI"),
            "rationale": resolution_data.get("rationale", ""),
            "confidence": float(resolution_data.get("confidence_score", resolution_data.get("confidence", 0.5))),
            "findings": findings,
            "context": context
        }
        
        # Get or generate report (checks database first)
        from services.report_generator import get_report_generator
        report_generator = get_report_generator()
        
        report_result = await report_generator.generate_evaluation_report(
            customer,
            alert_id,
            resolution,
            findings,
            context,
            force_regenerate=False  # Use stored report if available
        )
        
        if not report_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate report: {report_result.get('error', 'Unknown error')}"
            )
        
        # Check if customer email is available for sending
        can_send_email = bool(customer.get("email"))
        
        # Get email sent status from stored report
        stored_report = report_generator.get_stored_report(alert_id)
        # Ensure email_sent is always a boolean, never None
        email_sent = False
        email_sent_at = None
        email_sent_to = None
        
        if stored_report:
            # Get email_sent, ensuring it's a boolean
            email_sent_value = stored_report.get("email_sent")
            if email_sent_value is not None:
                email_sent = bool(email_sent_value)
            else:
                email_sent = False
            
            email_sent_at_str = stored_report.get("email_sent_at")
            if email_sent_at_str:
                try:
                    # Neo4j returns datetime as ISO string, parse it
                    if isinstance(email_sent_at_str, str):
                        # Handle different datetime formats
                        email_sent_at_str = email_sent_at_str.replace("Z", "+00:00")
                        if "." in email_sent_at_str and "+" in email_sent_at_str:
                            # Format: 2024-01-01T12:00:00.000+00:00
                            email_sent_at = datetime.fromisoformat(email_sent_at_str)
                        else:
                            # Try parsing without timezone
                            email_sent_at = datetime.fromisoformat(email_sent_at_str.split("+")[0])
                except Exception as e:
                    logger.debug(f"Could not parse email_sent_at: {e}")
            email_sent_to = stored_report.get("email_sent_to")
        
        return EvaluationReportResponse(
            alert_id=alert_id,
            report_content=report_result.get("content", ""),
            metadata=report_result.get("metadata", {}),
            next_steps=report_result.get("next_steps"),
            generated_at=datetime.now(),
            format=report_result.get("format", "text"),
            can_send_email=can_send_email,
            email_sent=email_sent,
            email_sent_at=email_sent_at,
            email_sent_to=email_sent_to
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evaluation report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get evaluation report: {str(e)}")


@app.post("/alerts/{alert_id}/send-report-email")
async def send_report_email(alert_id: str):
    """
    Send evaluation report via email to customer
    Works for any decision type (not just RFI)
    """
    logger.info(f"📧 Sending report email for alert {alert_id}")
    
    try:
        # Get alert, resolution, and customer
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        OPTIONAL MATCH (a)-[:HAS_RESOLUTION]->(r:Resolution)
        OPTIONAL MATCH (a)-[:INVESTIGATES_CUSTOMER]->(c:Customer)
        RETURN a, r, c
        """
        
        results = db.execute_query(query, {"alert_id": alert_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = dict(results[0]["a"])
        resolution_data = dict(results[0].get("r", {}))
        customer_data = dict(results[0].get("c", {}))
        
        if not resolution_data:
            raise HTTPException(
                status_code=404,
                detail="Resolution not found. Investigation may still be in progress."
            )
        
        if not customer_data.get("email"):
            raise HTTPException(
                status_code=400,
                detail="Customer email not found. Cannot send email."
            )
        
        # Parse findings and context
        import json
        import ast
        
        findings = {}
        context = {}
        
        findings_str = resolution_data.get("investigator_findings")
        if findings_str:
            try:
                findings = json.loads(findings_str)
            except (json.JSONDecodeError, TypeError):
                try:
                    findings = ast.literal_eval(findings_str)
                except:
                    findings = {}
        
        context_str = resolution_data.get("context_data")
        if context_str:
            try:
                context = json.loads(context_str)
            except (json.JSONDecodeError, TypeError):
                try:
                    context = ast.literal_eval(context_str)
                except:
                    context = {}
        
        # Prepare customer info
        customer = {
            "id": customer_data.get("customer_id", "UNKNOWN"),
            "email": customer_data.get("email", ""),
            "first_name": customer_data.get("first_name", ""),
            "last_name": customer_data.get("last_name", ""),
            "name": f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip() or "Customer"
        }
        
        # Prepare resolution
        resolution = {
            "recommendation": resolution_data.get("recommendation", "RFI"),
            "rationale": resolution_data.get("rationale", ""),
            "confidence": float(resolution_data.get("confidence_score", resolution_data.get("confidence", 0.5))),
            "findings": findings,
            "context": context
        }
        
        # Get stored report if available (or generate new one)
        from services.report_generator import get_report_generator
        report_generator = get_report_generator()
        
        # Try to get stored report first
        stored_report = report_generator.get_stored_report(alert_id)
        report_content = stored_report.get("content") if stored_report else None
        
        # If no stored report, generate one (will be stored automatically)
        if not report_content:
            report_result = await report_generator.generate_evaluation_report(
                customer,
                alert_id,
                resolution,
                findings,
                context,
                force_regenerate=False
            )
            if report_result.get("success"):
                report_content = report_result.get("content", "")
        
        # Send email with report
        from services.email_service import get_email_service
        email_service = get_email_service()
        
        email_result = await email_service.send_report_email(
            customer,
            alert_id,
            resolution,
            report_content
        )
        
        if not email_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email: {email_result.get('reason', 'Unknown error')}"
            )
        
        return {
            "success": True,
            "message": email_result.get("message", "Email sent successfully"),
            "timestamp": email_result.get("timestamp")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send report email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send report email: {str(e)}")


# ============================================================================
# TIMELINE ENDPOINTS
# ============================================================================

@app.get("/alerts/{alert_id}/timeline")
async def get_alert_timeline(alert_id: str):
    """
    Get investigation timeline events for an alert
    Returns all events stored in the database for this alert
    """
    logger.info(f"📋 Getting timeline for alert {alert_id}")
    
    query = """
    MATCH (a:Alert {alert_id: $alert_id})<-[:FOR_ALERT]-(e:Event)
    RETURN e.event_id as event_id,
           e.event_type as event_type,
           e.agent_name as agent_name,
           e.event_data as event_data,
           e.timestamp as timestamp
    ORDER BY e.timestamp ASC
    """
    
    try:
        results = db.execute_query(query, {"alert_id": alert_id})
        
        events = []
        for row in results:
            # Parse event_data (stored as string, might be JSON or Python dict string)
            event_data_str = row.get("event_data", "{}")
            event_data = {}
            
            if event_data_str:
                try:
                    import json
                    event_data = json.loads(event_data_str)
                except (json.JSONDecodeError, TypeError):
                    try:
                        import ast
                        event_data = ast.literal_eval(event_data_str)
                    except (ValueError, SyntaxError):
                        # If parsing fails, try to extract alert_id at least
                        if isinstance(event_data_str, str) and alert_id in event_data_str:
                            event_data = {"alert_id": alert_id, "raw_data": event_data_str}
                        else:
                            event_data = {"raw_data": event_data_str}
            
            events.append({
                "event_id": row.get("event_id"),
                "event": row.get("event_type", "unknown"),
                "agent_name": row.get("agent_name", "Unknown"),
                "data": event_data,
                "timestamp": row.get("timestamp")
            })
        
        return {
            "alert_id": alert_id,
            "events": events,
            "count": len(events)
        }
        
    except Exception as e:
        logger.error(f"Failed to get timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/analytics/dashboard", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics():
    """Get dashboard metrics"""
    logger.info("Get dashboard metrics")
    
    try:
        # Get all metrics
        query = """
        MATCH (a:Alert)
        RETURN 
            COUNT(a) as total,
            COUNTIF(a.status = 'OPEN') as open_count,
            COUNTIF(a.status = 'INVESTIGATING') as investigating_count,
            COUNTIF(a.status = 'RESOLVED') as resolved_count
        """
        
        results = db.execute_query(query)
        metrics = results[0] if results else {}
        
        # Get by scenario
        scenario_query = """
        MATCH (a:Alert)
        RETURN 
            a.scenario_code as scenario,
            COUNT(a) as count
        """
        
        scenario_results = db.execute_query(scenario_query)
        scenarios = {}
        for r in scenario_results:
            scenarios[r["scenario"]] = r["count"]
        
        # Get resolution distribution
        resolution_query = """
        MATCH (a:Alert)-[:HAS_RESOLUTION]->(r:Resolution)
        RETURN 
            r.recommendation as recommendation,
            COUNT(r) as count
        """
        
        resolution_results = db.execute_query(resolution_query)
        resolutions = {}
        for r in resolution_results:
            resolutions[r["recommendation"]] = r["count"]
        
        return DashboardMetricsResponse(
            total_alerts=metrics.get("total", 0),
            alerts_by_status={
                "OPEN": metrics.get("open_count", 0),
                "INVESTIGATING": metrics.get("investigating_count", 0),
                "RESOLVED": metrics.get("resolved_count", 0)
            },
            alerts_by_scenario={
                "VELOCITY_SPIKE": scenarios.get("VELOCITY_SPIKE", 0),
                "STRUCTURING": scenarios.get("STRUCTURING", 0),
                "KYC_INCONSISTENCY": scenarios.get("KYC_INCONSISTENCY", 0),
                "SANCTIONS_HIT": scenarios.get("SANCTIONS_HIT", 0),
                "DORMANT_ACTIVATION": scenarios.get("DORMANT_ACTIVATION", 0),
            },
            resolution_distribution={
                "ESCALATE": resolutions.get("ESCALATE", 0),
                "CLOSE": resolutions.get("CLOSE", 0),
                "RFI": resolutions.get("RFI", 0),
                "BLOCK": resolutions.get("BLOCK", 0),
            },
            avg_resolution_time_seconds=3.2
        )
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alert updates"""
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or handle commands if needed
            logger.debug(f"WebSocket received: {data}")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    from fastapi.responses import JSONResponse
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_code": 500
        }
    )


if __name__ == "__main__":
    import uvicorn
    if config.API_RELOAD:
        # Use import string for reload mode
        uvicorn.run(
            "app:app",
            host=config.API_HOST,
            port=config.API_PORT,
            reload=True,
            log_level="info"
        )
    else:
        # Use app object directly when reload is disabled
        uvicorn.run(
            app,
            host=config.API_HOST,
            port=config.API_PORT,
            reload=False,
            log_level="info"
        )

