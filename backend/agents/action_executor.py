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
        message = f"""
        Action Executed: RFI via Email
        
        Alert ID: {alert_id}
        Customer: {customer.get('name', 'Unknown')}
        Email: {customer.get('email', 'unknown@example.com')}
        
        Subject: Request for Transaction Information
        
        Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},
        
        We are reaching out to request clarification regarding recent transactions 
        on your account. Please provide the source of funds and purpose of these transactions 
        at your earliest convenience.
        
        Regards,
        Compliance Team
        """
        
        self.logger.info(message)
        
        return {
            "action": "RFI",
            "status": "EXECUTED_CONSOLE",  # Indicates console fallback
            "customer": customer,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_ivr(self, alert_id: str, resolution: Dict) -> Dict:
        """Execute IVR (Interactive Voice Response)"""
        self.logger.info(f"📞 Executing IVR for alert {alert_id}")
        
        # Get customer info
        customer = await self._get_customer_info(alert_id)
        
        # According to assignment: "Action Executed: IVR Call Initiated. Script ID 3 used for simple verification. Awaiting Customer Response..."
        message = f"""
        Action Executed: IVR Call Initiated. Script ID 3 used for simple verification. Awaiting Customer Response...
        
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
        
        self.logger.info(message)
        
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
        
        message = f"""
        Action Executed: SAR Preparer Module Activated
        
        Alert ID: {alert_id}
        Customer ID: {customer.get('id', 'N/A')}
        Customer Name: {customer.get('name', 'Unknown')}
        
        Rationale: {resolution.get('rationale', 'No rationale provided')}
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
        
        self.logger.info(message)
        
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
        
        message = f"""
        Action Executed: Alert Closed (False Positive)
        
        Alert ID: {alert_id}
        
        Reason: {resolution.get('rationale', 'Pattern identified as false positive')}
        Confidence: {resolution.get('confidence', 0):.2%}
        
        Status: Alert closed and archived
        
        Action: No further action required
        """
        
        self.logger.info(message)
        
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
        await self.query_database(query, {"alert_id": alert_id, "status": status})
        self.logger.info(f"✓ Updated alert {alert_id} status to {status}")
    
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

