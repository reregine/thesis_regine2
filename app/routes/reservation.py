from flask import Blueprint, request, jsonify, session, current_app, url_for
from ..extension import db
from ..models.reservation import Reservation
from ..models.admin import IncubateeProduct
from ..models.sales_report import SalesReport 
from datetime import datetime

reservation_bp = Blueprint("reservation_bp", __name__, url_prefix="/reservations")

def process_reservation_queues():
    """
    Process all pending reservations for all products using FCFS algorithm
    This function automatically approves reservations when stock is available
    and rejects reservations when stock is insufficient
    """
    try:
        # Get all products that have pending reservations
        products_with_pending = db.session.query(IncubateeProduct).join(Reservation).filter(
            Reservation.status == "pending").distinct().all()

        for product in products_with_pending:
            process_product_reservations(product.product_id)
            
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing reservation queues: {e}")
        return False

def process_product_reservations(product_id):
    """
    Process pending reservations for a specific product using FCFS algorithm
    Automatically approves when stock available, rejects when insufficient stock
    """
    try:
        product = IncubateeProduct.query.get(product_id)
        if not product:
            return False

        # Get all pending reservations for this product, ordered by reservation time (FCFS)
        pending_reservations = Reservation.query.filter_by(product_id=product_id, status="pending").order_by(Reservation.reserved_at.asc()).all()

        available_stock = product.stock_amount or 0
        
        for reservation in pending_reservations:
            if available_stock >= reservation.quantity:
                # Enough stock - approve reservation and deduct stock
                reservation.status = "approved"
                reservation.approved_at = datetime.utcnow()
                available_stock -= reservation.quantity
                product.stock_amount = available_stock
                
                current_app.logger.info(f"Reservation {reservation.reservation_id} auto-approved. "f"Stock deducted: {reservation.quantity}, Remaining: {available_stock}")
            else:
                # Not enough stock - reject reservation
                reservation.status = "rejected"
                reservation.rejected_at = datetime.utcnow()
                reservation.rejected_reason = "Insufficient stock - product out of stock"
                
                current_app.logger.info(f"Reservation {reservation.reservation_id} auto-rejected. "f"Requested: {reservation.quantity}, Available: {available_stock}")
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing reservations for product {product_id}: {e}")
        return False

    #CREATE A RESERVATION (with automatic FCFS processing)
