"""
Report Generator Service
Generates AI-powered evaluation reports for customers
Includes guidance and next steps based on alert resolution
"""

import logging
import os
from typing import Dict, Optional
from datetime import datetime
import json
from services.llm_service import get_llm_service
from services.report_schemas import EvaluationReport, NextSteps
from database.neo4j_connector import Neo4jConnector

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates AI-powered evaluation reports
    
    Features:
    - LLM-generated report content
    - Personalized guidance
    - Next steps recommendations
    - Professional formatting
    - PDF generation (optional)
    """
    
    def __init__(self):
        """Initialize Report Generator"""
        self.enabled = os.getenv("REPORT_GENERATION_ENABLED", "true").lower() == "true"
        self.llm_service = get_llm_service() if self.enabled else None
        self.use_structured_output = os.getenv("USE_STRUCTURED_OUTPUT", "true").lower() == "true"
        self.db = Neo4jConnector()
        
        logger.info(f"✓ Report Generator initialized (enabled: {self.enabled}, structured_output: {self.use_structured_output})")
    
    async def generate_evaluation_report(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        findings: Dict,
        context: Dict,
        force_regenerate: bool = False
    ) -> Dict:
        """
        Generate comprehensive evaluation report using AI
        Checks database first to avoid regenerating existing reports
        
        Args:
            customer: Customer information
            alert_id: Alert ID
            resolution: Resolution details (recommendation, rationale, confidence)
            findings: Investigation findings
            context: Customer context
            force_regenerate: If True, regenerate even if report exists
            
        Returns:
            Report dictionary with content and metadata
        """
        if not self.enabled:
            return {
                "success": False,
                "reason": "Report generation disabled"
            }
        
        try:
            # Check if report already exists in database
            if not force_regenerate:
                existing_report = self.get_stored_report(alert_id)
                if existing_report:
                    logger.info(f"✓ Retrieved existing report for alert {alert_id} from database")
                    return existing_report
            
            # Generate report content using LLM
            report_content = await self._generate_report_content(
                customer, alert_id, resolution, findings, context
            )
            
            # Generate next steps guidance
            next_steps = await self._generate_next_steps(
                resolution, findings, context
            )
            
            # Format as document
            formatted_report = self._format_report(
                customer, alert_id, resolution, report_content, next_steps
            )
            
            # Generate metadata
            metadata = {
                "alert_id": alert_id,
                "customer_id": customer.get("id"),
                "customer_name": customer.get("name"),
                "generated_at": datetime.now().isoformat(),
                "recommendation": resolution.get("recommendation"),
                "confidence": resolution.get("confidence", 0),
                "report_type": "EVALUATION_REPORT"
            }
            
            # Store report in database (store both formatted and raw content)
            self._store_report(alert_id, formatted_report, metadata, next_steps, raw_content=report_content)
            
            logger.info(f"✓ Generated and stored evaluation report for alert {alert_id}")
            
            # Generate HTML version for email
            html_report = self._format_report_html(
                customer, alert_id, resolution, report_content, next_steps
            )
            
            return {
                "success": True,
                "content": formatted_report,
                "html_content": html_report,  # Add HTML version
                "metadata": metadata,
                "next_steps": next_steps,
                "format": "text"  # Can be extended to PDF/HTML
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_report_content(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        findings: Dict,
        context: Dict
    ) -> str:
        """Generate report content using LLM with structured output"""
        
        if not self.llm_service or not self.llm_service.is_enabled():
            # Fallback to template-based report
            return self._generate_template_report(customer, alert_id, resolution, findings, context)
        
        try:
            # Use OpenAI client directly for structured output
            if not self.use_structured_output:
                raise ValueError("Structured output disabled, using fallback")
            
            from openai import OpenAI
            
            client = OpenAI(api_key=self.llm_service.openai_api_key)
            
            # Use a model that supports structured outputs
            model = self.llm_service.model_name
            if model not in ["gpt-4o", "gpt-4o-2024-08-06", "gpt-4-turbo"]:
                # Fallback to gpt-4o if model doesn't support structured outputs
                logger.warning(f"Model {model} may not support structured outputs, using gpt-4o")
                model = "gpt-4o"
            
            prompt = f"""Generate a professional, customer-friendly evaluation report for a banking compliance alert.

