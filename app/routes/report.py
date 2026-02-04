# report.py
from flask import Blueprint, json, render_template, request, jsonify, session, redirect, url_for, current_app, Response
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import csv
from io import StringIO
from app.routes.shop import get_redis_client
from ..models.admin import SalesReport, Incubatee, IncubateeProduct, db
from ..models.user import User
from ..models.reservation import Reservation

report_bp = Blueprint("report", __name__, url_prefix="/admin/reports")

@report_bp.route("/sales-summary")
def sales_summary():
    """Get sales summary for reports - FIXED for User model without names"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'overview')
        filter_type = request.args.get('filter', 'all')  # New: all, incubatee, category
        
        # Create cache key based on parameters
        cache_key_str = f"sales_summary:{start_date}:{end_date}:{report_type}:{filter_type}"
        
        # Try cache first (shorter cache for reports - 5 minutes)
        redis_client = get_redis_client()
        if redis_client:
            cached_data = redis_client.get(cache_key_str)
            if cached_data:
                return jsonify(json.loads(cached_data))
        
        # Base query for sales data
        sales_query = SalesReport.query
        
        # Apply date filter if provided
        start_date_obj = None
        end_date_obj = None
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                sales_query = sales_query.filter(SalesReport.sale_date >= start_date_obj,
                                               SalesReport.sale_date <= end_date_obj)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format"}), 400
        
        # Apply additional filters based on filter_type
        if filter_type == 'incubatee':
            incubatee_id = request.args.get('incubatee_id')
            if incubatee_id:
                # multiple approaches to find sales for this incubatee
                # 1. Direct match on incubatee_id in SalesReport
                # 2. Match through product's incubatee_id
                sales_query = sales_query.join(IncubateeProduct, 
                                            SalesReport.product_id == IncubateeProduct.product_id)\
                                        .filter(db.or_(
                                            SalesReport.incubatee_id == incubatee_id,
                                            IncubateeProduct.incubatee_id == incubatee_id))
        elif filter_type == 'category':
            category = request.args.get('category')
            if category:
                sales_query = sales_query.join(IncubateeProduct).filter(
                    IncubateeProduct.category == category)
        
        # Get sales data with related information
        sales_data = sales_query.options(
            db.joinedload(SalesReport.incubatee),
            db.joinedload(SalesReport.product),
            db.joinedload(SalesReport.user)
        ).all()
        
        # Process sales data
        sales_list = []
        for sale in sales_data:
            # Get customer name from username (since User model only has username)
            customer_name = "Unknown"
            if sale.user:
                customer_name = sale.user.username
            
            # Get incubatee name
            incubatee_name = "Unknown"
            if sale.incubatee:
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            sales_list.append({
                "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
                "reservation_id": sale.reservation_id,
                "incubatee_name": incubatee_name,
                "product_name": sale.product_name,
                "customer_name": customer_name,
                "quantity": sale.quantity,
                "unit_price": float(sale.unit_price) if sale.unit_price else 0,
                "total_price": float(sale.total_price) if sale.total_price else 0,
                "status": "completed"
            })
        
        # Calculate summary statistics
        total_revenue = sum(float(sale.total_price) for sale in sales_data if sale.total_price)
        total_orders = len(sales_data)
        completed_orders = len(sales_data)
        completion_rate = 100.0 if total_orders > 0 else 0
        
        # Get unique incubatees
        incubatee_ids = set()
        for sale in sales_data:
            if sale.incubatee_id:
                incubatee_ids.add(sale.incubatee_id)
            elif sale.product and sale.product.incubatee_id:
                incubatee_ids.add(sale.product.incubatee_id)
        
        active_incubatees = len(incubatee_ids)
        
        # Incubatee performance data
        incubatee_performance = []
        incubatee_sales = {}
        
        # Group sales by incubatee
        for sale in sales_data:
            incubatee_id = None
            incubatee_name = "Unknown"
            
            if sale.incubatee:
                incubatee_id = sale.incubatee_id
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_id = sale.product.incubatee_id
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            if incubatee_id not in incubatee_sales:
                incubatee_sales[incubatee_id] = {
                    'name': incubatee_name,
                    'revenue': 0,
                    'order_count': 0,
                    'product_count': 0,
                    'completed_orders': 0,
                    'products': set()
                }
            
            incubatee_sales[incubatee_id]['revenue'] += float(sale.total_price) if sale.total_price else 0
            incubatee_sales[incubatee_id]['order_count'] += 1
            incubatee_sales[incubatee_id]['products'].add(sale.product_name)
            incubatee_sales[incubatee_id]['completed_orders'] += 1
        
        # Format incubatee performance data
        for incubatee_id, data in incubatee_sales.items():
            incubatee_performance.append({
                'name': data['name'],
                'revenue': data['revenue'],
                'order_count': data['order_count'],
                'product_count': len(data['products']),
                'completion_rate': (data['completed_orders'] / data['order_count'] * 100) if data['order_count'] > 0 else 0,
                'top_product': next(iter(data['products'])) if data['products'] else 'N/A'
            })
        
        # Sort incubatees by revenue
        incubatee_performance.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Sales by incubatee for doughnut chart
        incubatee_sales_chart = {}
        for sale in sales_data:
            incubatee_name = "Unknown"
            if sale.incubatee:
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            if incubatee_name not in incubatee_sales_chart:
                incubatee_sales_chart[incubatee_name] = 0
            incubatee_sales_chart[incubatee_name] += float(sale.total_price) if sale.total_price else 0
        
        # Convert to lists for chart, limit to top 8 for better visualization
        sorted_incubatee_sales = sorted(incubatee_sales_chart.items(), key=lambda x: x[1], reverse=True)
        incubatee_sales_labels = [inc[0] for inc in sorted_incubatee_sales[:8]]
        incubatee_sales_data = [inc[1] for inc in sorted_incubatee_sales[:8]]
        
        # If there are more than 8 incubatees, group the rest as "Others"
        if len(sorted_incubatee_sales) > 8:
            others_total = sum(inc[1] for inc in sorted_incubatee_sales[8:])
            if others_total > 0:
                incubatee_sales_labels.append("Others")
                incubatee_sales_data.append(others_total)
        
        # Top incubatees for bar chart (limit to 5)
        top_incubatees_labels = [inc['name'] for inc in incubatee_performance[:5]]
        top_incubatees_data = [inc['revenue'] for inc in incubatee_performance[:5]]
        
        response_data = {
            "success": True,
            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "completion_rate": completion_rate,
                "active_incubatees": active_incubatees
            },
            "sales_data": sales_list,
            "incubatee_performance": incubatee_performance,
            "charts": {
                "incubatee_sales": {
                    "labels": incubatee_sales_labels,
                    "data": incubatee_sales_data
                },
                "top_incubatees": {
                    "labels": top_incubatees_labels,
                    "data": top_incubatees_data
                }
            }
        }
        
        # Cache the response
        if redis_client:
            redis_client.setex(cache_key_str, 300, json.dumps(response_data, default=str))
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in sales_summary: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/export")
def export_report():
    """Export sales report to CSV"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'overview')
        filter_type = request.args.get('filter', 'all')
        incubatee_id = request.args.get('incubatee_id')
        category = request.args.get('category')
        
        # Get sales data (similar to sales_summary)
        sales_query = SalesReport.query.options(
            db.joinedload(SalesReport.incubatee),
            db.joinedload(SalesReport.product),
            db.joinedload(SalesReport.user)
        )
        
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            sales_query = sales_query.filter(
                SalesReport.sale_date >= start_date_obj,
                SalesReport.sale_date <= end_date_obj
            )
        
        # Apply additional filters
        if filter_type == 'incubatee' and incubatee_id:
            sales_query = sales_query.join(IncubateeProduct,
                                        SalesReport.product_id == IncubateeProduct.product_id)\
                                    .filter(db.or_(SalesReport.incubatee_id == incubatee_id,IncubateeProduct.incubatee_id == incubatee_id))
        elif filter_type == 'category' and category:
            sales_query = sales_query.join(IncubateeProduct).filter(
                IncubateeProduct.category == category)
        
        sales_data = sales_query.all()
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Order ID', 'Incubatee', 'Product', 'Customer', 'Quantity', 'Unit Price', 'Total', 'Status'])
        
        for sale in sales_data:
            # Get customer name from username
            customer_name = "Unknown"
            if sale.user:
                customer_name = sale.user.username
            
            # Get incubatee name
            incubatee_name = "Unknown"
            if sale.incubatee:
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            writer.writerow([
                sale.sale_date.isoformat() if sale.sale_date else '',
                sale.reservation_id,
                incubatee_name,
                sale.product_name,
                customer_name,
                sale.quantity,
                float(sale.unit_price) if sale.unit_price else 0,
                float(sale.total_price) if sale.total_price else 0,
                'completed'
            ])
        
        # Return CSV file
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=report-{start_date}-to-{end_date}.csv"}
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting report: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/preview")
def preview_report():
    """Preview report data (limited rows)"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        filter_type = request.args.get('filter', 'all')
        incubatee_id = request.args.get('incubatee_id')
        category = request.args.get('category')
        
        # Base query
        sales_query = SalesReport.query.options(
            db.joinedload(SalesReport.incubatee),
            db.joinedload(SalesReport.product),
            db.joinedload(SalesReport.user)
        )
        
        # Apply filters
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            sales_query = sales_query.filter(
                SalesReport.sale_date >= start_date_obj,
                SalesReport.sale_date <= end_date_obj
            )
        
        if filter_type == 'incubatee' and incubatee_id:
            sales_query = sales_query.join(IncubateeProduct,
                                        SalesReport.product_id == IncubateeProduct.product_id)\
                                    .filter(db.or_(SalesReport.incubatee_id == incubatee_id,IncubateeProduct.incubatee_id == incubatee_id))
        elif filter_type == 'category' and category:
            sales_query = sales_query.join(IncubateeProduct).filter(
                IncubateeProduct.category == category)
        
        # Get limited data for preview (first 20 rows)
        sales_data = sales_query.limit(20).all()
        
        # Prepare preview data
        preview_data = []
        total_revenue = 0
        
        for sale in sales_data:
            # Get customer name from username
            customer_name = "Unknown"
            if sale.user:
                customer_name = sale.user.username
            
            # Get incubatee name
            incubatee_name = "Unknown"
            if sale.incubatee:
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            preview_data.append({
                "date": sale.sale_date.strftime("%Y-%m-%d") if sale.sale_date else "",
                "order_id": sale.reservation_id,
                "incubatee": incubatee_name,
                "product": sale.product_name,
                "customer": customer_name,
                "quantity": sale.quantity,
                "unit_price": float(sale.unit_price) if sale.unit_price else 0,
                "total": float(sale.total_price) if sale.total_price else 0
            })
            
            total_revenue += float(sale.total_price) if sale.total_price else 0
        
        return jsonify({
            "success": True,
            "preview_data": preview_data,
            "total_rows": len(sales_data),
            "total_revenue": total_revenue,
            "has_more_data": sales_query.count() > 20
        })
        
    except Exception as e:
        current_app.logger.error(f"Error previewing report: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/get-incubatees")
def get_incubatees_for_filter():
    """Get incubatees for filter dropdown"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        incubatees = Incubatee.query.order_by(Incubatee.company_name.asc()).all()
        
        incubatees_list = [{
            "id": i.incubatee_id,
            "name": f"{i.company_name} ({i.first_name} {i.last_name})" if i.company_name else f"{i.first_name} {i.last_name}"
        } for i in incubatees]
        
        return jsonify({
            "success": True,
            "incubatees": incubatees_list
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/get-categories")
def get_categories_for_filter():
    """Get unique product categories for filter dropdown"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        categories = db.session.query(
            IncubateeProduct.category.distinct()
        ).filter(
            IncubateeProduct.category.isnot(None),
            IncubateeProduct.category != ''
        ).order_by(IncubateeProduct.category.asc()).all()
        
        categories_list = [c[0] for c in categories]
        
        return jsonify({
            "success": True,
            "categories": categories_list
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500