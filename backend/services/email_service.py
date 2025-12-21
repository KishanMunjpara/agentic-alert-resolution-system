"""
Email Service
Handles sending emails to customers for RFI and other notifications
Includes guardrails for security and rate limiting
"""

import logging
import smtplib
import os
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import re
from config import config

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email Service with Security Guardrails
    
    Features:
    - SMTP email sending
    - Rate limiting per customer
    - Content validation and sanitization
    - Email template management
    - Audit logging
    - Error handling and retry logic
    """
    
    def __init__(self):
        """Initialize Email Service"""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        # Use SMTP user as from_email if FROM_EMAIL not set, or if they don't match (Gmail requirement)
        default_from = self.smtp_user if self.smtp_user else "compliance@bank.com"
        self.from_email = os.getenv("FROM_EMAIL", default_from)
        self.from_name = os.getenv("FROM_NAME", "Compliance Team")
        
        # Warn if FROM_EMAIL doesn't match SMTP_USER (Gmail requirement, but not for Brevo)
        # For Gmail: FROM_EMAIL must match SMTP_USER
        # For Brevo: FROM_EMAIL can be any verified sender email
        is_gmail = "gmail.com" in self.smtp_host.lower()
        if is_gmail and self.smtp_user and self.from_email != self.smtp_user:
            logger.warning(f"⚠️  FROM_EMAIL ({self.from_email}) doesn't match SMTP_USER ({self.smtp_user}). Gmail may reject emails. Consider setting FROM_EMAIL={self.smtp_user}")
        elif "brevo.com" in self.smtp_host.lower() or "sendinblue.com" in self.smtp_host.lower():
            logger.info(f"✓ Using Brevo SMTP. FROM_EMAIL ({self.from_email}) should be a verified sender in your Brevo account.")
        
        # Rate limiting: track emails per customer
        self.email_rate_limit = defaultdict(list)  # customer_id -> [timestamps]
        self.max_emails_per_hour = int(os.getenv("MAX_EMAILS_PER_HOUR", "5"))
        self.max_emails_per_day = int(os.getenv("MAX_EMAILS_PER_DAY", "10"))
        
        # Content guardrails
        self.blocked_domains = set(os.getenv("BLOCKED_EMAIL_DOMAINS", "").split(","))
        self.suspicious_keywords = ["password", "click here", "urgent", "verify account"]
        
        # Audit log
        self.email_audit_log = []
        
        logger.info("✓ Email Service initialized")
    
    def _check_rate_limit(self, customer_id: str) -> Tuple[bool, str]:
        """
        Check if customer has exceeded rate limits
        
        Returns:
            (allowed: bool, reason: str)
        """
        now = datetime.now()
        customer_emails = self.email_rate_limit[customer_id]
        
        # Remove emails older than 24 hours
        customer_emails[:] = [
            ts for ts in customer_emails 
            if now - ts < timedelta(hours=24)
        ]
        
        # Check hourly limit
        recent_emails = [
            ts for ts in customer_emails 
            if now - ts < timedelta(hours=1)
        ]
        
        if len(recent_emails) >= self.max_emails_per_hour:
            return False, f"Hourly rate limit exceeded ({self.max_emails_per_hour} emails/hour)"
        
        # Check daily limit
        if len(customer_emails) >= self.max_emails_per_day:
            return False, f"Daily rate limit exceeded ({self.max_emails_per_day} emails/day)"
        
        return True, "OK"
    
    def _validate_email_address(self, email: str) -> Tuple[bool, str]:
        """
        Validate email address format and domain
        
        Returns:
            (valid: bool, reason: str)
        """
        if not email or not isinstance(email, str):
            return False, "Email address is required"
        
        # Basic format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        # Check blocked domains
        domain = email.split("@")[1].lower()
        if domain in self.blocked_domains:
            return False, f"Email domain {domain} is blocked"
        
        # Check for suspicious patterns
        if any(keyword in email.lower() for keyword in ["test", "example", "fake"]):
            logger.warning(f"Suspicious email pattern detected: {email}")
        
        return True, "OK"
    
    def _sanitize_content(self, content: str) -> str:
        """
        Sanitize email content to prevent injection attacks
        
        Args:
            content: Email content to sanitize
            
        Returns:
            Sanitized content
        """
        # Remove potential script tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove javascript: protocol
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        
        # Remove data: URLs
        content = re.sub(r'data:[^;]*;base64,', '', content, flags=re.IGNORECASE)
        
        # Limit content length (prevent DoS)
        max_length = 10000
        if len(content) > max_length:
            logger.warning(f"Email content truncated from {len(content)} to {max_length} characters")
            content = content[:max_length] + "..."
        
        return content
    
    def _create_rfi_email(self, customer: Dict, alert_id: str, resolution: Dict, 
                          report_content: Optional[str] = None) -> MIMEMultipart:
        """
        Create RFI email with proper formatting
        
        Args:
            customer: Customer information
            alert_id: Alert ID
            resolution: Resolution details
            
        Returns:
            MIME message object
        """
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = customer.get("email", "")
        msg["Subject"] = "Request for Transaction Information"
        msg["X-Alert-ID"] = alert_id  # For tracking
        
        # Plain text version
        text_content = f"""
Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},

