# File: app/utils/email_sender.py
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.email_log import EmailLog

logger = logging.getLogger(__name__)

class EmailSender:
    """Send email notifications with logging"""
    
    @classmethod
    def log_email(cls, email_type: str, recipient_email: str, recipient_name: str, 
                  subject: str, product_id: int = None, incubatee_id: int = None,
                  stock_amount: int = None, threshold: int = None, 
                  status: str = 'sent', error_message: str = None,
                  interval_minutes: int = 5) -> EmailLog:
        """Log email sending attempt"""
        try:
            log = EmailLog(
                email_type=email_type,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                product_id=product_id,
                incubatee_id=incubatee_id,
                stock_amount=stock_amount,
                threshold=threshold,
                status=status,
                error_message=error_message,
                interval_minutes=interval_minutes,
                next_scheduled=datetime.utcnow() + timedelta(minutes=interval_minutes) if status == 'sent' else None
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to log email: {str(e)}")
            return None
    
    @classmethod
    def should_send_email(cls, incubatee_id: int, product_id: int, interval_minutes: int = 5) -> bool:
        """Check if we should send email based on interval"""
        try:
            # Check last sent email for this incubatee and product
            last_email = EmailLog.query.filter_by(
                incubatee_id=incubatee_id,
                product_id=product_id,
                status='sent'
            ).order_by(EmailLog.sent_at.desc()).first()
            
            if not last_email:
                return True  # No previous email, send it
            
            # Check if enough time has passed
            time_since = datetime.utcnow() - last_email.sent_at
            minutes_since = time_since.total_seconds() / 60
            
            return minutes_since >= interval_minutes
            
        except Exception as e:
            logger.error(f"Error checking email interval: {str(e)}")
            return True  # Default to sending if error
    
    @classmethod
    def send_email(cls, to_email: str, subject: str, html_content: str, 
                   text_content: str = None, email_type: str = 'general',
                   recipient_name: str = None, product_id: int = None,
                   incubatee_id: int = None, stock_amount: int = None,
                   threshold: int = None, interval_minutes: int = 5) -> bool:
        """Send an email using configured SMTP settings with logging"""
        
        # Check if we should send based on interval
        if product_id and incubatee_id:
            if not cls.should_send_email(incubatee_id, product_id, interval_minutes):
                logger.info(f"Skipping email to {to_email} - within interval period")
                # Log as skipped
                cls.log_email(
                    email_type=email_type,
                    recipient_email=to_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    product_id=product_id,
                    incubatee_id=incubatee_id,
                    stock_amount=stock_amount,
                    threshold=threshold,
                    status='skipped',
                    error_message='Within interval period',
                    interval_minutes=interval_minutes
                )
                return False
        
        try:
            # Get email configuration from app config
            smtp_host = current_app.config.get('SMTP_HOST', 'smtp.gmail.com')
            smtp_port = current_app.config.get('SMTP_PORT', 587)
            smtp_username = current_app.config.get('SMTP_USERNAME')
            smtp_password = current_app.config.get('SMTP_PASSWORD')
            from_email = current_app.config.get('FROM_EMAIL', smtp_username)
            
            if not all([smtp_username, smtp_password, from_email]):
                logger.error("Email configuration missing")
                # Log failure
                cls.log_email(
                    email_type=email_type,
                    recipient_email=to_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    product_id=product_id,
                    incubatee_id=incubatee_id,
                    stock_amount=stock_amount,
                    threshold=threshold,
                    status='failed',
                    error_message='Email configuration missing',
                    interval_minutes=interval_minutes
                )
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            # Attach both HTML and plain text versions
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            
            # Log success
            cls.log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=recipient_name,
                subject=subject,
                product_id=product_id,
                incubatee_id=incubatee_id,
                stock_amount=stock_amount,
                threshold=threshold,
                status='sent',
                interval_minutes=interval_minutes
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            
            # Log failure
            cls.log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=recipient_name,
                subject=subject,
                product_id=product_id,
                incubatee_id=incubatee_id,
                stock_amount=stock_amount,
                threshold=threshold,
                status='failed',
                error_message=str(e),
                interval_minutes=interval_minutes
            )
            return False
    
    @classmethod
    def send_low_stock_notification(cls, product_data: Dict[str, Any]) -> bool:
        """Send low stock notification to incubatee"""
        from .email_templates import EmailTemplates
        
        if not product_data.get('email'):
            logger.warning(f"No email found for incubatee {product_data.get('incubatee_name')}")
            return False
        
        subject, html_content, text_content = EmailTemplates.low_stock_notification(product_data)
        
        return cls.send_email(
            to_email=product_data['email'],
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            email_type='low_stock',
            recipient_name=product_data['incubatee_name'],
            product_id=product_data.get('product_id'),
            incubatee_id=product_data.get('incubatee_id'),
            stock_amount=product_data.get('current_stock'),
            threshold=product_data.get('threshold', 10),
            interval_minutes=current_app.config.get('EMAIL_INTERVAL_MINUTES', 5)
        )
    
    @classmethod
    def send_admin_notification(cls, products_data: List[Dict[str, Any]]) -> bool:
        """Send notification to admin about multiple low stock products"""
        from .email_templates import EmailTemplates
        
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if not admin_email:
            logger.warning("Admin email not configured")
            return False
        
        subject, html_content, text_content = EmailTemplates.bulk_low_stock_notification(products_data)
        
        return cls.send_email(
            to_email=admin_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            email_type='admin_low_stock_summary',
            recipient_name='Admin',
            interval_minutes=0  # No interval for admin emails
        )
    
    @classmethod
    def get_email_stats(cls, hours: int = 24) -> Dict[str, Any]:
        """Get email statistics for the last N hours"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Total emails
            total_emails = EmailLog.query.filter(EmailLog.sent_at >= since).count()
            
            # By status
            sent_emails = EmailLog.query.filter(
                EmailLog.sent_at >= since,
                EmailLog.status == 'sent'
            ).count()
            
            failed_emails = EmailLog.query.filter(
                EmailLog.sent_at >= since,
                EmailLog.status == 'failed'
            ).count()
            
            skipped_emails = EmailLog.query.filter(
                EmailLog.sent_at >= since,
                EmailLog.status == 'skipped'
            ).count()
            
            # By type
            low_stock_emails = EmailLog.query.filter(
                EmailLog.sent_at >= since,
                EmailLog.email_type == 'low_stock'
            ).count()
            
            return {
                'total': total_emails,
                'sent': sent_emails,
                'failed': failed_emails,
                'skipped': skipped_emails,
                'low_stock_emails': low_stock_emails,
                'period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Error getting email stats: {str(e)}")
            return {'error': str(e)}