Customer Information:
- Name: {customer.get('name', 'Customer')}
- Customer ID: {customer.get('id', 'N/A')}

Alert Details:
- Alert ID: {alert_id}
- Scenario: {findings.get('scenario', 'Unknown')}
- Date: {datetime.now().strftime('%Y-%m-%d')}

Investigation Findings:
{json.dumps(findings, indent=2)}

Resolution:
- Recommendation: {resolution.get('recommendation', 'N/A')}
- Rationale: {resolution.get('rationale', 'N/A')}
- Confidence: {resolution.get('confidence', 0):.1%}

Customer Context:
- KYC Risk Level: {context.get('kyc_risk', 'N/A')}
- Occupation: {context.get('occupation', 'N/A')}

Generate a professional report that:
1. Explains what was investigated in clear, non-technical language
2. Summarizes the findings in customer-friendly terms
3. Explains the resolution decision
4. Is professional but empathetic
5. Avoids technical jargon
6. Is approximately 300-400 words total
7. Write directly without placeholders or markdown formatting
8. Use clear, natural language

The report should be structured with:
- Introduction: Brief greeting and context
- Investigation Summary: What was investigated
- Findings Overview: Key findings from the investigation
- Resolution Explanation: Why this decision was made
- Conclusion: Closing statement"""
            
            # Use structured output with Pydantic model
            # Try beta API first, fallback to JSON schema if needed
            try:
                # Check if beta.chat.completions.parse exists
                if hasattr(client, 'beta'):
                    beta_obj = client.beta
                    if hasattr(beta_obj, 'chat') and hasattr(beta_obj.chat, 'completions'):
                        response = beta_obj.chat.completions.parse(
                            model=model,
                            messages=[
                                {"role": "system", "content": "You are a professional compliance analyst writing customer-facing reports. Write in plain text, no markdown, no placeholders."},
                                {"role": "user", "content": prompt}
                            ],
                            response_format=EvaluationReport,
                            temperature=self.llm_service.temperature,
                            max_tokens=self.llm_service.max_tokens
                        )
                        # Access parsed data
                        if hasattr(response, 'choices') and len(response.choices) > 0:
                            if hasattr(response.choices[0].message, 'parsed'):
                                report_data: EvaluationReport = response.choices[0].message.parsed
                            else:
                                raise ValueError("Parsed data not found in response")
                        else:
                            raise ValueError("No choices in response")
                    else:
                        raise AttributeError("beta.chat.completions.parse not available")
                else:
                    raise AttributeError("beta API not available")
            except (AttributeError, ValueError) as e:
                logger.warning(f"Structured output API failed: {e}, using JSON schema fallback")
                # Fallback: use regular chat.completions with JSON schema
                json_schema = EvaluationReport.model_json_schema()
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional compliance analyst. Return JSON matching the schema."},
                        {"role": "user", "content": f"{prompt}\n\nReturn the response as JSON matching this schema: {json.dumps(json_schema)}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.llm_service.temperature,
                    max_tokens=self.llm_service.max_tokens
                )
                # Parse JSON response manually
                json_content = response.choices[0].message.content
                parsed_json = json.loads(json_content)
                # Create EvaluationReport from dict
                report_data = EvaluationReport(**parsed_json)
            
            # Format the structured report into readable text
            report_content = f"""{report_data.introduction}

{report_data.investigation_summary}

{report_data.findings_overview}

{report_data.resolution_explanation}

{report_data.conclusion}"""
            
            logger.info("✓ Generated AI-powered report content with structured output")
            return report_content.strip()
            
        except Exception as e:
            logger.warning(f"Structured output generation failed: {e}, trying fallback")
            # Fallback to LangChain if structured output fails
            try:
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage
                except ImportError:
                    from langchain.schema import HumanMessage, SystemMessage
                
                prompt = f"""Generate a professional, customer-friendly evaluation report for a banking compliance alert.

Customer Information:
- Name: {customer.get('name', 'Customer')}
- Customer ID: {customer.get('id', 'N/A')}

Alert Details:
- Alert ID: {alert_id}
- Scenario: {findings.get('scenario', 'Unknown')}
- Date: {datetime.now().strftime('%Y-%m-%d')}