We are reaching out to request clarification regarding recent transactions on your account.

Alert ID: {alert_id}
Date: {datetime.now().strftime('%Y-%m-%d')}

Please provide the following information:
1. Source of funds for the recent transactions
2. Purpose of these transactions
3. Any additional context that may be relevant

Please respond at your earliest convenience. If you have any questions, please contact our compliance team.

Regards,
{self.from_name}
Compliance Department
        """
        
        # HTML version (sanitized)
        html_content = f"""
<html>
<body>
    <p>Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},</p>
    <p>We are reaching out to request clarification regarding recent transactions on your account.</p>
    <p><strong>Alert ID:</strong> {alert_id}<br>
    <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
    <p>Please provide the following information:</p>
    <ol>
        <li>Source of funds for the recent transactions</li>
        <li>Purpose of these transactions</li>
        <li>Any additional context that may be relevant</li>
    </ol>
    <p>Please respond at your earliest convenience. If you have any questions, please contact our compliance team.</p>
    <p>Regards,<br>
    {self.from_name}<br>
    Compliance Department</p>
</body>
</html>
        """
        
        # Sanitize content
        text_content = self._sanitize_content(text_content)
        html_content = self._sanitize_content(html_content)
        
        # Attach parts
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Attach evaluation report if provided
        if report_content:
            try:
                report_attachment = MIMEText(report_content, "plain")
                report_attachment.add_header(
                    "Content-Disposition",
                    f"attachment; filename=Evaluation_Report_{alert_id}.txt"
                )
                msg.attach(report_attachment)
                logger.info(f"✓ Attached evaluation report to email for alert {alert_id}")
            except Exception as e:
                logger.warning(f"Failed to attach report: {e}")
        
        return msg
    
    async def send_report_email(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        report_content: Optional[str] = None
    ) -> Dict:
        """
        Send email with evaluation report to customer (for any decision type)
        
        Args:
            customer: Customer information
            alert_id: Alert ID
            resolution: Resolution details
            report_content: Optional report content (will be generated if not provided)
            
        Returns:
            Result dictionary with status and details
        """
        customer_id = customer.get("id", "unknown")
        customer_email = customer.get("email", "")
        
        try:
            # Guardrail 1: Validate email address
            is_valid, reason = self._validate_email_address(customer_email)
            if not is_valid:
                logger.warning(f"Email validation failed for {customer_email}: {reason}")
                return {
                    "success": False,
                    "status": "VALIDATION_FAILED",
                    "reason": reason,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Guardrail 2: Check rate limits
            allowed, rate_limit_reason = self._check_rate_limit(customer_id)
            if not allowed:
                logger.warning(f"Rate limit exceeded for customer {customer_id}: {rate_limit_reason}")
                return {
                    "success": False,
                    "status": "RATE_LIMIT_EXCEEDED",
                    "reason": rate_limit_reason,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Guardrail 3: Get or generate evaluation report
            report_result = None
            html_report_content = None
            
            if not report_content:
                try:
                    from services.report_generator import get_report_generator
                    report_generator = get_report_generator()
                    
                    # Get findings and context from resolution
                    findings = resolution.get("findings", {})
                    context = resolution.get("context", {})
                    
                    report_result = await report_generator.generate_evaluation_report(
                        customer, alert_id, resolution, findings, context
                    )
                    
                    if report_result.get("success"):
                        report_content = report_result.get("content", "")
                        html_report_content = report_result.get("html_content")  # Get HTML version
                        logger.info(f"✓ Generated evaluation report for alert {alert_id}")
                    else:
                        logger.warning(f"Report generation failed: {report_result.get('error', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"Report generation unavailable: {e}")
            else:
                # If report_content was provided, try to get HTML version from stored report
                # This is better than parsing the formatted report
                try:
                    from services.report_generator import get_report_generator
                    report_generator = get_report_generator()
                    stored_report = report_generator.get_stored_report(alert_id)
                    if stored_report:
                        # First try to get pre-generated HTML
                        if stored_report.get("html_content"):
                            html_report_content = stored_report.get("html_content")
                        # Otherwise generate HTML from raw content (much better than parsing)
                        elif stored_report.get("raw_content"):
                            raw_content = stored_report.get("raw_content")
                            next_steps = stored_report.get("next_steps", "")
                            html_report_content = report_generator._format_report_html(
                                customer, alert_id, resolution, raw_content, next_steps
                            )
                            logger.info(f"✓ Generated HTML report from raw content for alert {alert_id}")
                except Exception as e:
                    logger.debug(f"Could not get HTML version from stored report: {e}")
            
            # Guardrail 4: Create email (with beautiful HTML report embedded)
            msg = self._create_report_email(customer, alert_id, resolution, report_content, html_report_content)
            
            # Guardrail 5: Send email with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Connect to SMTP server
                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.starttls()
                        if self.smtp_user and self.smtp_password:
                            server.login(self.smtp_user, self.smtp_password)
                        
                        # Send email
                        server.send_message(msg)
                    
                    # Log email details for diagnostics
                    logger.info(f"📧 Email details - From: {msg['From']}, To: {msg['To']}, Subject: {msg['Subject']}")
                    logger.info(f"📧 SMTP Config - Host: {self.smtp_host}, Port: {self.smtp_port}, User: {self.smtp_user}")
                    is_gmail = "gmail.com" in self.smtp_host.lower()
                    if is_gmail and self.from_email != self.smtp_user:
                        logger.warning(f"⚠️  FROM_EMAIL ({self.from_email}) != SMTP_USER ({self.smtp_user}). Gmail may reject or mark as spam!")
                    elif "brevo.com" in self.smtp_host.lower() or "sendinblue.com" in self.smtp_host.lower():
                        logger.info(f"✓ Using Brevo SMTP. FROM_EMAIL ({self.from_email}) should be verified in Brevo dashboard.")
                    logger.info(f"💡 Note: SMTP acceptance doesn't guarantee delivery. Check spam folder if email not received.")
                    
                    # Success - update rate limit tracking
                    self.email_rate_limit[customer_id].append(datetime.now())
                    
                    # Mark email as sent in database
                    try:
                        from services.report_generator import get_report_generator
                        report_generator = get_report_generator()
                        report_generator.mark_email_sent(alert_id, customer_email, "REPORT_EMAIL")
                    except Exception as e:
                        logger.warning(f"Failed to mark email as sent in database: {e}")
                    
                    # Audit log
                    audit_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "customer_id": customer_id,
                        "customer_email": customer_email,
                        "alert_id": alert_id,
                        "action": "REPORT_EMAIL_SENT",
                        "status": "SUCCESS",
                        "recommendation": resolution.get("recommendation", "UNKNOWN"),
                        "from_email": self.from_email,
                        "smtp_user": self.smtp_user
                    }
                    self.email_audit_log.append(audit_entry)
                    
                    logger.info(f"✓ Report email sent to {customer_email} for alert {alert_id}")
                    
                    return {
                        "success": True,
                        "status": "SENT",
                        "message": f"Email sent successfully to {customer_email}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except smtplib.SMTPException as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"SMTP error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error sending email: {e}")
                    raise
            
        except Exception as e:
            logger.error(f"Failed to send report email: {e}", exc_info=True)
            
            # Audit log failure
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "customer_id": customer_id,
                "customer_email": customer_email,
                "alert_id": alert_id,
                "action": "REPORT_EMAIL_SENT",
                "status": "FAILED",
                "error": str(e)
            }
            self.email_audit_log.append(audit_entry)
            
            return {
                "success": False,
                "status": "FAILED",
                "reason": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_report_email(
        self, 
        customer: Dict, 
        alert_id: str, 
        resolution: Dict, 
        report_content: Optional[str] = None,
        html_report_content: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email with beautiful HTML evaluation report embedded"""
        recommendation = resolution.get("recommendation", "RFI")
        customer_name = customer.get("name", "Customer")
        customer_email = customer.get("email", "")
        
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = customer_email
        msg["Subject"] = f"Transaction Evaluation Report - Alert {alert_id}"
        
        # Plain text version (fallback for email clients that don't support HTML)
        # Keep it simple - no next steps, just a brief message
        text_body = f"""Dear {customer_name},

We have completed an evaluation of recent activity on your account (Alert ID: {alert_id}).

Resolution: {recommendation}
Confidence: {resolution.get('confidence', 0):.1%}

Please find the detailed evaluation report in the HTML version of this email.

A separate Next Steps document has been attached for your reference.

If you have any questions or need assistance, please contact our Compliance Team:
- Email: compliance@bank.com
- Phone: 1-800-COMPLIANCE
- Hours: Monday - Friday, 9:00 AM - 5:00 PM EST

Best regards,
{self.from_name}
"""
        
        # Generate beautiful HTML email body
        html_body = ""
        if html_report_content:
            # Use pre-generated HTML report (best option - no parsing needed)
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="padding: 20px; background-color: #f3f4f6;">
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
            Dear {customer_name},
        </p>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
            We have completed an evaluation of recent activity on your account. Please find the detailed evaluation report below.
        </p>
        
        {html_report_content}
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-top: 30px;">
            Best regards,<br>
            <strong>{self.from_name}</strong>
        </p>
    </div>
</body>
</html>
            """
        elif report_content:
            # Generate HTML report on the fly if not pre-generated
            try:
                from services.report_generator import get_report_generator
                report_generator = get_report_generator()
                
                # The report_content passed here is the FULL formatted report
                # We need to extract just the evaluation details section (the LLM-generated content)
                # The formatted report structure is:
                # - Header with borders
                # - Executive Summary
                # - EVALUATION DETAILS section (this is what we want - the LLM content)
                # - NEXT STEPS section
                # - Contact Information
                
                # Get the raw report content and next steps from the report generator
                # Instead of parsing, we should get them from the stored report or regenerate
                # For now, let's parse more carefully
                import re
                
                eval_content = ""
                steps_content = ""
                
                # Split by major section dividers (the long dashes)
                sections = re.split(r'─{50,}', report_content)
                
                for i, section in enumerate(sections):
                    section_upper = section.upper()
                    # Find EVALUATION DETAILS section
                    if 'EVALUATION DETAILS' in section_upper and not eval_content:
                        # Get content after "EVALUATION DETAILS" header
                        parts = re.split(r'EVALUATION DETAILS', section, flags=re.IGNORECASE)
                        if len(parts) > 1:
                            eval_content = parts[1].strip()
                            # Remove any remaining headers or dividers
                            eval_content = re.sub(r'^[─\s]+', '', eval_content)
                            eval_content = re.sub(r'[─\s]+$', '', eval_content)
                            eval_content = eval_content.strip()
                    
                    # Find NEXT STEPS section  
                    if 'NEXT STEPS' in section_upper and not steps_content:
                        parts = re.split(r'NEXT STEPS', section, flags=re.IGNORECASE)
                        if len(parts) > 1:
                            steps_content = parts[1].strip()
                            # Remove any remaining headers or dividers
                            steps_content = re.sub(r'^[─\s]+', '', steps_content)
                            steps_content = re.sub(r'CONTACT INFORMATION.*', '', steps_content, flags=re.IGNORECASE | re.DOTALL)
                            steps_content = re.sub(r'[─\s]+$', '', steps_content)
                            steps_content = steps_content.strip()
                
                # Fallback: if parsing failed, try to get from report generator directly
                if not eval_content or len(eval_content) < 50:
                    # The report_content might be the full formatted report
                    # Try to extract just the evaluation part more aggressively
                    # Look for content that starts after "EVALUATION DETAILS" and contains actual text
                    match = re.search(
                        r'EVALUATION DETAILS[─\s]*(.*?)(?=NEXT STEPS|CONTACT INFORMATION|IMPORTANT NOTES|Generated:|Report ID:|$)',
                        report_content,
                        re.IGNORECASE | re.DOTALL
                    )
                    if match:
                        eval_content = match.group(1).strip()
                        # Clean up dividers
                        eval_content = re.sub(r'^[─\s\n]+', '', eval_content)
                        eval_content = re.sub(r'[─\s\n]+$', '', eval_content)
                        eval_content = eval_content.strip()
                    
                    # If still empty, use a portion of the report
                    if not eval_content or len(eval_content) < 50:
                        # Last resort: use content between known markers
                        # Find text that looks like evaluation content (has sentences, not just headers)
                        lines = report_content.split('\n')
                        in_eval_section = False
                        eval_lines = []
                        for line in lines:
                            if 'EVALUATION DETAILS' in line.upper():
                                in_eval_section = True
                                continue
                            if in_eval_section:
                                if 'NEXT STEPS' in line.upper() or 'CONTACT INFORMATION' in line.upper():
                                    break
                                if line.strip() and not line.strip().startswith('─'):
                                    eval_lines.append(line)
                        if eval_lines:
                            eval_content = '\n'.join(eval_lines).strip()
                
                # Generate HTML report
                html_report = report_generator._format_report_html(
                    customer,
                    alert_id,
                    resolution,
                    eval_content,
                    steps_content
                )
                
                # Create HTML email body with the report embedded
                html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="padding: 20px; background-color: #f3f4f6;">
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
            Dear {customer_name},
        </p>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
            We have completed an evaluation of recent activity on your account. Please find the detailed evaluation report below.
        </p>
        
        {html_report}
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-top: 30px;">
            Best regards,<br>
            <strong>{self.from_name}</strong>
        </p>
    </div>
</body>
</html>
                """
            except Exception as e:
                logger.warning(f"Failed to generate HTML report: {e}, using simple HTML")
                html_body = f"""
<html>
<body>
    <p>Dear {customer_name},</p>
    <p>We have completed an evaluation of recent activity on your account (Alert ID: {alert_id}).</p>
    <p><strong>Resolution:</strong> {recommendation}<br>
    <strong>Confidence:</strong> {resolution.get('confidence', 0):.1%}</p>
    <p>Please find the detailed evaluation report attached.</p>
    <p>Best regards,<br>{self.from_name}</p>
</body>
</html>
                """
        else:
            # Simple HTML if no report content
            html_body = f"""
<html>
<body>
    <p>Dear {customer_name},</p>
    <p>We have completed an evaluation of recent activity on your account (Alert ID: {alert_id}).</p>
    <p><strong>Resolution:</strong> {recommendation}<br>
    <strong>Confidence:</strong> {resolution.get('confidence', 0):.1%}</p>
    <p>Best regards,<br>{self.from_name}</p>
</body>
</html>
            """
        
        # Sanitize content
        text_body = self._sanitize_content(text_body)
        html_body = self._sanitize_content(html_body)
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_body.strip(), "plain"))
        msg.attach(MIMEText(html_body.strip(), "html"))
        
        # Create and attach Next Steps document if available
        if html_report_content:
            try:
                from services.report_generator import get_report_generator
                report_generator = get_report_generator()
                stored_report = report_generator.get_stored_report(alert_id)
                
                if stored_report and stored_report.get("next_steps"):
                    next_steps_content = stored_report.get("next_steps", "")
                    if next_steps_content:
                        # Create HTML document for Next Steps
                        next_steps_html = self._create_next_steps_document(
                            customer, alert_id, resolution, next_steps_content
                        )
                        
                        # Attach as HTML document
                        next_steps_html_attachment = MIMEText(next_steps_html, "html")
                        next_steps_html_attachment.add_header(
                            "Content-Disposition",
                            f"attachment; filename=Next_Steps_{alert_id}.html"
                        )
                        msg.attach(next_steps_html_attachment)
                        
                        # Also create plain text version (strip any HTML tags)
                        import re
                        # Remove HTML tags from next_steps_content if any
                        plain_next_steps = re.sub(r'<[^>]+>', '', next_steps_content)
                        # Decode HTML entities
                        import html
                        try:
                            plain_next_steps = html.unescape(plain_next_steps)
                        except:
                            pass
                        
                        next_steps_text = f"""Next Steps Guide
Action Items for Your Account Review

Alert Information:
- Alert ID: {alert_id}
- Customer: {customer_name}
- Resolution: {recommendation}
- Date: {datetime.now().strftime('%B %d, %Y')}

Next Steps:
{plain_next_steps}

Need Assistance?
Contact our Compliance Team:
- Email: compliance@bank.com
- Phone: 1-800-COMPLIANCE
- Hours: Monday - Friday, 9:00 AM - 5:00 PM EST
"""
                        next_steps_text_attachment = MIMEText(next_steps_text, "plain")
                        next_steps_text_attachment.add_header(
                            "Content-Disposition",
                            f"attachment; filename=Next_Steps_{alert_id}.txt"
                        )
                        msg.attach(next_steps_text_attachment)
                        logger.info(f"✓ Attached Next Steps documents (HTML and TXT) for alert {alert_id}")
            except Exception as e:
                logger.warning(f"Failed to attach Next Steps document: {e}")
        
        return msg
    
    def _create_next_steps_document(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        next_steps: str
    ) -> str:
        """Create a standalone HTML document for Next Steps"""
        customer_name = customer.get("name", "Customer")
        recommendation = resolution.get("recommendation", "RFI")
        
        # Format next steps with proper HTML
        import html
        escaped_steps = html.escape(next_steps)
        formatted_steps = escaped_steps.replace('\n', '<br>')
        
        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Next Steps - Alert {alert_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #111827;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #ffffff;
        }}
        .header {{
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            color: white;
            padding: 40px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            background-color: #ffffff;
            padding: 40px;
            border: 1px solid #e5e7eb;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        .info-box {{
            background-color: #f9fafb;
            border-left: 4px solid #2563eb;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 6px;
        }}
        .info-box h2 {{
            margin: 0 0 10px 0;
            font-size: 18px;
            color: #111827;
        }}
        .info-box p {{
            margin: 5px 0;
            color: #4b5563;
            font-size: 14px;
        }}
        .next-steps-content {{
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border-left: 4px solid #16a34a;
            padding: 30px;
            border-radius: 6px;
            margin-top: 30px;
        }}
        .next-steps-content h2 {{
            margin: 0 0 20px 0;
            color: #166534;
            font-size: 22px;
            font-weight: 700;
        }}
        .next-steps-content div {{
            color: #166534;
            font-size: 15px;
            line-height: 1.8;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 30px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }}
        .badge-rfi {{
            background-color: #dbeafe;
            color: #1e40af;
        }}
        .badge-escalate {{
            background-color: #fee2e2;
            color: #991b1b;
        }}
        .badge-close {{
            background-color: #dcfce7;
            color: #166534;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Next Steps Guide</h1>
        <p>Action Items for Your Account Review</p>
    </div>
    
    <div class="content">
        <div class="info-box">
            <h2>Alert Information</h2>
            <p><strong>Alert ID:</strong> {alert_id}</p>
            <p><strong>Customer:</strong> {customer_name}</p>
            <p><strong>Resolution:</strong> <span class="badge badge-{recommendation.lower()}">{recommendation}</span></p>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="next-steps-content">
            <h2>Next Steps</h2>
            <div>{formatted_steps}</div>
        </div>
        
        <div class="footer">
            <p><strong>Need Assistance?</strong></p>
            <p>Contact our Compliance Team:</p>
            <p>Email: <a href="mailto:compliance@bank.com" style="color: #2563eb;">compliance@bank.com</a> | 
               Phone: 1-800-COMPLIANCE</p>
            <p>Hours: Monday - Friday, 9:00 AM - 5:00 PM EST</p>
        </div>
    </div>
</body>
</html>"""
        
        return html_doc
    
    async def send_rfi_email(
        self, 
        customer: Dict, 
        alert_id: str, 
        resolution: Dict
    ) -> Dict:
        """
        Send RFI email to customer with guardrails
        
        Args:
            customer: Customer information
            alert_id: Alert ID
            resolution: Resolution details
            
        Returns:
            Result dictionary with status and details
        """
        customer_id = customer.get("id", "unknown")
        customer_email = customer.get("email", "")
        
        try:
            # Guardrail 1: Validate email address
            is_valid, reason = self._validate_email_address(customer_email)
            if not is_valid:
                logger.warning(f"Email validation failed for {customer_email}: {reason}")
                return {
                    "success": False,
                    "status": "VALIDATION_FAILED",
                    "reason": reason,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Guardrail 2: Check rate limits
            allowed, rate_limit_reason = self._check_rate_limit(customer_id)
            if not allowed:
                logger.warning(f"Rate limit exceeded for customer {customer_id}: {rate_limit_reason}")
                return {
                    "success": False,
                    "status": "RATE_LIMIT_EXCEEDED",
                    "reason": rate_limit_reason,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Guardrail 3: Generate evaluation report (AI-powered)
            report_content = None
            try:
                from services.report_generator import get_report_generator
                report_generator = get_report_generator()
                
                # Get findings and context from resolution
                findings = resolution.get("findings", {})
                context = resolution.get("context", {})
                
                report_result = await report_generator.generate_evaluation_report(
                    customer, alert_id, resolution, findings, context
                )
                
                if report_result.get("success"):
                    report_content = report_result.get("content", "")
                    logger.info(f"✓ Generated evaluation report for alert {alert_id}")
                else:
                    logger.warning(f"Report generation failed: {report_result.get('error', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Report generation unavailable: {e}")
            
            # Guardrail 4: Create email (with sanitization and report attachment)
            msg = self._create_rfi_email(customer, alert_id, resolution, report_content)
            
            # Guardrail 5: Send email with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Connect to SMTP server
                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.starttls()
                        if self.smtp_user and self.smtp_password:
                            server.login(self.smtp_user, self.smtp_password)
                        
                        # Send email
                        server.send_message(msg)
                    
                    # Log email details for diagnostics
                    logger.info(f"📧 Email details - From: {msg['From']}, To: {msg['To']}, Subject: {msg['Subject']}")
                    logger.info(f"📧 SMTP Config - Host: {self.smtp_host}, Port: {self.smtp_port}, User: {self.smtp_user}")
                    is_gmail = "gmail.com" in self.smtp_host.lower()
                    if is_gmail and self.from_email != self.smtp_user:
                        logger.warning(f"⚠️  FROM_EMAIL ({self.from_email}) != SMTP_USER ({self.smtp_user}). Gmail may reject or mark as spam!")
                    elif "brevo.com" in self.smtp_host.lower() or "sendinblue.com" in self.smtp_host.lower():
                        logger.info(f"✓ Using Brevo SMTP. FROM_EMAIL ({self.from_email}) should be verified in Brevo dashboard.")
                    logger.info(f"💡 Note: SMTP acceptance doesn't guarantee delivery. Check spam folder if email not received.")
                    
                    # Success - update rate limit tracking
                    self.email_rate_limit[customer_id].append(datetime.now())
                    
                    # Mark email as sent in database
                    try:
                        from services.report_generator import get_report_generator
                        report_generator = get_report_generator()
                        report_generator.mark_email_sent(alert_id, customer_email, "RFI_EMAIL")
                    except Exception as e:
                        logger.warning(f"Failed to mark email as sent in database: {e}")
                    
                    # Audit log
                    audit_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "customer_id": customer_id,
                        "customer_email": customer_email,
                        "alert_id": alert_id,
                        "action": "RFI_EMAIL_SENT",
                        "status": "SUCCESS",
                        "from_email": self.from_email,
                        "smtp_user": self.smtp_user
                    }
                    self.email_audit_log.append(audit_entry)
                    
                    logger.info(f"✓ RFI email sent to {customer_email} for alert {alert_id}")
                    
                    return {
                        "success": True,
                        "status": "SENT",
                        "customer_email": customer_email,
                        "alert_id": alert_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except smtplib.SMTPAuthenticationError as e:
                    error_msg = f"SMTP Authentication failed: {e}. Check your SMTP_USER and SMTP_PASSWORD. For Gmail, you may need an App Password instead of your regular password."
                    logger.error(error_msg)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise Exception(error_msg)
                except smtplib.SMTPException as e:
                    error_msg = f"SMTP error: {e}"
                    logger.error(error_msg)
                    if attempt < max_retries - 1:
                        logger.warning(f"SMTP error (attempt {attempt + 1}/{max_retries}): {e}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise Exception(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error sending email: {e}"
                    logger.error(error_msg, exc_info=True)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise Exception(error_msg)
            
        except Exception as e:
            # Audit log for failure
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "customer_id": customer_id,
                "customer_email": customer_email,
                "alert_id": alert_id,
                "action": "RFI_EMAIL_FAILED",
                "status": "ERROR",
                "error": str(e)
            }
            self.email_audit_log.append(audit_entry)
            
            logger.error(f"✗ Failed to send RFI email to {customer_email}: {e}", exc_info=True)
            
            return {
                "success": False,
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_resolution_email(
        self,
        customer: Dict,
        alert_id: str,
        evaluation: Dict
    ) -> Dict:
        """
        Send resolution confirmation email when proof is accepted
        
        Args:
            customer: Customer information
            alert_id: Alert ID
            evaluation: Proof evaluation result
            
        Returns:
            Result dictionary
        """
        customer_id = customer.get("id", "unknown")
        customer_email = customer.get("email", "")
        
        try:
            # Validate email
            is_valid, reason = self._validate_email_address(customer_email)
            if not is_valid:
                return {"success": False, "status": "VALIDATION_FAILED", "reason": reason}
            
            # Create email
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = customer_email
            msg["Subject"] = f"Alert Resolved - {alert_id}"
            
            text_content = f"""
Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},

We are pleased to inform you that your submitted proof has been reviewed and accepted.

Alert ID: {alert_id}
Status: RESOLVED
Date: {datetime.now().strftime('%Y-%m-%d')}

Your explanation has been verified and the alert has been resolved. No further action is required from your side.

Thank you for your cooperation and prompt response.

If you have any questions, please contact our compliance team.

Regards,
{self.from_name}
Compliance Department
            """
            
            html_content = f"""
<html>
<body>
    <p>Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},</p>
    <p>We are pleased to inform you that your submitted proof has been reviewed and accepted.</p>
    <p><strong>Alert ID:</strong> {alert_id}<br>
    <strong>Status:</strong> RESOLVED<br>
    <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
    <p>Your explanation has been verified and the alert has been resolved. No further action is required from your side.</p>
    <p>Thank you for your cooperation and prompt response.</p>
    <p>If you have any questions, please contact our compliance team.</p>
    <p>Regards,<br>
    {self.from_name}<br>
    Compliance Department</p>
