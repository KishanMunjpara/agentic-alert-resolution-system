"""
Action Executor Module
Executes resolved actions: RFI, IVR, SAR Prep
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ActionExecutor(BaseAgent):
    """
    Action Execution Module
    
    Responsibilities:
    - Execute RFI (Request for Information)
    - Execute IVR (Interactive Voice Response)
    - Execute SAR (Suspicious Activity Report) preparation
    - Log action results
    - Emit action events
    """
    
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """Initialize Action Executor"""
        super().__init__("ActionExecutor", broadcast_fn)
    
    async def execute(self, alert_id: str, resolution: Dict) -> Dict:
        """
        Execute recommended action
        
        Args:
            alert_id: Alert to execute action for
            resolution: Resolution containing recommendation
            
        Returns:
            Action execution result
        """
        self.reset_chain_of_thought()
        
        recommendation = resolution.get("recommendation", "RFI")
        self.logger.info(f"🎯 Executing action: {recommendation}")
        
        try:
            if recommendation == "RFI":
                result = await self._execute_rfi(alert_id, resolution)
            elif recommendation == "IVR":
                result = await self._execute_ivr(alert_id, resolution)
            elif recommendation == "ESCALATE":
                result = await self._execute_sar_prep(alert_id, resolution)
            elif recommendation == "BLOCK":
                result = await self._execute_block(alert_id, resolution)
            elif recommendation == "CLOSE":
                result = await self._execute_close(alert_id, resolution)
            else:
                result = await self._execute_rfi(alert_id, resolution)  # Default to RFI
            
            self.log_chain_of_thought(
                "Action Executed",
                {"action": recommendation, "result": result}
            )
            
            # Store action result in Resolution node
            await self._update_resolution_with_action(alert_id, recommendation, result)
            
            # Emit action event
            await self.emit_event("action_executed", {
                "alert_id": alert_id,
                "action_type": recommendation,
                "result": result
            })
            
            return result
            
        except Exception as e:
            error_details = self.handle_error(e, "Action execution")
            return {"error": str(e), **error_details}
    
    async def _execute_rfi(self, alert_id: str, resolution: Dict) -> Dict:
        """Execute RFI (Request for Information) with email sending"""
        self.logger.info(f"📧 Executing RFI for alert {alert_id}")
        
        # Get customer info
        customer = await self._get_customer_info(alert_id)
        
        # Try to send actual email (with fallback to console)
        try:
            from services.email_service import get_email_service
            from services.malfunction_handler import get_malfunction_handler
            
            email_service = get_email_service()
            malfunction_handler = get_malfunction_handler()
            
            # Send email with evaluation report (async function needs to be awaited)
            # Note: Report generation happens inside send_rfi_email automatically
            self.logger.info(f"📧 Attempting to send RFI email to {customer.get('email')}...")
            email_result = await malfunction_handler.execute_with_retry_async(
                email_service.send_rfi_email,
                "EMAIL_SERVICE",
                customer,
                alert_id,
                resolution
            )
            
            self.logger.info(f"📧 Email result: {email_result}")
            
            if email_result and email_result.get("success"):
                self.logger.info(f"✓ RFI email sent successfully to {customer.get('email')}")
                
                # Update alert status to AWAITING_PROOF
                await self._update_alert_status(alert_id, "AWAITING_PROOF")
                
                return {
                    "action": "RFI",
                    "status": "EMAIL_SENT",
                    "customer": customer,
                    "email_result": email_result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Email failed but log it with full details
                reason = email_result.get('reason', email_result.get('error', 'Unknown error')) if email_result else 'No result returned'
                status = email_result.get('status', 'UNKNOWN') if email_result else 'NO_RESULT'
                self.logger.error(f"✗ Email sending failed! Status: {status}, Reason: {reason}")
                self.logger.error(f"✗ Full email result: {email_result}")
                # Fall through to console output
        
        except Exception as e:
            # Email service unavailable - fallback to console
            self.logger.warning(f"Email service unavailable, using console output: {e}")
            from services.malfunction_handler import get_malfunction_handler, MalfunctionType, MalfunctionSeverity
            malfunction_handler = get_malfunction_handler()
            malfunction_handler.record_malfunction(
                malfunction_type=MalfunctionType.EMAIL_SERVICE_FAILURE,
                severity=MalfunctionSeverity.MEDIUM,
                component="ActionExecutor",
                error_message=str(e),
                alert_id=alert_id
            )
        
        # Fallback: Console output (original behavior)
        # Assignment requirement: "Action Executed: RFI via Email. Drafted message for Customer: [Customer_Name] requesting Source of Funds."
        customer_name = customer.get('name', 'Unknown')
        message = f"Action Executed: RFI via Email. Drafted message for Customer: {customer_name} requesting Source of Funds."
        
        # Additional details for audit trail
        detailed_message = f"""
        {message}
        
        Alert ID: {alert_id}
        Customer: {customer_name}
        Email: {customer.get('email', 'unknown@example.com')}
        
        Subject: Request for Transaction Information
        
        Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},
        
        We are reaching out to request clarification regarding recent transactions 
        on your account. Please provide the source of funds and purpose of these transactions 
        at your earliest convenience.
        
        Regards,
        Compliance Team
        """
        
        self.logger.info(message)  # Assignment-required format
        self.logger.info(detailed_message)  # Additional details
        
        return {
            "action": "RFI",
            "status": "EXECUTED_CONSOLE",  # Indicates console fallback
            "customer": customer,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_ivr(self, alert_id: str, resolution: Dict) -> Dict:
        """Execute IVR (Interactive Voice Response) - Automatically sends notification"""
        self.logger.info(f"📞 Executing IVR for alert {alert_id}")
        
        # Get customer info
        customer = await self._get_customer_info(alert_id)
        
        # Automatically send IVR notification email to customer
        try:
            from services.email_service import get_email_service
            from services.malfunction_handler import get_malfunction_handler
            
            email_service = get_email_service()
            malfunction_handler = get_malfunction_handler()
            
            # Send IVR notification email
            self.logger.info(f"📧 Sending IVR notification to {customer.get('email')}...")
            email_result = await malfunction_handler.execute_with_retry_async(
                self._send_ivr_notification_email,
                "EMAIL_SERVICE",
                email_service,
                customer,
                alert_id,
                resolution
            )
            
            if email_result and email_result.get("success"):
                self.logger.info(f"✓ IVR notification sent to {customer.get('email')}")
            else:
                self.logger.warning(f"IVR notification email failed, continuing with IVR execution")
        except Exception as e:
            self.logger.warning(f"Could not send IVR notification email: {e}, continuing with IVR execution")
        
        # Assignment requirement: "Action Executed: IVR Call Initiated. Script ID 3 used for simple verification. Awaiting Customer Response..."
        message = "Action Executed: IVR Call Initiated. Script ID 3 used for simple verification. Awaiting Customer Response..."
        
        # Additional details for audit trail
        detailed_message = f"""
        {message}
        
        Alert ID: {alert_id}
        Customer: {customer.get('name', 'Unknown')}
        Phone: {customer.get('phone', 'N/A')}
        
        IVR Script Details:
        - Script ID: 3
        - Purpose: Simple verification for dormant account activation
        - Verification Questions:
          1. Please confirm your identity with your account number
          2. Please provide the source of funds for the recent transaction
          3. Please confirm the purpose of the transaction
        
        Status: Call initiated, awaiting customer response
        Next Step: Customer will be contacted via automated IVR system
        """
        
        self.logger.info(message)  # Assignment-required format
        self.logger.info(detailed_message)  # Additional details
        
        # Update alert status to AWAITING_RESPONSE
        await self._update_alert_status(alert_id, "AWAITING_RESPONSE")
        
        return {
            "action": "IVR",
            "status": "CALL_INITIATED",
            "customer": customer,
            "script_id": 3,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_sar_prep(self, alert_id: str, resolution: Dict) -> Dict:
        """Execute SAR (Suspicious Activity Report) Preparation"""
        self.logger.info(f"📋 Escalating to SAR Prep for alert {alert_id}")
        
        customer = await self._get_customer_info(alert_id)
        
        # Assignment requirement: "Action Executed: SAR Preparer Module Activated. Case [Alert_ID] pre-populated and routed to Human Queue. Rationale: [Adjudicator Rationale]."
        rationale = resolution.get('rationale', 'No rationale provided')
        message = f"Action Executed: SAR Preparer Module Activated. Case {alert_id} pre-populated and routed to Human Queue. Rationale: {rationale}."
        
        # Additional details for audit trail
        detailed_message = f"""
        {message}
        
        Alert ID: {alert_id}
        Customer ID: {customer.get('id', 'N/A')}
        Customer Name: {customer.get('name', 'Unknown')}
        
        Rationale: {rationale}
        Confidence: {resolution.get('confidence', 0):.2%}
        
        Status: Case pre-populated and routed to Human Review Queue
        
        SAR Form Fields:
        - Suspect Information: {customer.get('name', 'Unknown')}
        - Transaction Description: {resolution.get('findings', {}).get('transaction_description', 'See findings')}
        - Amount: ${resolution.get('findings', {}).get('total_amount', 0):,.2f}
        - Detection Date: {datetime.now().strftime('%Y-%m-%d')}
        
        Priority: HIGH
        Next Step: Human analyst review and SAR filing
        """
        
        self.logger.info(message)  # Assignment-required format
        self.logger.info(detailed_message)  # Additional details
        
        # Create SAR Case node in Neo4j
        sar_id = await self._create_sar_case(alert_id, customer, resolution)
        
        # Automatically notify compliance team/analysts about SAR case
        try:
            await self._notify_compliance_team(alert_id, customer, resolution, sar_id)
        except Exception as e:
            self.logger.warning(f"Could not notify compliance team: {e}, continuing with SAR prep")
        
        # Update alert status to ESCALATED
        await self._update_alert_status(alert_id, "ESCALATED")
        
        return {
            "action": "SAR_PREP",
            "status": "ROUTED_TO_QUEUE",
            "customer": customer,
            "rationale": resolution.get("rationale"),
            "confidence": resolution.get("confidence"),
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_block(self, alert_id: str, resolution: Dict) -> Dict:
        """Execute BLOCK - Block transaction/account"""
        self.logger.info(f"🚫 Blocking account for alert {alert_id}")
        
        customer = await self._get_customer_info(alert_id)
        
        message = f"""
        Action Executed: Account Blocked
        
        Alert ID: {alert_id}
        Customer: {customer.get('name', 'Unknown')}
        
        Status: Customer account temporarily blocked pending review
        
        Reason: {resolution.get('rationale', 'Sanctions or high-risk match detected')}
        
        Next Steps:
        1. Notify customer of block
        2. Schedule compliance review
        3. Determine if regulatory reporting required
        4. Document decision and rationale
        """
        
        self.logger.info(message)
        
        # Block the account in database
        await self._block_account(alert_id, resolution)
        
        # Automatically notify customer about account block
        try:
            from services.email_service import get_email_service
            from services.malfunction_handler import get_malfunction_handler
            
            email_service = get_email_service()
            malfunction_handler = get_malfunction_handler()
            
            self.logger.info(f"📧 Sending block notification to {customer.get('email')}...")
            email_result = await malfunction_handler.execute_with_retry_async(
                self._send_block_notification_email,
                "EMAIL_SERVICE",
                email_service,
                customer,
                alert_id,
                resolution
            )
            
            if email_result and email_result.get("success"):
                self.logger.info(f"✓ Block notification sent to {customer.get('email')}")
            else:
                self.logger.warning(f"Block notification email failed, but account is blocked")
        except Exception as e:
            self.logger.warning(f"Could not send block notification email: {e}, but account is blocked")
        
        # Update alert status to BLOCKED
        await self._update_alert_status(alert_id, "BLOCKED")
        
        return {
            "action": "BLOCK",
            "status": "ACCOUNT_BLOCKED",
            "customer": customer,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_close(self, alert_id: str, resolution: Dict) -> Dict:
        """Execute CLOSE - Close alert as false positive"""
        self.logger.info(f"✓ Closing alert {alert_id} as false positive")
        
        # Get customer info
        customer = await self._get_customer_info(alert_id)
        
        message = f"""
        Action Executed: Alert Closed (False Positive)
        
        Alert ID: {alert_id}
        
        Reason: {resolution.get('rationale', 'Pattern identified as false positive')}
        Confidence: {resolution.get('confidence', 0):.2%}
        
        Status: Alert closed and archived
        
        Action: No further action required
        """
        
        self.logger.info(message)
        
        # Automatically notify customer about closure
        try:
            from services.email_service import get_email_service
            from services.malfunction_handler import get_malfunction_handler
            
            email_service = get_email_service()
            malfunction_handler = get_malfunction_handler()
            
            self.logger.info(f"📧 Sending closure notification to {customer.get('email')}...")
            email_result = await malfunction_handler.execute_with_retry_async(
                self._send_closure_notification_email,
                "EMAIL_SERVICE",
                email_service,
                customer,
                alert_id,
                resolution
            )
            
            if email_result and email_result.get("success"):
                self.logger.info(f"✓ Closure notification sent to {customer.get('email')}")
            else:
                self.logger.warning(f"Closure notification email failed, but alert is closed")
        except Exception as e:
            self.logger.warning(f"Could not send closure notification email: {e}, but alert is closed")
        
        # Update alert status to RESOLVED
        await self._update_alert_status(alert_id, "RESOLVED")
        
        return {
            "action": "CLOSE",
            "status": "CLOSED",
            "rationale": resolution.get("rationale"),
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _update_alert_status(self, alert_id: str, status: str):
        """Update alert status"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        SET a.status = $status,
            a.updated_at = datetime()
        RETURN a
        """
        await self.write_to_database(query, {"alert_id": alert_id, "status": status})
        self.logger.info(f"✓ Updated alert {alert_id} status to {status}")
    
    async def _update_resolution_with_action(self, alert_id: str, action_type: str, action_result: Dict):
        """Update Resolution node with action execution details"""
        import json
        query = """
        MATCH (a:Alert {alert_id: $alert_id})-[:HAS_RESOLUTION]->(r:Resolution)
        SET r.action_executed = $action_type,
            r.action_status = $action_status,
            r.action_timestamp = $action_timestamp,
            r.action_result = $action_result
        RETURN r
        """
        
        try:
            await self.write_to_database(query, {
                "alert_id": alert_id,
                "action_type": action_type,
                "action_status": action_result.get("status", "EXECUTED"),
                "action_timestamp": action_result.get("timestamp", datetime.now().isoformat()),
                "action_result": json.dumps(action_result)
            })
            self.logger.debug(f"✓ Updated resolution with action details for {alert_id}")
        except Exception as e:
            self.logger.warning(f"Failed to update resolution with action: {e}")
    
    async def _create_sar_case(self, alert_id: str, customer: Dict, resolution: Dict):
        """Create SAR Case node in Neo4j"""
        import uuid
        import json
        
        sar_id = f"SAR-{uuid.uuid4().hex[:8]}"
        
        # Get findings for form fields
        findings = resolution.get("findings", {})
        total_amount = findings.get("total_amount", 0)
        transaction_description = findings.get("transaction_description", "See investigation findings")
        
        query = """
        MATCH (a:Alert {alert_id: $alert_id})
        CREATE (sar:SARCase {
            sar_id: $sar_id,
            alert_id: $alert_id,
            customer_id: $customer_id,
            customer_name: $customer_name,
            suspect_information: $suspect_info,
            transaction_description: $txn_description,
            amount: $amount,
            detection_date: $detection_date,
            rationale: $rationale,
            confidence_score: $confidence,
            priority: $priority,
            status: 'PENDING_REVIEW',
            created_at: $timestamp
        })
        CREATE (a)-[:ESCALATED_TO_SAR]->(sar)
        RETURN sar.sar_id as sar_id
        """
        
        try:
            await self.write_to_database(query, {
                "sar_id": sar_id,
                "alert_id": alert_id,
                "customer_id": customer.get("id", "UNKNOWN"),
                "customer_name": customer.get("name", "Unknown"),
                "suspect_info": json.dumps({
                    "name": customer.get("name", "Unknown"),
                    "customer_id": customer.get("id", "UNKNOWN")
                }),
                "txn_description": transaction_description,
                "amount": float(total_amount),
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "rationale": resolution.get("rationale", "No rationale provided"),
                "confidence": float(resolution.get("confidence", 0)),
                "priority": "HIGH",
                "timestamp": datetime.now().isoformat()
            })
            self.logger.info(f"✓ Created SAR Case {sar_id} for alert {alert_id}")
            return sar_id
        except Exception as e:
            self.logger.error(f"Failed to create SAR case: {e}")
            return ""
    
    async def _block_account(self, alert_id: str, resolution: Dict):
        """Block account in database"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})-[:INVESTIGATES_ACCOUNT]->(acc:Account)
        SET acc.status = 'BLOCKED',
            acc.blocked_at = $timestamp,
            acc.block_reason = $reason,
            acc.blocked_by = 'ActionExecutor',
            acc.updated_at = datetime()
        RETURN acc.account_id as account_id
        """
        
        try:
            results = await self.write_to_database(query, {
                "alert_id": alert_id,
                "timestamp": datetime.now().isoformat(),
                "reason": resolution.get("rationale", "Sanctions or high-risk match detected")
            })
            self.logger.info(f"✓ Blocked account for alert {alert_id}")
        except Exception as e:
            self.logger.error(f"Failed to block account: {e}")
    
    async def _send_ivr_notification_email(self, email_service, customer: Dict, alert_id: str, resolution: Dict) -> Dict:
        """Send IVR notification email to customer"""
        subject = "Automated Verification Call - Action Required"
        body = f"""
Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},