@reservation_bp.route("/create", methods=["POST"])
def create_reservation():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not all([user_id, product_id, quantity]):
            return jsonify({"error": "Missing required fields"}), 400

        if quantity <= 0:
            return jsonify({"error": "Quantity must be greater than 0"}), 400

        product = IncubateeProduct.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # Check if product has any stock at all
        current_stock = product.stock_amount or 0
        if current_stock <= 0:
            # Immediately reject if no stock
            reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="rejected",reserved_at=datetime.utcnow(),rejected_at=datetime.utcnow(),rejected_reason="Product out of stock")
            db.session.add(reservation)
            db.session.commit()
            
            return jsonify({"message": "Reservation created but rejected - product out of stock","reservation_id": reservation.reservation_id,"status": "rejected","reason": "Product out of stock"}), 201

        # Create reservation as pending first
        reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="pending",reserved_at=datetime.utcnow())
        db.session.add(reservation)
        db.session.commit()

        #CRITICAL FIX: Process immediately after creation
        process_product_reservations(product_id)
        
        #Refresh to get the final status
        db.session.refresh(reservation)

        return jsonify({
            "message": "Reservation processed successfully","reservation_id": reservation.reservation_id,
            "status": reservation.status,"reason": reservation.rejected_reason if reservation.status == "rejected" else None}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating reservation: {e}")
        return jsonify({"error": "Server error"}), 500
# BULK CREATE RESERVATIONS (from cart)
@reservation_bp.route("/create-bulk", methods=["POST"])
def create_bulk_reservations():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        items = data.get("items", [])  # List of {product_id, quantity}

        if not user_id or not items:
            return jsonify({"error": "Missing required fields"}), 400

        results = []
        processed_products = set()
        
        # First, create all reservations as pending
        for item in items:
            product_id = item.get("product_id")
            quantity = item.get("quantity")

            if not product_id or quantity <= 0:
                continue

            product = IncubateeProduct.query.get(product_id)
            if not product:
                results.append({"product_id": product_id,"status": "error","message": "Product not found"})
                continue

            # Check if product has no stock
            current_stock = product.stock_amount or 0
            if current_stock <= 0:
                reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="rejected",reserved_at=datetime.utcnow(),rejected_at=datetime.utcnow(),rejected_reason="Product out of stock")
                db.session.add(reservation)
                results.append({"product_id": product_id,"reservation_id": reservation.reservation_id,"status": "rejected","message": "Product out of stock"})
            else:
                # Create as pending
                reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="pending",reserved_at=datetime.utcnow())
                db.session.add(reservation)
                results.append({"product_id": product_id,"reservation_id": reservation.reservation_id,"status": "pending"})
                processed_products.add(product_id)

        db.session.commit()

        # Process each product's reservation queue
        for product_id in processed_products:
            process_product_reservations(product_id)

        # Update results with final statuses
        for result in results:
            if "reservation_id" in result:
                reservation = Reservation.query.get(result["reservation_id"])
                if reservation:
                    result["status"] = reservation.status
                    result["message"] = f"Reservation {reservation.status}"
                    if reservation.status == "rejected":
                        result["reason"] = reservation.rejected_reason

        return jsonify({"message": "Reservations processed successfully","results": results}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating bulk reservations: {e}")
        return jsonify({"error": "Server error"}), 500

# UPDATE RESERVATION STATUS (Only for completion)
@reservation_bp.route("/<int:reservation_id>/status", methods=["PUT"])
def update_reservation_status(reservation_id):
    """Only allow updating to 'completed' status (when item is picked up)"""
    try:
        data = request.get_json()
        new_status = data.get("status")

        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({"error": "Reservation not found"}), 404

        # Only allow changing to 'completed' status
        if new_status != "completed":
            return jsonify({"error": "Only status change to 'completed' is allowed"}), 400

        # Only allow completing approved reservations
        if reservation.status != "approved":
            return jsonify({"error": "Only approved reservations can be completed"}), 400

        # Get product details
        product = IncubateeProduct.query.get(reservation.product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # Update reservation status
        reservation.status = new_status
        reservation.completed_at = datetime.utcnow()

        # Create sales report entry
        sales_report = SalesReport(reservation_id=reservation.reservation_id,
            product_id=reservation.product_id,user_id=reservation.user_id,product_name=product.name,
            quantity=reservation.quantity,unit_price=product.price_per_stocks,total_price=product.price_per_stocks * reservation.quantity,
            sale_date=datetime.utcnow().date(),  # Today's date
            completed_at=datetime.utcnow())
        
        db.session.add(sales_report)
        db.session.commit()
        
        return jsonify({"message": "Reservation marked as completed and sales record created","sales_id": sales_report.sales_id}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating reservation: {e}")
        return jsonify({"error": "Server error"}), 500
    
# GET ALL RESERVATIONS (ADMIN / STAFF)
@reservation_bp.route("/", methods=["GET"])
def get_all_reservations():
    try:
        reservations = (
            db.session.query(Reservation, IncubateeProduct)
            .join(IncubateeProduct, Reservation.product_id == IncubateeProduct.product_id)
            .order_by(Reservation.reserved_at.desc())
            .all())
        
        result = []
        for reservation, product in reservations:
            result.append({"reservation_id": reservation.reservation_id,"user_id": reservation.user_id,"product_id": product.product_id,
                "product_name": product.name,"price_per_stocks": float(product.price_per_stocks or 0),
                "quantity": reservation.quantity,"status": reservation.status,
                "reserved_at": reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "approved_at": reservation.approved_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.approved_at else None,
                "completed_at": reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else None,
                "rejected_at": reservation.rejected_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.rejected_at else None,
                "rejected_reason": reservation.rejected_reason})

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching all reservations: {e}")
        return jsonify({"error": "Server error"}), 500    

# FORCE PROCESS ALL PENDING RESERVATIONS
@reservation_bp.route("/process-pending", methods=["POST"])
def process_pending_reservations():
    """Admin endpoint to force process all pending reservations"""
    try:
        success = process_reservation_queues()
        
        if success:
            return jsonify({"success": True, "message": "All pending reservations processed successfully"})
        else:
            return jsonify({"success": False, "message": "Error processing pending reservations"})
            
    except Exception as e:
        current_app.logger.error(f"Error processing pending reservations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# GET PRODUCT RESERVATION QUEUE
@reservation_bp.route("/product/<int:product_id>/queue", methods=["GET"])
def get_product_reservation_queue(product_id):
    """Get the current reservation queue for a product"""
    try:
        product = IncubateeProduct.query.get(product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404

        # Get all reservations for this product, ordered by reservation time
        reservations = Reservation.query.filter_by(product_id=product_id).order_by(Reservation.reserved_at.asc()).all()

        queue_data = []
        for reservation in reservations:
            queue_data.append({"reservation_id": reservation.reservation_id,"user_id": reservation.user_id,
                "quantity": reservation.quantity,"status": reservation.status,
                "reserved_at": reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "position_in_queue": len([r for r in reservations if r.reserved_at <= reservation.reserved_at])})

        return jsonify({"success": True,"product_id": product_id,"product_name": product.name,"current_stock": product.stock_amount or 0,"reservation_queue": queue_data})

    except Exception as e:
        current_app.logger.error(f"Error fetching product queue: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# GET RESERVATIONS BY STATUS (Shopee-style tab)
@reservation_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_reservations(user_id):
    try:
        reservations = (
            db.session.query(Reservation, IncubateeProduct)
            .join(IncubateeProduct, Reservation.product_id == IncubateeProduct.product_id)
            .filter(Reservation.user_id == user_id)
            .order_by(Reservation.reserved_at.desc())
            .all())

        reservations_list = []
        for reservation, product in reservations:
            reservations_list.append({
                "reservation_id": reservation.reservation_id,
                "product_id": product.product_id,
                "product_name": product.name,
                "image_path": url_for('static', filename=f'uploads/{product.image_path}') if product.image_path else url_for('static', filename='images/no-image.png'),
                "price_per_stocks": float(product.price_per_stocks or 0),
                "quantity": reservation.quantity,
                "status": reservation.status,
                "reserved_at": reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "approved_at": reservation.approved_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.approved_at else None,
                "completed_at": reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else None,
                "rejected_at": reservation.rejected_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.rejected_at else None,
                "rejected_reason": reservation.rejected_reason  })

        return jsonify({"success": True, "reservations": reservations_list}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching user reservations: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@reservation_bp.route("/status/<string:status>", methods=["GET"])
def get_reservations_by_status(status):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        if status not in ["pending", "approved", "completed", "rejected"]:
            return jsonify({"success": False, "message": "Invalid status"}), 400

        reservations = (
            db.session.query(Reservation, IncubateeProduct)
            .join(IncubateeProduct, Reservation.product_id == IncubateeProduct.product_id)
            .filter(Reservation.user_id == user_id, Reservation.status == status)
            .order_by(Reservation.reserved_at.desc())
            .all())

        reservations_list = []
        for reservation, product in reservations:
            reservations_list.append({
                "reservation_id": reservation.reservation_id,
                "product_id": product.product_id,
                "product_name": product.name,
                "image_path": url_for('static', filename=f'uploads/{product.image_path}') if product.image_path else url_for('static', filename='images/no-image.png'),
                "price_per_stocks": float(product.price_per_stocks or 0),
                "quantity": reservation.quantity,
                "status": reservation.status,
                "reserved_at": reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "approved_at": reservation.approved_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.approved_at else None,
                "completed_at": reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else None,
                "rejected_at": reservation.rejected_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.rejected_at else None,
                "rejected_reason": reservation.rejected_reason})

        return jsonify({"success": True, "reservations": reservations_list}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching {status} reservations: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500


# DELETE RESERVATION
@reservation_bp.route("/<int:reservation_id>", methods=["DELETE"])
def delete_reservation(reservation_id):
    try:
        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({"error": "Reservation not found"}), 404

        db.session.delete(reservation)
        db.session.commit()
        return jsonify({"message": "Reservation deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting reservation: {e}")
        return jsonify({"error": "Server error"}), 500

@reservation_bp.route("/<int:reservation_id>/approve", methods=["POST"])
def approve_reservation(reservation_id):
    """Approve reservation and update product stock."""
    try:
        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({"success": False, "error": "Reservation not found"})
        
        product = IncubateeProduct.query.get(reservation.product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"})
        
        # Check if enough stock is available
        if product.stock_amount < reservation.quantity:
            return jsonify({"success": False, "error": "Insufficient stock"})
        
        # Update stock amount
        product.stock_amount -= reservation.quantity
        reservation.status = "approved"
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Reservation approved and stock updated"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    
# SALES REPORT - Get sales data from sales_reports table
@reservation_bp.route("/sales-report", methods=["GET"])
def get_sales_report():
    try:
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"success": False, "error": "Date parameter is required"}), 400
        
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Get sales data with joined reservation info
        sales_data = (
            db.session.query(SalesReport, Reservation)
            .join(Reservation, SalesReport.reservation_id == Reservation.reservation_id)
            .filter(SalesReport.sale_date == target_date)
            .order_by(Reservation.completed_at.desc())
            .all())
        
        # Calculate summary
        total_sales = sum(sale.SalesReport.total_price for sale in sales_data)
        total_orders = len(sales_data)
        total_products = sum(sale.SalesReport.quantity for sale in sales_data)
        
        # Prepare report data - using Reservation's completed_at
        report_data = []
        for sale_report, reservation in sales_data:
            report_data.append({
                "sales_id": sale_report.sales_id,
                "reservation_id": sale_report.reservation_id,
                "user_id": sale_report.user_id,
                "product_name": sale_report.product_name,
                "quantity": sale_report.quantity,
                "unit_price": float(sale_report.unit_price),
                "total_price": float(sale_report.total_price),
                "sale_date": sale_report.sale_date.strftime("%Y-%m-%d"),
                "reserved_at": reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_at": reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else None,
                "status": reservation.status})
        
        summary = {"total_sales": float(total_sales),"total_orders": total_orders,
            "completed_orders": total_orders,  # All sales reports are completed orders
            "total_products": total_products}
        
        return jsonify({"success": True,"report": report_data,"summary": summary}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating sales report: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500

# EXPORT SALES REPORT TO CSV
@reservation_bp.route("/sales-report/export", methods=["GET"])
def export_sales_report():
    try:
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"success": False, "error": "Date parameter is required"}), 400
        
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Get sales data with joined reservation info
        sales_data = (
            db.session.query(SalesReport, Reservation)
            .join(Reservation, SalesReport.reservation_id == Reservation.reservation_id)
            .filter(SalesReport.sale_date == target_date)
            .order_by(Reservation.completed_at.asc())
            .all()
        )
        
        # Create CSV content
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header - added reserved_at and status
        writer.writerow(['Sales ID', 'Reservation ID', 'User ID', 'Product Name', 'Quantity', 'Unit Price', 'Total Price', 'Sale Date', 'Reserved Date', 'Completed Time', 'Status'])
        
        # Write data - FIXED: Remove peso sign, export only numbers
        for sale_report, reservation in sales_data:
            writer.writerow([
                sale_report.sales_id,
                sale_report.reservation_id,
                sale_report.user_id,
                sale_report.product_name,
                sale_report.quantity,
                float(sale_report.unit_price),  # FIXED: No peso sign, just the number
                float(sale_report.total_price),  # FIXED: No peso sign, just the number
                sale_report.sale_date.strftime("%Y-%m-%d"),
                reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else "N/A",
                reservation.status])
        
        # Prepare response
        from flask import Response
        response = Response(output.getvalue(),mimetype="text/csv",headers={"Content-Disposition": f"attachment;filename=sales-report-{date_str}.csv","Content-type": "text/csv"})
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting sales report: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500
        
# GET SALES SUMMARY (For Dashboard)
@reservation_bp.route("/sales-summary", methods=["GET"])
def get_sales_summary():
    """Get overall sales summary for dashboard"""
    try:
        # Today's sales
        today = datetime.utcnow().date()
        today_sales = db.session.query(db.func.sum(SalesReport.total_price)).filter(SalesReport.sale_date == today).scalar() or 0
        
        # This month's sales
        first_day_of_month = today.replace(day=1)
        month_sales = db.session.query(db.func.sum(SalesReport.total_price)).filter(SalesReport.sale_date >= first_day_of_month).scalar() or 0
        
        # Total completed orders today
        today_orders = db.session.query(SalesReport).filter(SalesReport.sale_date == today).count()
        
        # Total products sold today
        today_products = db.session.query(db.func.sum(SalesReport.quantity)).filter(SalesReport.sale_date == today).scalar() or 0
        
        return jsonify({
            "success": True,
            "summary": {"today_sales": float(today_sales),"month_sales": float(month_sales),"today_orders": today_orders,"today_products": today_products}}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting sales summary: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500

# GET SALES BY DATE RANGE
@reservation_bp.route("/sales-by-date-range", methods=["GET"])
def get_sales_by_date_range():
    """Get sales data for a date range (for charts)"""
    try:
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        
        if not start_date_str or not end_date_str:
            return jsonify({"success": False, "error": "Start and end date parameters are required"}), 400
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # Get daily sales for the date range
        daily_sales = db.session.query(
            SalesReport.sale_date,
            db.func.sum(SalesReport.total_price).label('daily_total'),
            db.func.count(SalesReport.sales_id).label('order_count'),
            db.func.sum(SalesReport.quantity).label('product_count')).filter(
            SalesReport.sale_date >= start_date,SalesReport.sale_date <= end_date).group_by(SalesReport.sale_date).order_by(SalesReport.sale_date).all()
        
        sales_data = []
        for day in daily_sales:
            sales_data.append({
                "date": day.sale_date.strftime("%Y-%m-%d"),
                "total_sales": float(day.daily_total or 0),
                "order_count": day.order_count,
                "product_count": day.product_count or 0})
        
        return jsonify({"success": True,"sales_data": sales_data,"start_date": start_date_str,"end_date": end_date_str}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting sales by date range: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500