</body>
</html>
            """
            
            msg.attach(MIMEText(self._sanitize_content(text_content), "plain"))
            msg.attach(MIMEText(self._sanitize_content(html_content), "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✓ Resolution email sent to {customer_email} for alert {alert_id}")
            return {"success": True, "status": "SENT"}
            
        except Exception as e:
            logger.error(f"Failed to send resolution email: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_branch_escalation_email(
        self,
        customer: Dict,
        alert_id: str,
        evaluation: Dict
    ) -> Dict:
        """
        Send branch escalation email when proof requires verification
        
        Args:
            customer: Customer information
            alert_id: Alert ID
            evaluation: Proof evaluation result
            
        Returns:
            Result dictionary
        """
        customer_id = customer.get("id", "unknown")
        customer_email = customer.get("email", "")
        
        try:
            # Validate email
            is_valid, reason = self._validate_email_address(customer_email)
            if not is_valid:
                return {"success": False, "status": "VALIDATION_FAILED", "reason": reason}
            
            # Create email
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = customer_email
            msg["Subject"] = f"Additional Verification Required - {alert_id}"
            
            text_content = f"""
Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},

Thank you for submitting your explanation regarding alert {alert_id}.

After reviewing your submission, we require additional verification to complete our evaluation.

Alert ID: {alert_id}
Status: Requires Branch Verification
Date: {datetime.now().strftime('%Y-%m-%d')}

