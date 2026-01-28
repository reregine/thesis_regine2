# app/utils/email_templates.py
from typing import Dict, Any, List

class EmailTemplates:
    """Email templates for system notifications"""
    
    @staticmethod
    def low_stock_notification(product_data: Dict[str, Any]) -> tuple:
        """
        Create low stock notification email
        Returns (subject, html_content, text_content)
        """
        subject = f"⚠️ Low Stock Alert: {product_data['product_name']}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Low Stock Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #ff9800; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background-color: #f9f9f9; }}
                .alert-box {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; }}
                .product-info {{ background-color: white; border: 1px solid #ddd; padding: 20px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Low Stock Alert</h1>
                    <p>ATBI Incubator Management System</p>
                </div>
                
                <div class="content">
                    <p>Dear {product_data['incubatee_name']},</p>
                    
                    <div class="alert-box">
                        <h3>Your product is running low on stock!</h3>
                        <p>Please arrange to restock as soon as possible to avoid sales interruption.</p>
                    </div>
                    
                    <div class="product-info">
                        <h3>Product Details</h3>
                        <table>
                            <tr><td><strong>Product Name:</strong></td><td>{product_data['product_name']}</td></tr>
                            <tr><td><strong>Stock Number:</strong></td><td>{product_data['stock_no']}</td></tr>
                            <tr><td><strong>Current Stock:</strong></td><td><span style="color: red; font-weight: bold;">{product_data['current_stock']} units</span></td></tr>
                            <tr><td><strong>Low Stock Threshold:</strong></td><td>{product_data['threshold']} units</td></tr>
                            <tr><td><strong>Company:</strong></td><td>{product_data['company_name'] or 'N/A'}</td></tr>
                            <tr><td><strong>Alert Time:</strong></td><td>{product_data['last_checked'].strftime('%Y-%m-%d %H:%M:%S') if product_data.get('last_checked') else 'Now'}</td></tr>
                        </table>
                    </div>
                    
                    <p><strong>Required Action:</strong></p>
                    <ol>
                        <li>Check your current inventory levels</li>
                        <li>Prepare additional stock for delivery</li>
                        <li>Schedule restocking with ATBI staff</li>
                        <li>Update your product availability once restocked</li>
                    </ol>
                    
                    <p>To update your stock levels, please log in to your incubatee dashboard or contact ATBI administration.</p>
                    
                    <p style="text-align: center;">
                        <a href="#" class="btn">Update Stock Levels</a>
                    </p>
                    
                    <p>For assistance, please contact ATBI administration:</p>
                    <ul>
                        <li>Email: admin@atbi.com</li>
                        <li>Phone: (123) 456-7890</li>
                    </ul>
                    
                    <p>Best regards,<br>
                    <strong>ATBI Incubator Management System</strong></p>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from ATBI Incubator Management System.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        LOW STOCK ALERT - ATBI Incubator Management System
        
        Dear {product_data['incubatee_name']},
        
        Your product "{product_data['product_name']}" (Stock No: {product_data['stock_no']}) 
        is running low on stock!
        
        Current Stock: {product_data['current_stock']} units
        Low Stock Threshold: {product_data['threshold']} units
        Company: {product_data['company_name'] or 'N/A'}
        
        REQUIRED ACTION:
        1. Check your current inventory levels
        2. Prepare additional stock for delivery
        3. Schedule restocking with ATBI staff
        4. Update your product availability once restocked
        
        Please log in to your incubatee dashboard or contact ATBI administration to update stock levels.
        
        For assistance, contact ATBI administration:
        Email: admin@atbi.com
        Phone: (123) 456-7890
        
        Best regards,
        ATBI Incubator Management System
        
        This is an automated notification. Please do not reply to this email.
        """
        
        return subject, html_content, text_content
    
    @staticmethod
    def bulk_low_stock_notification(products_data: List[Dict[str, Any]]) -> tuple:
        """
        Create bulk low stock notification for multiple products
        """
        subject = f"⚠️ Low Stock Alert: {len(products_data)} Products Need Restocking"
        
        # Group products by incubatee
        incubatee_products = {}
        for product in products_data:
            incubatee_id = product['incubatee_id']
            if incubatee_id not in incubatee_products:
                incubatee_products[incubatee_id] = {
                    'incubatee_name': product['incubatee_name'],
                    'company_name': product['company_name'],
                    'products': []
                }
            incubatee_products[incubatee_id]['products'].append(product)
        
        html_products_list = ""
        for incubatee_id, data in incubatee_products.items():
            html_products_list += f"""
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #ff9800;">
                <h4>{data['incubatee_name']} - {data['company_name'] or 'N/A'}</h4>
                <ul>
            """
            for product in data['products']:
                html_products_list += f"""
                    <li>
                        <strong>{product['product_name']}</strong> (Stock No: {product['stock_no']})
                        - Current: <span style="color: red;">{product['current_stock']}</span> units
                        - Threshold: {product['threshold']} units
                    </li>
                """
            html_products_list += "</ul></div>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert {{ color: #856404; background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; }}
                .product-list {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="alert">
                <h2>⚠️ Multiple Products Need Restocking</h2>
                <p>Total products with low stock: {len(products_data)}</p>
            </div>
            
            <div class="product-list">
                {html_products_list}
            </div>
            
            <p>Please coordinate with respective incubatees for restocking.</p>
            
            <p><strong>ATBI Administration</strong></p>
        </body>
        </html>
        """
        
        text_content = f"Multiple products ({len(products_data)}) need restocking. Please check the system for details."
        
        return subject, html_content, text_content