We need to verify some information regarding recent activity on your account.

An automated verification call will be placed to your registered phone number shortly. 
Please be prepared to answer the following verification questions:

1. Please confirm your identity with your account number
2. Please provide the source of funds for the recent transaction
3. Please confirm the purpose of the transaction

Alert ID: {alert_id}

If you have any questions, please contact our customer service team.

Best regards,
Compliance Team
        """
        
        return await email_service._send_email_simple(
            to_email=customer.get('email'),
            subject=subject,
            body=body
        )
    
    async def _send_block_notification_email(self, email_service, customer: Dict, alert_id: str, resolution: Dict) -> Dict:
        """Send account block notification email to customer"""
        subject = "Important: Account Access Temporarily Restricted"
        body = f"""
Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},

This is an important notification regarding your account.

Your account has been temporarily restricted pending a compliance review.

Reason: {resolution.get('rationale', 'Security review required')}

Alert ID: {alert_id}

What you need to know:
- Your account access is temporarily restricted
- This is a precautionary measure
- A compliance review is scheduled
- You will be notified once the review is complete

If you believe this is an error or have questions, please contact our customer service team immediately.

Best regards,
Compliance Team
        """
        
        return await email_service._send_email_simple(
            to_email=customer.get('email'),
            subject=subject,
            body=body
        )
    
    async def _send_closure_notification_email(self, email_service, customer: Dict, alert_id: str, resolution: Dict) -> Dict:
        """Send alert closure notification email to customer"""
        subject = "Alert Resolved - No Action Required"
        body = f"""
Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},

