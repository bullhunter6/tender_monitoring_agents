"""
Enhanced Email Notification Service with Database Integration
Updated to use email addresses from database and log all email activities
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime
import logging
import json
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.tender import Tender
from app.repositories.email_settings_repository import EmailSettingsRepository

logger = logging.getLogger(__name__)

class EnhancedEmailService:
    """Enhanced email service using database-stored email addresses and Agent 3 composed content"""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.email_user = settings.EMAIL_USER
        self.email_password = settings.EMAIL_PASSWORD
        self.email_repo = EmailSettingsRepository()
    
    async def send_intelligent_notifications(self, email_compositions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send notifications using Agent 3 composed email content with database-stored emails
        
        Args:
            email_compositions: List of email compositions from Agent 3
            
        Returns:
            Results of email sending operations
        """
        try:
            results = {
                'total_compositions': len(email_compositions),
                'sent_successfully': 0,
                'failed_sends': 0,
                'errors': [],
                'sent_emails': []
            }
            
            if not email_compositions:
                logger.info("No email compositions to send")
                return results
            
            logger.info(f"Sending {len(email_compositions)} intelligent email notifications using database emails...")
            
            # Get database session
            db = SessionLocal()
            try:
                for composition in email_compositions:
                    try:
                        result = await self._send_single_intelligent_email_db(composition, db)
                        
                        if result['success']:
                            results['sent_successfully'] += result.get('emails_sent', 0)
                            results['sent_emails'].extend(result.get('sent_details', []))
                            logger.info(f"Successfully sent intelligent emails for: {composition['tender_data']['title'][:50]}...")
                        else:
                            results['failed_sends'] += 1
                            results['errors'].append({
                                'tender_title': composition['tender_data']['title'][:50] + "...",
                                'error': result['error']
                            })
                            logger.error(f"Failed to send intelligent emails: {result['error']}")
                            
                    except Exception as e:
                        results['failed_sends'] += 1
                        results['errors'].append({
                            'tender_title': composition.get('tender_data', {}).get('title', 'Unknown')[:50] + "...",
                            'error': str(e)
                        })
                        logger.error(f"Error sending intelligent email: {e}")
                
            finally:
                db.close()
            
            logger.info(f"Intelligent email notifications completed: {results['sent_successfully']} emails sent successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in intelligent notifications: {e}")
            return {
                'total_compositions': len(email_compositions),
                'sent_successfully': 0,
                'failed_sends': len(email_compositions),
                'errors': [{'tender_title': 'All', 'error': str(e)}],
                'sent_emails': []
            }
    
    async def _send_single_intelligent_email_db(self, composition: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Send intelligent email to all database-stored recipients for the category"""
        try:
            tender_data = composition['tender_data']
            email_content = composition['email_content']
            team_category = email_content['team_category']
            
            # Get recipient emails from database
            recipient_emails = self.email_repo.get_emails_by_category(db, team_category)
            
            if not recipient_emails:
                error_msg = f"No email addresses configured for {team_category} team in database"
                logger.warning(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'emails_sent': 0
                }
            
            # Check notification preferences
            preferences = self.email_repo.get_notification_preferences(db)
            if not preferences.get('send_for_new_tenders', True):
                logger.info(f"New tender notifications disabled for {team_category} team")
                return {
                    'success': True,
                    'message': 'Notifications disabled',
                    'emails_sent': 0
                }
            
            sent_details = []
            failed_sends = 0
            
            # Send to all recipients
            for recipient_email in recipient_emails:
                try:
                    # Create email message
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = email_content['subject']
                    msg['From'] = self.email_user
                    msg['To'] = recipient_email
                    
                    # Add priority header if high priority
                    if email_content.get('priority') == 'High':
                        msg['X-Priority'] = '1'
                        msg['Importance'] = 'high'
                    
                    # Use Agent 3 composed HTML content
                    html_content = email_content['html_body']
                    
                    # Add email metadata as hidden content for tracking
                    html_content += f"""
                    <!-- Email Metadata -->
                    <!-- Agent Version: {email_content.get('agent_version', '3.0')} -->
                    <!-- Tender ID: {email_content.get('tender_id', 'N/A')} -->
                    <!-- Generated At: {email_content.get('generated_at', 'N/A')} -->
                    <!-- Team Category: {team_category} -->
                    <!-- Priority: {email_content.get('priority', 'Medium')} -->
                    <!-- Recipient: {recipient_email} -->
                    """
                    
                    html_part = MIMEText(html_content, 'html', 'utf-8')
                    msg.attach(html_part)
                    
                    # Send email
                    with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.email_user, self.email_password)
                        server.send_message(msg)
                    
                    # Log successful send
                    self.email_repo.log_email_notification(
                        db=db,
                        recipient_email=recipient_email,
                        email_type='new_tender',
                        team_category=team_category,
                        subject=email_content['subject'],
                        status='sent',
                        tender_id=email_content.get('tender_id')
                    )
                    
                    sent_details.append({
                        'recipient': recipient_email,
                        'subject': email_content['subject'],
                        'priority': email_content.get('priority', 'Medium'),
                        'sent_at': datetime.utcnow().isoformat()
                    })
                    
                    logger.info(f"Email sent successfully to {recipient_email} for {team_category} team")
                    
                except Exception as e:
                    failed_sends += 1
                    error_msg = f"Failed to send to {recipient_email}: {str(e)}"
                    logger.error(error_msg)
                    
                    # Log failed send
                    self.email_repo.log_email_notification(
                        db=db,
                        recipient_email=recipient_email,
                        email_type='new_tender',
                        team_category=team_category,
                        subject=email_content['subject'],
                        status='failed',
                        error_message=str(e),
                        tender_id=email_content.get('tender_id')
                    )
            
            emails_sent = len(sent_details)
            success = emails_sent > 0
            
            return {
                'success': success,
                'emails_sent': emails_sent,
                'failed_sends': failed_sends,
                'sent_details': sent_details,
                'message': f"Sent to {emails_sent}/{len(recipient_emails)} recipients"
            }
            
        except Exception as e:
            error_msg = f"Error in single email send: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'emails_sent': 0
            }
    
    async def send_fallback_notifications(self, tenders: List[Tender], category: str) -> bool:
        """
        Fallback method for sending basic notifications using database emails
        """
        try:
            if not tenders:
                logger.info(f"No tenders to notify for category: {category}")
                return True
            
            # Get database session
            db = SessionLocal()
            try:
                # Get recipient emails from database
                recipient_emails = self.email_repo.get_emails_by_category(db, category)
                
                if not recipient_emails:
                    logger.warning(f"No email addresses configured for {category} team in database")
                    return False
                
                # Check notification preferences
                preferences = self.email_repo.get_notification_preferences(db)
                if not preferences.get('send_for_new_tenders', True):
                    logger.info(f"New tender notifications disabled for {category} team")
                    return True
                
                # Send to all recipients
                subject = f"New {category.upper()} Tenders - {len(tenders)} Found"
                
                for recipient_email in recipient_emails:
                    try:
                        # Create email
                        msg = MIMEMultipart('alternative')
                        msg['Subject'] = subject
                        msg['From'] = self.email_user
                        msg['To'] = recipient_email
                        
                        # Create basic HTML content (fallback)
                        html_content = self._create_fallback_tender_email(tenders, category)
                        html_part = MIMEText(html_content, 'html', 'utf-8')
                        msg.attach(html_part)
                        
                        # Send email
                        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                            server.starttls()
                            server.login(self.email_user, self.email_password)
                            server.send_message(msg)
                        
                        # Log successful send
                        self.email_repo.log_email_notification(
                            db=db,
                            recipient_email=recipient_email,
                            email_type='fallback_notification',
                            team_category=category,
                            subject=subject,
                            status='sent'
                        )
                        
                        logger.info(f"Fallback email sent successfully to {recipient_email}")
                        
                    except Exception as e:
                        error_msg = f"Failed to send fallback email to {recipient_email}: {str(e)}"
                        logger.error(error_msg)
                        
                        # Log failed send
                        self.email_repo.log_email_notification(
                            db=db,
                            recipient_email=recipient_email,
                            email_type='fallback_notification',
                            team_category=category,
                            subject=subject,
                            status='failed',
                            error_message=str(e)
                        )
                
                logger.info(f"Successfully sent fallback email notifications to {len(recipient_emails)} recipients for {len(tenders)} {category} tenders")
                return True
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Failed to send fallback email notifications: {e}")
            return False
    
    def _create_fallback_tender_email(self, tenders: List[Tender], category: str) -> str:
        """Create basic HTML email content for tenders (fallback method)"""
        team_name = "ESG Team" if category == "esg" else "Credit Rating Team"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .tender {{ border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }}
                .tender-title {{ font-size: 18px; font-weight: bold; color: #333; }}
                .tender-category {{ background-color: #007bff; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
                .tender-date {{ color: #666; font-size: 14px; }}
                .tender-description {{ margin: 10px 0; line-height: 1.5; }}
                .tender-link {{ color: #007bff; text-decoration: none; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>New Tender Notifications - {team_name}</h2>
                <p>We found {len(tenders)} new tender(s) that match your criteria.</p>
                <p><em>Enhanced AI email composition was not available. Using basic notification format.</em></p>
            </div>
        """
        
        for tender in tenders:
            tender_date = tender.tender_date.strftime("%Y-%m-%d") if tender.tender_date else "Date not specified"
            
            html_content += f"""
            <div class="tender">
                <div class="tender-title">{tender.title}</div>
                <div style="margin: 5px 0;">
                    <span class="tender-category">{tender.category.upper()}</span>
                    <span class="tender-date">Date: {tender_date}</span>
                </div>
                <div class="tender-description">
                    {tender.description[:500] if tender.description else 'No description available'}{'...' if tender.description and len(tender.description) > 500 else ''}
                </div>
                <div>
                    <a href="{tender.url}" class="tender-link">View Full Tender →</a>
                </div>
            </div>
            """
        
        html_content += """
            <div class="footer">
                <p>This is an automated notification from the Tender Monitoring System using database-stored email addresses.</p>
                <p>If you no longer wish to receive these notifications, please contact your administrator.</p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    async def test_email_connection(self) -> Dict[str, Any]:
        """Test email connection and configuration"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
            
            return {
                "status": "success",
                "message": "Email connection successful"
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Email connection failed: {str(e)}"
            }
    
    async def send_test_intelligent_email(self, recipient: str, test_tender_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a test email using Agent 3 composition and log to database"""
        try:
            from datetime import datetime
            
            # Create test tender data if not provided
            if not test_tender_data:
                test_tender_data = {
                    'title': 'Test ESG Consulting Services Tender',
                    'url': 'https://example.com/test-tender',
                    'category': 'esg',
                    'description': 'Test tender for ESG consulting and sustainability reporting services',
                    'matched_keywords': ['environmental', 'sustainability', 'ESG']
                }
            
            # Create test detailed info
            test_detailed_info = {
                'detailed_title': 'Comprehensive ESG Consulting and Sustainability Reporting Services',
                'detailed_description': 'Full-service ESG consulting including materiality assessment, stakeholder engagement, and comprehensive sustainability reporting aligned with international standards.',
                'requirements': 'Experience in ESG consulting, knowledge of SASB/GRI standards, demonstrated track record',
                'deadline': '2025-07-15',
                'tender_value': '50,000 - 100,000 USD',
                'contact_info': {
                    'organization': 'Test Organization',
                    'contact_person': 'Test Contact',
                    'email': 'test@example.com',
                    'phone': '+1-555-0123'
                }
            }
            
            # Use Agent 3 to compose test email
            from app.agents.agent3 import EmailComposerAgent
            agent3 = EmailComposerAgent()
            
            email_content = await agent3.compose_tender_email(
                tender_data=test_tender_data,
                detailed_info=test_detailed_info,
                team_category=test_tender_data['category']
            )
            
            # Create test email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[TEST] {email_content['subject']}"
            msg['From'] = self.email_user
            msg['To'] = recipient
            
            # Add test disclaimer to HTML content
            test_html = f"""
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 5px;">
                <strong>🧪 TEST EMAIL</strong> - This is a test of the Agent 3 intelligent email composition system using database configuration.
            </div>
            {email_content['html_body']}
            <div style="background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; font-size: 12px; color: #666;">
                <strong>Test Metadata:</strong><br>
                Generated by: Agent 3 Email Composer<br>
                Test Time: {datetime.utcnow().isoformat()}<br>
                System: Tender Monitoring v3.0 with Database Integration
            </div>
            """
            
            html_part = MIMEText(test_html, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            # Log to database
            db = SessionLocal()
            try:
                self.email_repo.log_email_notification(
                    db=db,
                    recipient_email=recipient,
                    email_type='test',
                    team_category=test_tender_data['category'],
                    subject=f"[TEST] {email_content['subject']}",
                    status='sent'
                )
            finally:
                db.close()
            
            return {
                'status': 'success',
                'message': f'Test intelligent email sent successfully to {recipient} using database configuration',
                'email_content_preview': {
                    'subject': email_content['subject'],
                    'priority': email_content['priority'],
                    'summary': email_content.get('summary', 'Test email summary')
                }
            }
            
        except Exception as e:
            # Log failed test to database
            db = SessionLocal()
            try:
                self.email_repo.log_email_notification(
                    db=db,
                    recipient_email=recipient,
                    email_type='test',
                    team_category='test',
                    subject='Test Email (Failed)',
                    status='failed',
                    error_message=str(e)
                )
            finally:
                db.close()
                
            return {
                'status': 'failed',
                'message': f'Failed to send test intelligent email: {str(e)}'
            }

EmailService = EnhancedEmailService