Investigation Findings:
{json.dumps(findings, indent=2)}

Resolution:
- Recommendation: {resolution.get('recommendation', 'N/A')}
- Rationale: {resolution.get('rationale', 'N/A')}
- Confidence: {resolution.get('confidence', 0):.1%}

Customer Context:
- KYC Risk Level: {context.get('kyc_risk', 'N/A')}
- Occupation: {context.get('occupation', 'N/A')}

Generate a professional report in plain text, no markdown, no placeholders."""
                
                messages = [
                    SystemMessage(content="You are a professional compliance analyst. Write in plain text, no markdown, no placeholders."),
                    HumanMessage(content=prompt)
                ]
                
                response = self.llm_service.chat_model.invoke(messages)
                report_content = response.content.strip()
                
                logger.info("✓ Generated AI-powered report content (fallback)")
                return report_content
            except Exception as e2:
                logger.warning(f"LLM report generation failed: {e2}, using template")
                return self._generate_template_report(customer, alert_id, resolution, findings, context)
    
    async def _generate_next_steps(
        self,
        resolution: Dict,
        findings: Dict,
        context: Dict
    ) -> str:
        """Generate next steps guidance using LLM with structured output"""
        
        if not self.llm_service or not self.llm_service.is_enabled():
            return self._generate_template_next_steps(resolution)
        
        try:
            # Use OpenAI client directly for structured output
            if not self.use_structured_output:
                raise ValueError("Structured output disabled, using fallback")
            
            from openai import OpenAI
            
            client = OpenAI(api_key=self.llm_service.openai_api_key)
            
            # Use a model that supports structured outputs
            model = self.llm_service.model_name
            if model not in ["gpt-4o", "gpt-4o-2024-08-06", "gpt-4-turbo"]:
                # Fallback to gpt-4o if model doesn't support structured outputs
                logger.warning(f"Model {model} may not support structured outputs, using gpt-4o")
                model = "gpt-4o"
            
            prompt = f"""Based on the following banking compliance resolution, provide clear, actionable next steps for the customer.

Resolution:
- Recommendation: {resolution.get('recommendation', 'N/A')}
- Rationale: {resolution.get('rationale', 'N/A')}

Scenario: {findings.get('scenario', 'Unknown')}

Provide structured next steps with:
1. Immediate actions the customer should take (if any)
2. Documents or information they may need to provide
3. Timeline expectations
4. Contact information for questions
5. What happens next in the process

Keep it concise and customer-friendly."""
            
            # Use structured output with Pydantic model
            # Try beta API first, fallback to JSON schema if needed
            try:
                # Check if beta.chat.completions.parse exists
                if hasattr(client, 'beta'):
                    beta_obj = client.beta
                    if hasattr(beta_obj, 'chat') and hasattr(beta_obj.chat, 'completions'):
                        response = beta_obj.chat.completions.parse(
                            model=model,
                            messages=[
                                {"role": "system", "content": "You are a customer service representative providing clear guidance."},
                                {"role": "user", "content": prompt}
                            ],
                            response_format=NextSteps,
                            temperature=self.llm_service.temperature,
                            max_tokens=500
                        )
                        # Access parsed data
                        if hasattr(response, 'choices') and len(response.choices) > 0:
                            if hasattr(response.choices[0].message, 'parsed'):
                                next_steps_data: NextSteps = response.choices[0].message.parsed
                            else:
                                raise ValueError("Parsed data not found in response")
                        else:
                            raise ValueError("No choices in response")
                    else:
                        raise AttributeError("beta.chat.completions.parse not available")
                else:
                    raise AttributeError("beta API not available")
            except (AttributeError, ValueError) as e:
                logger.warning(f"Structured output API failed: {e}, using JSON schema fallback")
                # Fallback: use regular chat.completions with JSON schema
                json_schema = NextSteps.model_json_schema()
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a customer service representative. Return JSON matching the schema."},
                        {"role": "user", "content": f"{prompt}\n\nReturn the response as JSON matching this schema: {json.dumps(json_schema)}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.llm_service.temperature,
                    max_tokens=500
                )
                # Parse JSON response manually
                json_content = response.choices[0].message.content
                parsed_json = json.loads(json_content)
                # Create NextSteps from dict
                next_steps_data = NextSteps(**parsed_json)
            
            # Format the structured next steps into readable text
            steps_list = []
            
            if next_steps_data.immediate_actions:
                steps_list.append("1. Immediate actions:")
                for i, action in enumerate(next_steps_data.immediate_actions, 1):
                    steps_list.append(f"   {i}. {action}")
            
            if next_steps_data.required_documents:
                steps_list.append("\n2. Documents/information:")
                for i, doc in enumerate(next_steps_data.required_documents, 1):
                    steps_list.append(f"   {i}. {doc}")
            
            if next_steps_data.timeline:
                steps_list.append(f"\n3. Timeline: {next_steps_data.timeline}")
            
            if next_steps_data.contact_info:
                steps_list.append(f"\n4. Contact information: {next_steps_data.contact_info}")
            
            if next_steps_data.what_happens_next:
                steps_list.append(f"\n5. What happens next: {next_steps_data.what_happens_next}")
            
            next_steps = "\n".join(steps_list)
            
            logger.info("✓ Generated AI-powered next steps with structured output")
            return next_steps.strip()
            
        except Exception as e:
            logger.warning(f"Structured next steps generation failed: {e}, trying fallback")
            # Fallback to LangChain if structured output fails
            try:
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage
                except ImportError:
                    from langchain.schema import HumanMessage, SystemMessage
                
                prompt = f"""Based on the following banking compliance resolution, provide clear, actionable next steps for the customer.