We are writing to inform you that a recent alert on your account has been reviewed and resolved.

Alert ID: {alert_id}

Resolution: The activity has been reviewed and determined to be legitimate. No further action is required on your part.

Reason: {resolution.get('rationale', 'Pattern identified as false positive')}

Your account continues to operate normally. If you have any questions or concerns, please don't hesitate to contact us.

Thank you for your patience.

Best regards,
Compliance Team
        """
        
        return await email_service._send_email_simple(
            to_email=customer.get('email'),
            subject=subject,
            body=body
        )
    
    async def _notify_compliance_team(self, alert_id: str, customer: Dict, resolution: Dict, sar_id: str):
        """Automatically notify compliance team about new SAR case"""
        # Get compliance team email from config or use default
        import os
        compliance_email = os.getenv("COMPLIANCE_TEAM_EMAIL", "kishan.students@gmail.com")
        
        try:
            from services.email_service import get_email_service
            email_service = get_email_service()
            
            subject = f"URGENT: New SAR Case Created - {sar_id}"
            body = f"""
New Suspicious Activity Report (SAR) case has been created and requires immediate review.

SAR Case ID: {sar_id}
Alert ID: {alert_id}
Customer: {customer.get('name', 'Unknown')} ({customer.get('id', 'N/A')})

Rationale: {resolution.get('rationale', 'No rationale provided')}
Confidence Score: {resolution.get('confidence', 0):.2%}

