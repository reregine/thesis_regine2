
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from flask import current_app

logger = logging.getLogger(__name__)

class EmailSender:
    """Send email notifications"""
    
    @classmethod
    def send_email(cls, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send an email using configured SMTP settings"""
        try:
            # Get email configuration from app config
            smtp_host = current_app.config.get('SMTP_HOST', 'smtp.gmail.com')
            smtp_port = current_app.config.get('SMTP_PORT', 587)
            smtp_username = current_app.config.get('SMTP_USERNAME', 'reginejoycefrancisco110603@gmail.com')
            smtp_password = current_app.config.get('SMTP_PASSWORD', 'lpsdyhyrsfpzewzy')
            from_email = current_app.config.get('FROM_EMAIL', 'atbi.system@gmail.com')

            if not all([smtp_username, smtp_password, from_email]):
                logger.error("Email configuration missing")
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
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
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
            text_content=text_content
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
            text_content=text_content
        )