Resolution:
- Recommendation: {resolution.get('recommendation', 'N/A')}
- Rationale: {resolution.get('rationale', 'N/A')}

Scenario: {findings.get('scenario', 'Unknown')}

Provide clear, actionable next steps."""
                
                messages = [
                    SystemMessage(content="You are a customer service representative providing clear guidance."),
                    HumanMessage(content=prompt)
                ]
                
                response = self.llm_service.chat_model.invoke(messages)
                next_steps = response.content.strip()
                
                logger.info("✓ Generated AI-powered next steps (fallback)")
                return next_steps
            except Exception as e2:
                logger.warning(f"LLM next steps generation failed: {e2}, using template")
                return self._generate_template_next_steps(resolution)
    
    def _format_report(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        report_content: str,
        next_steps: str
    ) -> str:
        """Format report as a complete document (plain text)"""
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TRANSACTION EVALUATION REPORT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Report Date: {datetime.now().strftime('%B %d, %Y')}
Alert ID: {alert_id}
Customer: {customer.get('name', 'Customer')}
Customer ID: {customer.get('id', 'N/A')}

───────────────────────────────────────────────────────────────────────────────
EXECUTIVE SUMMARY
───────────────────────────────────────────────────────────────────────────────

Resolution: {resolution.get('recommendation', 'N/A')}
Confidence Level: {resolution.get('confidence', 0):.1%}

This report summarizes the evaluation of recent account activity and provides 
guidance on next steps.

───────────────────────────────────────────────────────────────────────────────
EVALUATION DETAILS
───────────────────────────────────────────────────────────────────────────────

{report_content}

───────────────────────────────────────────────────────────────────────────────
NEXT STEPS
───────────────────────────────────────────────────────────────────────────────

{next_steps}

───────────────────────────────────────────────────────────────────────────────
CONTACT INFORMATION
───────────────────────────────────────────────────────────────────────────────

If you have questions or need assistance, please contact our Compliance Team:

Email: compliance@bank.com
Phone: 1-800-COMPLIANCE
Hours: Monday - Friday, 9:00 AM - 5:00 PM EST

───────────────────────────────────────────────────────────────────────────────
IMPORTANT NOTES
───────────────────────────────────────────────────────────────────────────────

• This report is for your records
• Please retain this document for your files
• If you have concerns, contact us immediately
• All information is confidential and secure

───────────────────────────────────────────────────────────────────────────────

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Report ID: RPT-{alert_id}

╚══════════════════════════════════════════════════════════════════════════════╝
        """
        
        return report.strip()
    
    def _format_report_html(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        report_content: str,
        next_steps: str
    ) -> str:
        """Format report as a beautiful HTML document for email"""
        
        # Get recommendation color
        recommendation = resolution.get('recommendation', 'N/A')
        rec_color = {
            'ESCALATE': '#dc2626',  # red
            'RFI': '#2563eb',       # blue
            'CLOSE': '#16a34a',     # green
            'BLOCK': '#dc2626',     # red
            'IVR': '#7c3aed'        # purple
        }.get(recommendation, '#6b7280')  # gray default
        
        # Format report content with proper HTML
        # Escape HTML special characters first, then convert newlines
        import html
        escaped_content = html.escape(report_content)
        formatted_content = escaped_content.replace('\n', '<br>')
        
        # Format next steps
        if next_steps:
            escaped_steps = html.escape(next_steps)
            formatted_next_steps = escaped_steps.replace('\n', '<br>')
        else:
            formatted_next_steps = ''
        
        html_report = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transaction Evaluation Report - {alert_id}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f3f4f6; padding: 20px;">
        <tr>
            <td align="center">
                <table role="presentation" style="max-width: 700px; width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                Transaction Evaluation Report
                            </h1>
                            <p style="margin: 10px 0 0 0; color: #e0e7ff; font-size: 14px;">
                                Professional Compliance Documentation
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Report Info -->
                    <tr>
                        <td style="padding: 30px; background-color: #f9fafb; border-bottom: 1px solid #e5e7eb;">
                            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Report Date</strong><br>
                                        <span style="color: #111827; font-size: 15px; font-weight: 600;">{datetime.now().strftime('%B %d, %Y')}</span>
                                    </td>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Alert ID</strong><br>
                                        <span style="color: #111827; font-size: 15px; font-weight: 600;">{alert_id}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Customer</strong><br>
                                        <span style="color: #111827; font-size: 15px; font-weight: 600;">{customer.get('name', 'Customer')}</span>
                                    </td>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Customer ID</strong><br>
                                        <span style="color: #111827; font-size: 15px; font-weight: 600;">{customer.get('id', 'N/A')}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Executive Summary -->
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 20px; font-weight: 700; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
                                Executive Summary
                            </h2>
                            <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 4px solid {rec_color}; padding: 20px; border-radius: 6px; margin-bottom: 20px;">
                                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 8px 0;">
                                            <strong style="color: #4b5563; font-size: 13px; display: block; margin-bottom: 4px;">Resolution</strong>
                                            <span style="color: {rec_color}; font-size: 24px; font-weight: 700;">{recommendation}</span>
                                        </td>
                                        <td style="padding: 8px 0; text-align: right;">
                                            <strong style="color: #4b5563; font-size: 13px; display: block; margin-bottom: 4px;">Confidence Level</strong>
                                            <span style="color: #111827; font-size: 24px; font-weight: 700;">{resolution.get('confidence', 0):.1%}</span>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
                                This report summarizes the evaluation of recent account activity and provides guidance on next steps.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Evaluation Details -->
                    <tr>
                        <td style="padding: 30px; background-color: #f9fafb;">
                            <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 20px; font-weight: 700; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
                                Evaluation Details
                            </h2>
                            <div style="color: #374151; font-size: 15px; line-height: 1.8; background-color: #ffffff; padding: 20px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                {formatted_content}
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Next Steps -->
                    {f'''
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 20px; font-weight: 700; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
                                Next Steps
                            </h2>
                            <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-left: 4px solid #16a34a; padding: 20px; border-radius: 6px;">
                                <div style="color: #166534; font-size: 15px; line-height: 1.8; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; max-width: 100%;">
                                    {formatted_next_steps}
                                </div>
                                <p style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #86efac; color: #166534; font-size: 13px; font-style: italic;">
                                    📎 A detailed Next Steps document has been attached to this email for your reference.
                                </p>
                            </div>
                        </td>
                    </tr>
                    ''' if formatted_next_steps else ''}
                    
                    <!-- Contact Information -->
                    <tr>
                        <td style="padding: 30px; background-color: #f9fafb;">
                            <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 20px; font-weight: 700; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
                                Contact Information
                            </h2>
                            <div style="background-color: #ffffff; padding: 20px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 15px;">
                                    If you have questions or need assistance, please contact our Compliance Team:
                                </p>
                                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 8px 0; color: #111827; font-size: 15px;">
                                            <strong>Email:</strong> <a href="mailto:compliance@bank.com" style="color: #2563eb; text-decoration: none;">compliance@bank.com</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #111827; font-size: 15px;">
                                            <strong>Phone:</strong> 1-800-COMPLIANCE
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #111827; font-size: 15px;">
                                            <strong>Hours:</strong> Monday - Friday, 9:00 AM - 5:00 PM EST
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; background-color: #1f2937; text-align: center;">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px; line-height: 1.6;">
                                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                                Report ID: RPT-{alert_id}<br><br>
                                <span style="color: #6b7280;">This report is confidential and intended solely for the recipient.</span>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        return html_report.strip()
    
    def _generate_template_report(
        self,
        customer: Dict,
        alert_id: str,
        resolution: Dict,
        findings: Dict,
        context: Dict
    ) -> str:
        """Generate template-based report (fallback when LLM unavailable)"""
        
        scenario = findings.get('scenario', 'Unknown')
        recommendation = resolution.get('recommendation', 'N/A')
        
        report = f"""
Our compliance team has completed an evaluation of recent activity on your account.

INVESTIGATION SUMMARY:
We reviewed your account activity related to alert {alert_id}. Our automated 
compliance system analyzed the transaction patterns and customer profile to 
determine the appropriate course of action.

FINDINGS:
The investigation identified {scenario.replace('_', ' ').lower()} patterns in your 
account activity. After thorough analysis, our system has determined that 
{resolution.get('rationale', 'further review is needed')}.

RESOLUTION:
Based on our evaluation, the recommended action is: {recommendation}.

This decision was made with {resolution.get('confidence', 0):.1%} confidence 
based on the available information and regulatory guidelines.
        """
        
        return report.strip()
    
    def _generate_template_next_steps(self, resolution: Dict) -> str:
        """Generate template-based next steps (fallback)"""
        
        recommendation = resolution.get('recommendation', 'RFI')
        
        steps_map = {
            'RFI': """
1. Review the information requested in the email
2. Gather any supporting documents
3. Respond within 5 business days
4. Contact us if you need clarification
            """,
            'ESCALATE': """
1. No immediate action required from you
2. Our team will review the case
3. You may be contacted for additional information
4. We will notify you of any decisions
            """,
            'IVR': """
1. Answer the automated call when it arrives
2. Have your account information ready
3. Follow the voice prompts
4. Contact us if you miss the call
            """,
            'BLOCK': """
1. Contact our compliance team immediately
2. Do not attempt additional transactions
3. We will provide further instructions
4. Your account access will be restored after review
            """,
            'CLOSE': """
1. No action required
2. The alert has been resolved
3. Continue normal account activity
4. Contact us if you have questions
            """
        }
        
        return steps_map.get(recommendation, steps_map['RFI']).strip()
    
    def _store_report(self, alert_id: str, content: str, metadata: Dict, next_steps: str, raw_content: Optional[str] = None):
        """Store report in Neo4j database"""
        try:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})
            MERGE (r:Report {alert_id: $alert_id})
            SET r.content = $content,
                r.metadata = $metadata,
                r.next_steps = $next_steps,
                r.raw_content = $raw_content,
                r.generated_at = datetime(),
                r.updated_at = datetime()
            MERGE (a)-[:HAS_REPORT]->(r)
            RETURN r
            """
            
            self.db.execute_write(query, {
                "alert_id": alert_id,
                "content": content,
                "metadata": json.dumps(metadata),
                "next_steps": next_steps,
                "raw_content": raw_content or ""
            })
            
            logger.debug(f"✓ Stored report for alert {alert_id} in database")
        except Exception as e:
            logger.warning(f"Failed to store report in database: {e}")
            # Don't fail report generation if storage fails
    
    def mark_email_sent(self, alert_id: str, email_address: str, email_type: str = "REPORT_EMAIL") -> bool:
        """
        Mark report email as sent in database
        
        Args:
            alert_id: Alert ID
            email_address: Email address the report was sent to
            email_type: Type of email (REPORT_EMAIL, RFI_EMAIL, etc.)
            
        Returns:
            True if successfully marked
        """
        try:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})-[:HAS_REPORT]->(r:Report)
            SET r.email_sent = true,
                r.email_sent_at = datetime(),
                r.email_sent_to = $email_address,
                r.email_type = $email_type,
                r.updated_at = datetime()
            RETURN r
            """
            
            self.db.execute_write(query, {
                "alert_id": alert_id,
                "email_address": email_address,
                "email_type": email_type
            })
            
            logger.info(f"✓ Marked email as sent for alert {alert_id} to {email_address}")
            return True
        except Exception as e:
            logger.warning(f"Failed to mark email as sent in database: {e}")
            return False
    
    def get_email_status(self, alert_id: str) -> Optional[Dict]:
        """
        Get email sent status for a report
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Dictionary with email status or None if report doesn't exist
        """
        try:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})-[:HAS_REPORT]->(r:Report)
            RETURN r.email_sent as email_sent,
                   r.email_sent_at as email_sent_at,
                   r.email_sent_to as email_sent_to,
                   r.email_type as email_type
            """
            
            results = self.db.execute_query(query, {"alert_id": alert_id})
            
            if results and results[0].get("email_sent") is not None:
                return {
                    "email_sent": results[0].get("email_sent", False),
                    "email_sent_at": results[0].get("email_sent_at"),
                    "email_sent_to": results[0].get("email_sent_to"),
                    "email_type": results[0].get("email_type", "REPORT_EMAIL")
                }
        except Exception as e:
            logger.debug(f"Could not retrieve email status: {e}")
        
        return None
    
    def get_stored_report(self, alert_id: str) -> Optional[Dict]:
        """Retrieve stored report from Neo4j database"""
        try:
            query = """
            MATCH (a:Alert {alert_id: $alert_id})-[:HAS_REPORT]->(r:Report)
            RETURN r.content as content, 
                   r.metadata as metadata, 
                   r.next_steps as next_steps,
                   r.raw_content as raw_content,
                   r.email_sent as email_sent,
                   r.email_sent_at as email_sent_at,
                   r.email_sent_to as email_sent_to,
                   r.email_type as email_type
            ORDER BY r.updated_at DESC
            LIMIT 1
            """
            
            results = self.db.execute_query(query, {"alert_id": alert_id})
            
            if results and results[0].get("content"):
                metadata_str = results[0].get("metadata", "{}")
                try:
                    metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                except:
                    metadata = {}
                
                stored_data = {
                    "success": True,
                    "content": results[0].get("content", ""),
                    "metadata": metadata,
                    "next_steps": results[0].get("next_steps", ""),
                    "format": "text",
                    "email_sent": results[0].get("email_sent", False),
                    "email_sent_at": results[0].get("email_sent_at"),
                    "email_sent_to": results[0].get("email_sent_to"),
                    "email_type": results[0].get("email_type")
                }
                
                # Add raw content if available (for HTML generation)
                raw_content = results[0].get("raw_content")
                if raw_content:
                    stored_data["raw_content"] = raw_content
                    # Generate HTML version from raw content
                    try:
                        html_report = self._format_report_html(
                            {"name": metadata.get("customer_name", "Customer"), "id": metadata.get("customer_id", "N/A")},
                            alert_id,
                            {"recommendation": metadata.get("recommendation", "RFI"), "confidence": metadata.get("confidence", 0)},
                            raw_content,
                            stored_data["next_steps"]
                        )
                        stored_data["html_content"] = html_report
                    except Exception as e:
                        logger.debug(f"Could not generate HTML from stored report: {e}")
                
                return stored_data
        except Exception as e:
            logger.debug(f"Could not retrieve stored report: {e}")
        
        return None
    
    def generate_pdf(self, report_content: str, output_path: str) -> bool:
        """
        Generate PDF version of report (optional - requires reportlab)
        
        Args:
            report_content: Report text content
            output_path: Path to save PDF
            
        Returns:
            True if successful
        """
        try:
            # Optional: Install reportlab for PDF generation
            # pip install reportlab
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add content
            for line in report_content.split('\n'):
                if line.strip():
                    story.append(Paragraph(line, styles['Normal']))
                    story.append(Spacer(1, 12))
            
            doc.build(story)
            logger.info(f"✓ Generated PDF report: {output_path}")
            return True
            
        except ImportError:
            logger.warning("reportlab not installed - PDF generation disabled")
            return False
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return False


# Singleton instance
_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Get singleton ReportGenerator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator

