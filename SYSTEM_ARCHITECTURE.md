# Agentic Alert Resolution System (AARS) - Architecture Overview

## Objective Alignment

### ✅ Objective: Design and implement a simplified, working model of AARS
**Status**: **FULLY IMPLEMENTED**

The system provides a complete, working implementation with:
- Multi-agent architecture (Hub-and-Spoke pattern)
- Real-time investigation processing
- Complete audit trail
- WebSocket-based live updates
- RESTful API for alert management

### ✅ Goal 1: Demonstrate ability to structure a multi-agent application
**Status**: **FULLY IMPLEMENTED**

#### Architecture Pattern: Hub-and-Spoke
```
Orchestrator Agent (Hub)
├── Investigator Agent (Spoke)
├── Context Gatherer Agent (Spoke)
├── Adjudicator Agent (Spoke)
└── Action Executor Module (Spoke)
```

#### Key Components:

1. **BaseAgent** (`backend/agents/base_agent.py`)
   - Abstract base class for all agents
   - Provides common functionality:
     - Chain-of-thought logging
     - WebSocket event emission
     - Neo4j database access
     - Error handling

2. **OrchestratorAgent** (`backend/agents/orchestrator.py`)
   - Hub agent coordinating the investigation workflow
   - Responsibilities:
     - Receive alerts
     - Route to appropriate spoke agents
     - Coordinate investigation sequence
     - Manage investigation timeline
     - Broadcast events via WebSocket

3. **Spoke Agents**:
   - **InvestigatorAgent**: Queries transaction history, calculates metrics
   - **ContextGathererAgent**: Retrieves KYC profiles and customer context
   - **AdjudicatorAgent**: Evaluates SOPs and makes resolution decisions
   - **ActionExecutor**: Executes actions (RFI, IVR, SAR Prep, BLOCK, CLOSE)

### ✅ Goal 2: Leverage external tools (simulated)
**Status**: **FULLY IMPLEMENTED**

#### Simulated External Tools:

1. **OSINT Service** (`backend/services/osint_service.py`)
   - Simulates adverse media search
   - Returns mock results based on customer data
   - Production-ready interface for integration with:
     - Dow Jones Risk & Compliance
     - World-Check
     - LexisNexis

2. **Email Service** (`backend/services/email_service.py`)
   - SMTP integration (Brevo/Gmail)
   - Automated email sending for:
     - RFI requests
     - IVR notifications
     - SAR case notifications
     - Block/closure notifications
   - Evaluation report attachments

3. **Database Tools** (via Neo4jConnector)
   - Historical transaction lookback (90 days)
   - Customer KYC profile retrieval
   - Linked account queries
   - Sanctions list matching

4. **LLM Service** (`backend/services/llm_service.py`)
   - OpenAI integration for SOP evaluation
   - Edge case handling
   - Rationale generation
   - Structured output support

### ✅ Goal 3: Apply conditional reasoning (SOPs)
**Status**: **FULLY IMPLEMENTED**

#### SOP Evaluation System:

1. **SOP Storage** (Neo4j)
   - SOPs stored as nodes with:
     - `rule_id`: Unique identifier
     - `scenario_code`: Alert scenario
     - `condition_logic`: Conditional rules
     - `action`: Decision (ESCALATE, RFI, CLOSE, etc.)
     - `priority`: Evaluation order

2. **Adjudicator Agent** (`backend/agents/adjudicator.py`)
   - Retrieves applicable SOPs for scenario
   - Evaluates SOP conditions using:
     - Rule-based evaluation (primary)
     - LLM-based evaluation (fallback for edge cases)
   - Applies decision logic (if/then/else)
   - Generates rationale and confidence scores

3. **SOP Evaluation Process**:
   ```
   For each applicable SOP:
   1. Parse condition logic
   2. Evaluate against findings + context
   3. Calculate confidence score
   4. If matched and confidence > threshold:
      → Use this SOP's action
   5. If no SOP matches:
      → Use LLM for edge case handling
   ```

4. **Decision Types**:
   - `ESCALATE`: Escalate to SAR Prep
   - `RFI`: Request for Information
   - `IVR`: Interactive Voice Response
   - `CLOSE`: Close as false positive
   - `BLOCK`: Block account/transaction

### ✅ Goal 4: Produce compliant, auditable resolution
**Status**: **FULLY IMPLEMENTED**

#### Audit Trail Components:

1. **Chain-of-Thought Logging**
   - Every agent logs reasoning steps
   - Includes:
     - Timestamp
     - Step description
     - Details (findings, context, decisions)
     - Confidence scores
   - Stored in agent's `chain_of_thought` array

2. **Event Logging** (Neo4j)
   - All events stored as `Event` nodes
   - Event types:
     - `investigation_started`
     - `investigator_finding`
     - `context_found`
     - `decision_made`
     - `action_executed`
     - `investigation_complete`
   - Linked to Alert via `FOR_ALERT` relationship