Priority: HIGH
Status: PENDING_REVIEW

The SAR case has been pre-populated with all relevant information and is now in the Human Review Queue.

Please log into the compliance system to review and file the SAR.

Best regards,
Agentic Alert Resolution System
            """
            
            result = await email_service._send_email_simple(
                to_email=compliance_email,
                subject=subject,
                body=body
            )
            
            if result.get("success"):
                self.logger.info(f"✓ Compliance team notified about SAR case {sar_id}")
            else:
                self.logger.warning(f"Failed to notify compliance team: {result.get('reason', 'Unknown error')}")
        except Exception as e:
            self.logger.error(f"Error notifying compliance team: {e}")
    
    async def _get_customer_info(self, alert_id: str) -> Dict:
        """Get customer information for action execution"""
        query = """
        MATCH (a:Alert {alert_id: $alert_id})-[:INVESTIGATES_CUSTOMER]->(c:Customer)
        RETURN {
            id: c.customer_id,
            first_name: COALESCE(c.first_name, ''),
            last_name: COALESCE(c.last_name, ''),
            name: COALESCE(c.first_name, '') + ' ' + COALESCE(c.last_name, ''),
            email: COALESCE(c.email, ''),
            phone: COALESCE(c.phone, '')
        } as customer
        """
        
        try:
            results = await self.query_database(query, {"alert_id": alert_id})
            if results:
                customer = results[0]["customer"]
                # Ensure all required fields exist
                if not customer.get("email"):
                    customer["email"] = "unknown@example.com"
                if not customer.get("first_name"):
                    customer["first_name"] = "Valued"
                if not customer.get("last_name"):
                    customer["last_name"] = "Customer"
                return customer
            return {
                "id": "unknown",
                "first_name": "Valued",
                "last_name": "Customer",
                "name": "Unknown Customer",
                "email": "unknown@example.com",
                "phone": ""
            }
        except Exception as e:
            self.logger.error(f"Failed to get customer info: {e}")
            return {
                "id": "unknown",
                "first_name": "Valued",
                "last_name": "Customer",
                "name": "Unknown Customer",
                "email": "unknown@example.com",
                "phone": ""
            }