NEXT STEPS:

Please choose one of the following options:

1. Visit Your Nearest Branch
   - Bring a valid government-issued ID
   - Bring supporting documents (invoices, receipts, contracts)
   - Ask to speak with a compliance officer
   - Reference Alert ID: {alert_id}

2. Contact Customer Care
   - Phone: 1-800-COMPLIANCE
   - Hours: Monday - Friday, 9:00 AM - 5:00 PM EST
   - Have your Alert ID ready: {alert_id}

Our team will assist you in completing the verification process.

We appreciate your cooperation in this matter.

Regards,
{self.from_name}
Compliance Department
            """
            
            html_content = f"""
<html>
<body>
    <p>Dear {customer.get('first_name', 'Valued')} {customer.get('last_name', 'Customer')},</p>
    <p>Thank you for submitting your explanation regarding alert {alert_id}.</p>
    <p>After reviewing your submission, we require additional verification to complete our evaluation.</p>
    <p><strong>Alert ID:</strong> {alert_id}<br>
    <strong>Status:</strong> Requires Branch Verification<br>
    <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
    <h3>NEXT STEPS:</h3>
    <p>Please choose one of the following options:</p>
    <ol>
        <li><strong>Visit Your Nearest Branch</strong><br>
        - Bring a valid government-issued ID<br>
        - Bring supporting documents (invoices, receipts, contracts)<br>
        - Ask to speak with a compliance officer<br>
        - Reference Alert ID: {alert_id}</li>
        <li><strong>Contact Customer Care</strong><br>
        - Phone: 1-800-COMPLIANCE<br>
        - Hours: Monday - Friday, 9:00 AM - 5:00 PM EST<br>
        - Have your Alert ID ready: {alert_id}</li>
    </ol>
    <p>Our team will assist you in completing the verification process.</p>
    <p>We appreciate your cooperation in this matter.</p>
    <p>Regards,<br>
    {self.from_name}<br>
    Compliance Department</p>