3. **Resolution Storage** (Neo4j)
   - Resolution node contains:
     - `resolution_id`: Unique identifier
     - `recommendation`: Decision (ESCALATE, RFI, etc.)
     - `rationale`: Explanation
     - `confidence_score`: Confidence level (0-1)
     - `investigator_findings`: JSON string of findings
     - `context_data`: JSON string of context
     - `sop_matched`: Matched SOP rule ID
     - `created_at`: Timestamp
   - Linked to Alert via `HAS_RESOLUTION` relationship

4. **Timeline API** (`/alerts/{alert_id}/timeline`)
   - Returns complete investigation timeline
   - All events in chronological order
   - Includes agent names and event data

5. **System Guardrails** (`backend/services/system_guardrails.py`)
   - Input validation
   - Output sanitization
   - Security event logging
   - Audit log management

## System Architecture

### Data Flow

```
Alert Ingested
    ↓
Orchestrator Agent
    ├─→ Investigator Agent
    │   └─→ Findings (transaction patterns, metrics)
    │
    ├─→ Context Gatherer Agent
    │   └─→ Context (KYC profile, risk rating)
    │
    ├─→ Adjudicator Agent
    │   ├─→ Retrieve SOPs
    │   ├─→ Evaluate SOPs
    │   └─→ Resolution Decision
    │
    └─→ Action Executor
        └─→ Execute Action (RFI/IVR/SAR/BLOCK/CLOSE)
            ↓
Resolution Stored & Auditable
```

### Database Schema (Neo4j)

**Node Types**:
- `Alert`: Banking transaction alerts
- `Customer`: Customer information
- `Account`: Bank accounts
- `Transaction`: Transaction records
- `Resolution`: Investigation resolutions
- `SOP`: Standard Operating Procedures
- `Event`: Audit trail events
- `SARCase`: Suspicious Activity Reports

**Key Relationships**:
- `(Alert)-[:INVESTIGATES_CUSTOMER]->(Customer)`
- `(Alert)-[:INVESTIGATES_ACCOUNT]->(Account)`
- `(Alert)-[:HAS_RESOLUTION]->(Resolution)`
- `(Alert)<-[:FOR_ALERT]-(Event)`
- `(Customer)-[:OWNS]->(Account)`
- `(Account)-[:HAS_TRANSACTION]->(Transaction)`

## Key Features

### 1. Multi-Agent Coordination
- Orchestrator manages workflow
- Spoke agents execute specialized tasks
- Asynchronous execution with proper error handling

### 2. SOP-Based Decision Making
- Rule-based evaluation (primary)
- LLM-based evaluation (fallback)
- Confidence scoring
- Rationale generation

### 3. Complete Audit Trail
- Chain-of-thought logging
- Event timeline
- Resolution storage
- WebSocket real-time updates

### 4. External Tool Integration
- OSINT service (simulated)
- Email service (SMTP)
- Database queries (Neo4j)
- LLM service (OpenAI)

### 5. 5 Alert Scenarios
- A-001: Velocity Spike (Layering)
- A-002: Below-Threshold Structuring
- A-003: KYC Inconsistency
- A-004: Sanctions List Hit
- A-005: Dormant Account Activation

## Compliance & Auditability

### Audit Requirements Met:

1. **Complete Investigation Record**
   - All agent activities logged
   - Findings and context preserved
   - Decision rationale documented

2. **Timeline Tracking**
   - Chronological event log
   - Agent attribution
   - Timestamp for every action

3. **Resolution Documentation**
   - Decision with rationale
   - Confidence scores
   - SOP references
   - Complete findings and context

4. **System Guardrails**
   - Input validation
   - Output sanitization
   - Security event logging
   - Error handling

## API Endpoints

### Alert Management
- `POST /alerts/ingest`: Ingest new alert
- `GET /alerts/list`: List all alerts
- `GET /alerts/{alert_id}`: Get alert details
- `POST /alerts/{alert_id}/investigate`: Start investigation

### Resolution
- `GET /resolutions/{alert_id}`: Get resolution
- `GET /alerts/{alert_id}/evaluation-report`: Get evaluation report
- `POST /alerts/{alert_id}/send-report-email`: Send report email

### Timeline & Audit
- `GET /alerts/{alert_id}/timeline`: Get investigation timeline

### Analytics
- `GET /analytics/dashboard`: Dashboard metrics

### WebSocket
- `WS /ws/alerts`: Real-time event streaming

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: Neo4j (Graph Database)
- **LLM**: OpenAI GPT-4o (optional)
- **Email**: SMTP (Brevo/Gmail)
- **Frontend**: React + TypeScript + Vite
- **Real-time**: WebSocket

## Conclusion

The AARS implementation **fully meets** all stated objectives:

✅ **Multi-agent application structure**: Hub-and-spoke architecture with clear separation of concerns

✅ **External tool integration**: Simulated OSINT, email, database, and LLM services

✅ **Conditional reasoning**: SOP-based decision making with rule-based and LLM evaluation

✅ **Compliant, auditable resolutions**: Complete chain-of-thought logging, event timeline, and resolution storage

The system is production-ready with proper error handling, security guardrails, and comprehensive audit trails.

