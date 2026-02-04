# File: app/utils/email_templates.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.reservation import Reservation

class EmailTemplates:
    """Email templates for system notifications"""
    
    @staticmethod
    def get_sold_quantities(product_id: int, days_back: int = 7) -> dict:
        """
        Get sold quantities from reservations for a product
        Returns: {
            'last_7_days': sold quantity in last 7 days,
            'pending_sold': currently reserved but not yet picked up,
            'total_sold_all_time': total sold from completed reservations
        }
        """
        try:
            # Get date threshold
            since_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Sold in last 7 days (completed reservations)
            last_7_days_sold = db.session.query(
                db.func.sum(Reservation.quantity)
            ).filter(
                Reservation.product_id == product_id,
                Reservation.status == 'completed',
                Reservation.completed_at >= since_date
            ).scalar() or 0
            
            # Currently pending/approved reservations (sold but not picked up yet)
            pending_sold = db.session.query(
                db.func.sum(Reservation.quantity)
            ).filter(
                Reservation.product_id == product_id,
                Reservation.status.in_(['pending', 'approved'])
            ).scalar() or 0
            
            # Total sold all time
            total_sold_all_time = db.session.query(
                db.func.sum(Reservation.quantity)
            ).filter(
                Reservation.product_id == product_id,
                Reservation.status == 'completed'
            ).scalar() or 0
            
            return {
                'last_7_days': int(last_7_days_sold),
                'pending_sold': int(pending_sold),
                'total_sold_all_time': int(total_sold_all_time),
                'trend': 'increasing' if last_7_days_sold > 0 else 'stable'
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting sold quantities: {str(e)}")
            return {
                'last_7_days': 0,
                'pending_sold': 0,
                'total_sold_all_time': 0,
                'trend': 'unknown'
            }
    
    @staticmethod
    def low_stock_notification(product_data: Dict[str, Any]) -> tuple:
        """
        Create low stock notification email with sold quantities
        Returns (subject, html_content, text_content)
        """
        # Get sold quantities
        sold_info = EmailTemplates.get_sold_quantities(product_data['product_id'])
        
        # Calculate effective available stock (current stock minus pending sold)
        current_stock = product_data.get('current_stock', 0)
        pending_sold = sold_info['pending_sold']
        effective_stock = max(0, current_stock - pending_sold)
        
        subject = f"⚠️ Low Stock Alert: {product_data['product_name']} - Only {effective_stock} units available"
        
        # Determine stock status
        stock_status = ""
        if effective_stock <= 3:
            stock_status = "CRITICAL - URGENT RESTOCK NEEDED"
        elif effective_stock <= 10:
            stock_status = "LOW - RESTOCK SOON"
        else:
            stock_status = "BELOW THRESHOLD"
        
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
                .alert-box {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .stock-info {{ background-color: white; border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .sold-info {{ background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .critical {{ background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0; }}
                .stat-card {{ background: white; padding: 15px; border-radius: 5px; border: 1px solid #dee2e6; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #28a745; }}
                .stat-label {{ font-size: 12px; color: #6c757d; }}
                .warning {{ color: #dc3545; font-weight: bold; }}
                .success {{ color: #28a745; }}
                .trend-up {{ color: #28a745; }}
                .trend-stable {{ color: #6c757d; }}
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
                    
                    <div class="alert-box {'critical' if effective_stock <= 3 else ''}">
                        <h3>📊 Your product is running low on stock!</h3>
                        <p><strong>Status:</strong> {stock_status}</p>
                        <p>Please arrange to restock as soon as possible to avoid sales interruption.</p>
                    </div>
                    
                    <div class="stock-info">
                        <h3>📦 Current Stock Overview</h3>
                        <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Product Name:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{product_data['product_name']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Stock Number:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{product_data['stock_no']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Physical Stock:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{product_data['current_stock']} units</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Pending Sales:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;" class="success">+{sold_info['pending_sold']} units</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Effective Available Stock:</strong></td>
                                <td style="padding: 8px;" class="{'warning' if effective_stock <= 3 else ''}">
                                    <strong>{effective_stock} units</strong>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="sold-info">
                        <h3>💰 Sales Performance</h3>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value">{sold_info['last_7_days']}</div>
                                <div class="stat-label">Units Sold (Last 7 Days)</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{sold_info['pending_sold']}</div>
                                <div class="stat-label">Units Pending Pickup</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{sold_info['total_sold_all_time']}</div>
                                <div class="stat-label">Total Units Sold</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value {'trend-up' if sold_info['trend'] == 'increasing' else 'trend-stable'}">
                                    {sold_info['trend'].upper()}
                                </div>
                                <div class="stat-label">Sales Trend</div>
                            </div>
                        </div>
                        
                        <p style="margin-top: 15px;">
                            <strong>Note:</strong> Your product has <span class="success">{sold_info['pending_sold']} units</span> 
                            reserved by customers waiting for pickup. These will be deducted from your current stock 
                            once picked up.
                        </p>
                    </div>
                    
                    <h3>📋 Required Action:</h3>
                    <ol>
                        <li>Check your current inventory levels</li>
                        <li>Prepare additional stock for delivery</li>
                        <li>Schedule restocking with ATBI staff</li>
                        <li>Update your product availability once restocked</li>
                        <li>Monitor sales trends and adjust stock levels accordingly</li>
                    </ol>
                    
                    <p style="text-align: center;">
                        <a href="#" class="btn">📊 View Detailed Sales Report</a>
                    </p>
                    
                    <p>For assistance, please contact ATBI administration:</p>
                    <ul>
                        <li>📧 Email: admin@atbi.com</li>
                        <li>📞 Phone: (123) 456-7890</li>
                    </ul>
                    
                    <p>Best regards,<br>
                    <strong>ATBI Incubator Management System</strong></p>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from ATBI Incubator Management System.</p>
                    <p>Notification generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        LOW STOCK ALERT - ATBI Incubator Management System
        ===================================================
        
        Dear {product_data['incubatee_name']},
        
        Your product "{product_data['product_name']}" (Stock No: {product_data['stock_no']}) 
        is running low on stock!
        
        📊 STOCK OVERVIEW:
        -----------------
        Product Name: {product_data['product_name']}
        Stock Number: {product_data['stock_no']}
        Physical Stock: {product_data['current_stock']} units
        Pending Sales: {sold_info['pending_sold']} units (awaiting pickup)
        Effective Available: {effective_stock} units
        
        Status: {stock_status}
        
        💰 SALES PERFORMANCE:
        --------------------
        Units Sold (Last 7 Days): {sold_info['last_7_days']}
        Units Pending Pickup: {sold_info['pending_sold']}
        Total Units Sold: {sold_info['total_sold_all_time']}
        Sales Trend: {sold_info['trend'].upper()}
        
        Note: You have {sold_info['pending_sold']} units reserved by customers 
        that will be deducted from your current stock once picked up.
        
        📋 REQUIRED ACTION:
        ------------------
        1. Check your current inventory levels
        2. Prepare additional stock for delivery
        3. Schedule restocking with ATBI staff
        4. Update your product availability once restocked
        5. Monitor sales trends and adjust stock levels accordingly
        
        To update your stock levels, please log in to your incubatee dashboard 
        or contact ATBI administration.
        
        For assistance, contact ATBI administration:
        📧 Email: admin@atbi.com
        📞 Phone: (123) 456-7890
        
        Best regards,
        ATBI Incubator Management System
        
        This is an automated notification.
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        Please do not reply to this email.
        """
        
        return subject, html_content, text_content
    
    @staticmethod
    def bulk_low_stock_notification(products_data: List[Dict[str, Any]]) -> tuple:
        """
        Create bulk low stock notification for multiple products
        Includes sold quantities for each product
        """
        # Get sold quantities for all products
        products_with_sales = []
        for product in products_data:
            sold_info = EmailTemplates.get_sold_quantities(product['product_id'])
            product['sold_info'] = sold_info
            # Calculate effective stock
            product['effective_stock'] = max(0, product['current_stock'] - sold_info['pending_sold'])
            products_with_sales.append(product)
        
        subject = f"⚠️ Low Stock Alert: {len(products_with_sales)} Products Need Restocking"
        
        # Group products by incubatee
        incubatee_products = {}
        for product in products_with_sales:
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
            # Count critical vs low stock for this incubatee
            critical_count = sum(1 for p in data['products'] if p['effective_stock'] <= 3)
            low_count = sum(1 for p in data['products'] if 3 < p['effective_stock'] <= 10)
            
            html_products_list += f"""
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #ff9800;">
                <h4>{data['incubatee_name']} - {data['company_name'] or 'N/A'}</h4>
                <p style="margin: 5px 0; font-size: 14px;">
                    <span style="color: #dc3545;">🔥 {critical_count} critical</span> | 
                    <span style="color: #ff9800;">⚠️ {low_count} low stock</span>
                </p>
                <table style="width:100%; border-collapse: collapse; margin: 10px 0; font-size: 13px;">
                    <thead>
                        <tr style="background-color: #e9ecef;">
                            <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Product</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 2px solid #dee2e6;">Stock No</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 2px solid #dee2e6;">Physical</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 2px solid #dee2e6;">Pending</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 2px solid #dee2e6;">Available</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 2px solid #dee2e6;">Sold (7d)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for product in data['products']:
                status_color = '#dc3545' if product['effective_stock'] <= 3 else '#ff9800'
                status_icon = '🔥' if product['effective_stock'] <= 3 else '⚠️'
                
                html_products_list += f"""
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">
                                <strong>{product['product_name']}</strong>
                            </td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #dee2e6;">
                                {product['stock_no']}
                            </td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #dee2e6;">
                                {product['current_stock']}
                            </td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #dee2e6; color: #28a745;">
                                {product['sold_info']['pending_sold']}
                            </td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #dee2e6; color: {status_color};">
                                {status_icon} {product['effective_stock']}
                            </td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #dee2e6;">
                                {product['sold_info']['last_7_days']}
                            </td>
                        </tr>
                """
            
            html_products_list += """
                    </tbody>
                </table>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert {{ color: #856404; background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; }}
                .summary-box {{ background-color: #007bff; color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .summary-stats {{ display: flex; justify-content: space-around; text-align: center; }}
                .stat {{ font-size: 24px; font-weight: bold; }}
                .stat-label {{ font-size: 12px; }}
                .product-list {{ margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="alert">
                <h2>⚠️ Multiple Products Need Restocking</h2>
                <p>Total products with low stock: {len(products_with_sales)}</p>
            </div>
            
            <div class="summary-box">
                <h3>📊 Summary</h3>
                <div class="summary-stats">
                    <div>
                        <div class="stat">{len(products_with_sales)}</div>
                        <div class="stat-label">Total Products</div>
                    </div>
                    <div>
                        <div class="stat">{sum(1 for p in products_with_sales if p['effective_stock'] <= 3)}</div>
                        <div class="stat-label">Critical</div>
                    </div>
                    <div>
                        <div class="stat">{sum(p['sold_info']['pending_sold'] for p in products_with_sales)}</div>
                        <div class="stat-label">Pending Units</div>
                    </div>
                </div>
            </div>
            
            <div class="product-list">
                {html_products_list}
            </div>
            
            <p><strong>Note:</strong> "Pending" refers to units sold but not yet picked up by customers. 
            These will be deducted from stock upon pickup.</p>
            
            <p>Please coordinate with respective incubatees for restocking.</p>
            
            <div class="footer">
                <p>This is an automated report from ATBI Stock Monitoring System.</p>
                <p>Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <p><strong>ATBI Administration</strong></p>
        </body>
        </html>
        """
        
        text_content = f"""ATBI Low Stock Report
=========================

Total Products Needing Restocking: {len(products_with_sales)}
Critical Products: {sum(1 for p in products_with_sales if p['effective_stock'] <= 3)}
Total Pending Units: {sum(p['sold_info']['pending_sold'] for p in products_with_sales)}

Please check the web interface for detailed product information.

Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        return subject, html_content, text_content