# app/utils/email.py
from flask import render_template, current_app
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

def send_inventory_alert_email(recipients, subject, product, alert, current_stock, alert_level=None, is_test=False):
    """Send inventory alert email using SMTP"""
    try:
        # Get email configuration from app config
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = current_app.config.get('MAIL_PORT', 587)
        mail_username = current_app.config.get('MAIL_USERNAME', '')
        mail_password = current_app.config.get('MAIL_PASSWORD', '')
        mail_from = current_app.config.get('MAIL_DEFAULT_SENDER', 'inventory@example.com')
        
        # Create email body
        html_body = render_inventory_alert_html(product=product, alert=alert, current_stock=current_stock, alert_level=alert_level, is_test=is_test)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_from
        
        # Handle recipients (can be string or list)
        if isinstance(recipients, str):
            recipients = [email.strip() for email in recipients.split(',')]
        msg['To'] = ', '.join(recipients)
        
        # Attach HTML content
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Send email in background thread
        thread = threading.Thread(
            target=send_email_thread,
            args=(smtp_server, smtp_port, mail_username, mail_password, mail_from, recipients, msg)
        )
        thread.start()
        
        return thread
        
    except Exception as e:
        current_app.logger.error(f"Failed to send inventory alert: {e}")
        return None

def send_email_thread(smtp_server, smtp_port, username, password, mail_from, recipients, msg):
    """Send email in a separate thread"""
    try:
        # Connect to SMTP server
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            if username and password:
                server.login(username, password)
            
            # Send email
            server.sendmail(mail_from, recipients, msg.as_string())
            
        print(f"✅ Email sent successfully to {recipients}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def render_inventory_alert_html(product, alert, current_stock, alert_level=None, is_test=False):
    """Render HTML email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: {'#e74c3c' if alert_level == 'critical' else '#f39c12'}; 
                     color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .product-info {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; }}
            .alert-level {{ display: inline-block; padding: 5px 10px; border-radius: 3px; color: white; 
                          background-color: {'#e74c3c' if alert_level == 'critical' else '#f39c12'}; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #777; }}
            .btn {{ display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; 
                  text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{'TEST: ' if is_test else ''}Inventory Alert</h1>
            <span class="alert-level">
                {alert_level.upper() if alert_level else 'STOCK'} ALERT
            </span>
        </div>
        
        <div class="content">
            <h2>{product.name}</h2>
            
            <div class="product-info">
                <p><strong>Current Stock:</strong> <span style="color: {'#e74c3c' if alert_level == 'critical' else '#f39c12'}; font-weight: bold;">{current_stock} units</span></p>
                <p><strong>Alert Threshold:</strong> 
                    {alert.critical_stock_threshold if alert_level == 'critical' else alert.low_stock_threshold} units
                    ({'Critical' if alert_level == 'critical' else 'Low'})
                </p>
                <p><strong>Reorder Point:</strong> {alert.reorder_point} units</p>
                <p><strong>Product Code:</strong> {product.stock_no}</p>
                <p><strong>Vendor:</strong> {product.incubatee.company_name if product.incubatee.company_name else f'{product.incubatee.first_name} {product.incubatee.last_name}'}</p>
            </div>
            
            <h3>Recommended Action:</h3>
            <ul>
                {f'<li>IMMEDIATE ACTION REQUIRED: Restock product immediately</li><li>Consider temporarily disabling product from sales</li><li>Contact vendor for urgent restocking</li>' if alert_level == 'critical' else '<li>Plan for restocking within the next few days</li><li>Check sales trends for this product</li><li>Update reorder point if necessary</li>'}
            </ul>
            
            <p><strong>Alert ID:</strong> INV-{alert.alert_id if alert else 'TEST'}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated alert from the ATBI Inventory Management System.</p>
            <p>To manage your alert preferences, visit the inventory dashboard.</p>
        </div>
    </body>
    </html>
    """