</body>
</html>
            """
            
            msg.attach(MIMEText(self._sanitize_content(text_content), "plain"))
            msg.attach(MIMEText(self._sanitize_content(html_content), "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✓ Branch escalation email sent to {customer_email} for alert {alert_id}")
            return {"success": True, "status": "SENT"}
            
        except Exception as e:
            logger.error(f"Failed to send branch escalation email: {e}")
            return {"success": False, "error": str(e)}
    
    def get_email_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get email audit log"""
        return self.email_audit_log[-limit:]
    
    async def _send_email_simple(self, to_email: str, subject: str, body: str) -> Dict:
        """
        Simple email sending method for notifications
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            Result dictionary
        """
        try:
            # Validate email
            is_valid, reason = self._validate_email_address(to_email)
            if not is_valid:
                return {"success": False, "status": "VALIDATION_FAILED", "reason": reason}
            
            # Create email
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Plain text version
            text_content = self._sanitize_content(body)
            msg.attach(MIMEText(text_content, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✓ Simple email sent to {to_email}: {subject}")
            return {"success": True, "status": "SENT"}
            
        except Exception as e:
            logger.error(f"Failed to send simple email: {e}")
            return {"success": False, "error": str(e)}
    
    def get_rate_limit_status(self, customer_id: str) -> Dict:
        """Get rate limit status for a customer"""
        now = datetime.now()
        customer_emails = self.email_rate_limit.get(customer_id, [])
        
        # Filter to last 24 hours
        recent_emails = [
            ts for ts in customer_emails 
            if now - ts < timedelta(hours=24)
        ]
        
        hourly_count = len([
            ts for ts in recent_emails 
            if now - ts < timedelta(hours=1)
        ])
        
        return {
            "customer_id": customer_id,
            "emails_last_hour": hourly_count,
            "emails_last_24h": len(recent_emails),
            "hourly_limit": self.max_emails_per_hour,
            "daily_limit": self.max_emails_per_day,
            "can_send": hourly_count < self.max_emails_per_hour and len(recent_emails) < self.max_emails_per_day
        }
    
    def get_email_config_diagnostics(self) -> Dict:
        """
        Get email configuration diagnostics to help troubleshoot delivery issues
        
        Returns:
            Dictionary with configuration details and warnings
        """
        diagnostics = {
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_user": self.smtp_user,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "has_password": bool(self.smtp_password),
            "warnings": [],
            "recommendations": []
        }
        
        # Check for common issues
        if not self.smtp_user:
            diagnostics["warnings"].append("SMTP_USER is not set")
            diagnostics["recommendations"].append("Set SMTP_USER in your .env file")
        
        if not self.smtp_password:
            diagnostics["warnings"].append("SMTP_PASSWORD is not set")
            diagnostics["recommendations"].append("Set SMTP_PASSWORD in your .env file (use App Password for Gmail)")
        
        # Check provider-specific requirements
        is_gmail = "gmail.com" in self.smtp_host.lower()
        is_brevo = "brevo.com" in self.smtp_host.lower() or "sendinblue.com" in self.smtp_host.lower()
        
        if is_gmail and self.from_email != self.smtp_user:
            diagnostics["warnings"].append(f"FROM_EMAIL ({self.from_email}) doesn't match SMTP_USER ({self.smtp_user})")
            diagnostics["recommendations"].append(f"Set FROM_EMAIL={self.smtp_user} in your .env file (Gmail requirement)")
        elif is_brevo:
            diagnostics["info"] = f"Using Brevo SMTP. FROM_EMAIL ({self.from_email}) should be a verified sender in your Brevo account."
            if self.from_email != self.smtp_user:
                diagnostics["info"] += " Note: For Brevo, FROM_EMAIL doesn't need to match SMTP_USER, but must be verified in your Brevo dashboard."
        
        if is_gmail and self.from_email != self.smtp_user:
            diagnostics["warnings"].append("Gmail requires FROM_EMAIL to match SMTP_USER")
            diagnostics["recommendations"].append("Gmail will reject or mark emails as spam if FROM_EMAIL doesn't match the authenticated account")
        
        if not diagnostics["warnings"]:
            diagnostics["status"] = "OK"
            diagnostics["message"] = "Email configuration looks good. If emails aren't received, check spam folder."
        else:
            diagnostics["status"] = "WARNING"
            diagnostics["message"] = "Configuration issues detected. Emails may not be delivered."
        
        return diagnostics


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get singleton EmailService instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

