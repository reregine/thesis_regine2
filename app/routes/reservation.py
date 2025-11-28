from flask import Blueprint, request, jsonify, session, current_app, url_for, Response
from ..extension import db
from ..models.reservation import Reservation
from ..models.admin import IncubateeProduct, SalesReport
from datetime import datetime, timezone, timedelta
import csv
from io import StringIO
import redis
import json
import os

reservation_bp = Blueprint("reservation_bp", __name__, url_prefix="/reservations")

# Redis client setup
redis_client = None

def get_redis_client():
    """Get redis client with lazy initialization"""
    global redis_client
    if redis_client is None:
        try:
            redis_url = os.environ.get('redis_url')
            if redis_url:
                redis_client = redis.from_url(redis_url)
            else:
                # Fallback to local redis if no environment variable
                redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        except Exception as e:
            current_app.logger.error(f"Redis Connection failed: {str(e)}")
            redis_client = None
    return redis_client

def cache_key(prefix, *args):
    """Generate cache key with prefix and arguments"""
    key_parts = [prefix] + [str(arg) for arg in args]
    return ":".join(key_parts)

def get_cached_data(key, expire_seconds=3600):
    """Get data from cache, return (data, found) tuple"""
    redis_client = get_redis_client()
    if not redis_client:
        return None, False
    
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached), True
        return None, False
    except Exception as e:
        current_app.logger.warning(f"Cache get error for key {key}: {str(e)}")
        return None, False
    
def set_cached_data(key, data, expire_seconds=3600):
    """Set data in cache with expiration"""
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        redis_client.setex(key, expire_seconds, json.dumps(data, default=str))
    except Exception as e:
        current_app.logger.warning(f"Cache set error for key {key}: {str(e)}")

def invalidate_cache(pattern):
    """Invalidate cache keys matching pattern"""
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        current_app.logger.warning(f"Cache invalidation error for pattern {pattern}: {str(e)}")

def invalidate_reservation_caches(user_id=None, product_id=None):
    """Invalidate reservation-related caches"""
    patterns = [
        "reservations:*",
        "reservations_user:*",
        "reservations_status:*",
        "product_queue:*",
        "sales:*"
    ]
    
    if user_id:
        patterns.append(f"reservations_user:{user_id}*")
        patterns.append(f"reservations_status:*:{user_id}")
    
    if product_id:
        patterns.append(f"product_queue:{product_id}")
        patterns.append(f"reservations_product:{product_id}*")
    
    for pattern in patterns:
        invalidate_cache(pattern)

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
        
        # Invalidate relevant caches after processing
        invalidate_reservation_caches()
        invalidate_cache("products:*")  # Invalidate product stock caches
        
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing reservation queues: {e}")
        return False

def process_product_reservations(product_id):
    """
    Process pending reservations for a specific product using FCFS algorithm
    Automatically approves when stock is available after 2-minute delay
    Rejects reservations when stock is insufficient
    """
    try:
        product = IncubateeProduct.query.get(product_id)
        if not product:
            return False

        # Get all pending reservations for this product, ordered by reservation time (FCFS)
        pending_reservations = Reservation.query.filter_by(
            product_id=product_id, 
            status="pending"
        ).order_by(Reservation.reserved_at.asc()).all()

        available_stock = product.stock_amount or 0
        current_time = datetime.now(timezone.utc)
        
        for reservation in pending_reservations:
            # Calculate how long the reservation has been pending
            time_pending = current_time - reservation.reserved_at
            time_pending_minutes = time_pending.total_seconds() / 60
            
            # Check if reservation has been pending for at least 2 minutes
            if time_pending_minutes >= 2:
                if available_stock >= reservation.quantity:
                    # Enough stock AND 2 minutes have passed - APPROVE the reservation
                    reservation.status = "approved"
                    reservation.approved_at = current_time
                    available_stock -= reservation.quantity
                    product.stock_amount = available_stock
                    
                    current_app.logger.info(
                        f"Reservation {reservation.reservation_id} auto-approved after {time_pending_minutes:.1f} minutes. "
                        f"Stock deducted: {reservation.quantity}, Remaining: {available_stock}"
                    )
                else:
                    # Not enough stock - REJECT the reservation
                    reservation.status = "rejected"
                    reservation.rejected_at = current_time
                    reservation.rejected_reason = "Insufficient stock - product out of stock"
                    
                    current_app.logger.info(
                        f"Reservation {reservation.reservation_id} auto-rejected after {time_pending_minutes:.1f} minutes. "
                        f"Requested: {reservation.quantity}, Available: {available_stock}"
                    )
            else:
                # Reservation is still within the 2-minute waiting period
                minutes_remaining = 2 - time_pending_minutes
                current_app.logger.info(
                    f"Reservation {reservation.reservation_id} still pending. "
                    f"Time elapsed: {time_pending_minutes:.1f} minutes, "
                    f"Time remaining: {minutes_remaining:.1f} minutes"
                )
        
        db.session.commit()
        
        # Invalidate caches for this product
        invalidate_reservation_caches(product_id=product_id)
        invalidate_cache(f"product:{product_id}")
        invalidate_cache(f"incubatee_products:{product.incubatee_id}")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing reservations for product {product_id}: {e}")
        return False

@reservation_bp.route("/create", methods=["POST"])
def create_reservation():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not all([user_id, product_id, quantity]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        if quantity <= 0:
            return jsonify({"success": False, "error": "Quantity must be greater than 0"}), 400

        product = IncubateeProduct.query.get(product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404

        # Check if product has any stock at all
        current_stock = product.stock_amount or 0
        if current_stock <= 0:
            # Immediately reject if no stock
            reservation = Reservation(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity,
                status="rejected",
                reserved_at=datetime.now(timezone.utc),
                rejected_at=datetime.now(timezone.utc),
                rejected_reason="Product out of stock"
            )
            db.session.add(reservation)
            db.session.commit()
            
            # Invalidate caches
            invalidate_reservation_caches(user_id=user_id, product_id=product_id)
            
            return jsonify({
                "success": True,
                "message": "Reservation created but rejected - product out of stock",
                "reservation_id": reservation.reservation_id,
                "status": "rejected",
                "reason": "Product out of stock"
            }), 201

        # Create reservation as pending first (will be processed after 2 minutes)
        reservation = Reservation(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            status="pending",
            reserved_at=datetime.now(timezone.utc)
        )
        db.session.add(reservation)
        db.session.commit()

        # Process immediately to check if it should be approved/rejected
        # But with the 2-minute delay logic, it will remain pending if stock is available
        process_product_reservations(product_id)
        
        # Refresh to get the final status
        db.session.refresh(reservation)

        # Calculate time until potential approval
        time_until_approval = "2 minutes" if reservation.status == "pending" else "immediately"
        
        # Invalidate caches
        invalidate_reservation_caches(user_id=user_id, product_id=product_id)
        
        return jsonify({
            "success": True,
            "message": f"Reservation created successfully. Status will be updated in {time_until_approval}",
            "reservation_id": reservation.reservation_id,
            "status": reservation.status,
            "estimated_approval_time": time_until_approval,
            "reason": reservation.rejected_reason if reservation.status == "rejected" else None
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating reservation: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500

@reservation_bp.route("/process-delayed", methods=["POST"])
def process_delayed_reservations():
    """
    Manually trigger processing of all pending reservations
    Useful for testing the 2-minute delay functionality
    """
    try:
        success = process_reservation_queues()
        
        if success:
            return jsonify({"success": True, "message": "Delayed reservations processed successfully","note": "Reservations pending for 2+ minutes were approved if stock available"})
        else:
            return jsonify({"success": False, "message": "Error processing delayed reservations"})
            
    except Exception as e:
        current_app.logger.error(f"Error processing delayed reservations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# BULK CREATE RESERVATIONS (from cart)
@reservation_bp.route("/create-bulk", methods=["POST"])
def create_bulk_reservations():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        items = data.get("items", [])  # List of {product_id, quantity}

        if not user_id or not items:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

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
                reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="rejected",reserved_at=datetime.now(timezone.utc),rejected_at=datetime.now(timezone.utc),rejected_reason="Product out of stock")
                db.session.add(reservation)
                results.append({"product_id": product_id,"reservation_id": reservation.reservation_id,"status": "rejected","message": "Product out of stock"})
            else:
                # Create as pending
                reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="pending",reserved_at=datetime.now(timezone.utc))
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

        # Invalidate caches
        invalidate_reservation_caches(user_id=user_id)
        for product_id in processed_products:
            invalidate_reservation_caches(product_id=product_id)
        
        return jsonify({"success": True, "message": "Reservations processed successfully","results": results}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating bulk reservations: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500

# UPDATE RESERVATION STATUS (Only for completion)
@reservation_bp.route("/<int:reservation_id>/status", methods=["PUT"])
def update_reservation_status(reservation_id):
    """Only allow updating to 'completed' status (when item is picked up)"""
    try:
        data = request.get_json()
        new_status = data.get("status")

        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({"success": False, "error": "Reservation not found"}), 404

        # Only allow changing to 'completed' status
        if new_status != "completed":
            return jsonify({"success": False, "error": "Only status change to 'completed' is allowed"}), 400

        # Only allow completing approved reservations
        if reservation.status != "approved":
            return jsonify({"success": False, "error": "Only approved reservations can be completed"}), 400

        # Get product details
        product = IncubateeProduct.query.get(reservation.product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404

        # Update reservation status
        reservation.status = new_status
        reservation.completed_at = datetime.now(timezone.utc)

        # Create sales report entry
        sales_report = SalesReport(
            reservation_id=reservation.reservation_id,
            product_id=reservation.product_id,
            user_id=reservation.user_id,
            product_name=product.name,
            quantity=reservation.quantity,
            unit_price=product.price_per_stocks,
            total_price=product.price_per_stocks * reservation.quantity,
            sale_date=datetime.now(timezone.utc).date()
        )
        
        db.session.add(sales_report)
        
        # ✅ AUTO-UPDATE PRODUCT POPULARITY
        try:
            from app.services.popularity_service import ProductPopularityService
            ProductPopularityService.update_from_reservation(reservation)
            print(f"🎯 Auto-updated popularity for reservation {reservation_id}")
        except Exception as e:
            print(f"⚠️ Could not update popularity: {e}")
        
        db.session.commit()
        
        # Invalidate caches
        invalidate_reservation_caches(user_id=reservation.user_id, product_id=reservation.product_id)
        invalidate_cache("sales:*")
        invalidate_cache("sales_summary:*")
        
        return jsonify({"success": True, "message": "Reservation marked as completed and sales record created","sales_id": sales_report.sales_id}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating reservation: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500
    
# GET ALL RESERVATIONS (ADMIN / STAFF)
@reservation_bp.route("/", methods=["GET"])
def get_all_reservations():
    try:
        cache_key_str = "reservations:all"
        
        # Try cache first (5 minutes cache for admin view)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=300)
        if found:
            return jsonify(cached_data)
        
        reservations = (
            db.session.query(Reservation, IncubateeProduct)
            .join(IncubateeProduct, Reservation.product_id == IncubateeProduct.product_id)
            .order_by(Reservation.reserved_at.desc())
            .all())
        
        result = []
        for reservation, product in reservations:
            result.append({
                "reservation_id": reservation.reservation_id,
                "user_id": reservation.user_id,
                "product_id": product.product_id,
                "product_name": product.name,
                "price_per_stocks": float(product.price_per_stocks or 0),
                "quantity": reservation.quantity,
                "status": reservation.status,
                "reserved_at": reservation.reserved_at.isoformat() if reservation.reserved_at else None,
                "approved_at": reservation.approved_at.isoformat() if reservation.approved_at else None,
                "completed_at": reservation.completed_at.isoformat() if reservation.completed_at else None,
                "rejected_at": reservation.rejected_at.isoformat() if reservation.rejected_at else None,
                "rejected_reason": reservation.rejected_reason
            })

        response_data = {
            "success": True,
            "reservations": result,
            "count": len(result),
            "message": "Reservations retrieved successfully"
        }
        
        set_cached_data(cache_key_str, response_data, 300)
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching all reservations: {e}")
        return jsonify({"success": False, "error": str(e),"reservations": [],"count": 0,"message": "Error fetching reservations"}), 500
        
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
        cache_key_str = cache_key("product_queue", product_id)
        
        # Try cache first (2 minutes cache for queue data)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=120)
        if found:
            return jsonify(cached_data)
        
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

        response_data = {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "current_stock": product.stock_amount or 0,
            "reservation_queue": queue_data
        }
        
        set_cached_data(cache_key_str, response_data, 120)
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching product queue: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# GET RESERVATIONS BY STATUS (Shopee-style tab)
@reservation_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_reservations(user_id):
    try:
        cache_key_str = cache_key("reservations_user", user_id)
        
        # Try cache first (2 minutes cache for user reservations)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=120)
        if found:
            return jsonify(cached_data)
        
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

        response_data = {"success": True, "reservations": reservations_list}
        set_cached_data(cache_key_str, response_data, 120)
        return jsonify(response_data), 200

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

        cache_key_str = cache_key("reservations_status", status, user_id)
        
        # Try cache first (1 minute cache for status-based queries - more frequent updates)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=60)
        if found:
            return jsonify(cached_data)

        reservations = (
            db.session.query(Reservation, IncubateeProduct)
            .join(IncubateeProduct, Reservation.product_id == IncubateeProduct.product_id)
            .filter(Reservation.user_id == user_id, Reservation.status == status)
            .order_by(Reservation.reserved_at.desc())
            .all())

        reservations_list = []
        current_time = datetime.now(timezone.utc)
        
        for reservation, product in reservations:
            # Calculate pending time for pending reservations
            pending_info = None
            if status == "pending":
                time_pending = current_time - reservation.reserved_at
                time_pending_minutes = time_pending.total_seconds() / 60
                minutes_remaining = max(0, 2 - time_pending_minutes)
                
                pending_info = {
                    "time_elapsed_minutes": round(time_pending_minutes, 1),
                    "time_remaining_minutes": round(minutes_remaining, 1),
                    "will_approve_at": (reservation.reserved_at + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
                }

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
                "rejected_reason": reservation.rejected_reason,
                "pending_info": pending_info  # Only for pending reservations
            })

        response_data = {"success": True, "reservations": reservations_list}
        set_cached_data(cache_key_str, response_data, 60)
        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching {status} reservations: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

# DELETE RESERVATION
@reservation_bp.route("/<int:reservation_id>", methods=["DELETE"])
def delete_reservation(reservation_id):
    try:
        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({"success": False, "error": "Reservation not found"}), 404

        user_id = reservation.user_id
        product_id = reservation.product_id
        
        db.session.delete(reservation)
        db.session.commit()
        
        # Invalidate relevant caches
        invalidate_reservation_caches(user_id=user_id, product_id=product_id)
        
        return jsonify({"success": True, "message": "Reservation deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting reservation: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500

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
        
        # Invalidate caches
        invalidate_reservation_caches(user_id=reservation.user_id, product_id=reservation.product_id)
        invalidate_cache(f"product:{reservation.product_id}")
        
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
        
        cache_key_str = cache_key("sales_report", date_str)
        
        # Try cache first (5 minutes cache for sales reports)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=300)
        if found:
            return jsonify(cached_data)
        
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
            report_data.append({"sales_id": sale_report.sales_id,"reservation_id": sale_report.reservation_id,
                "user_id": sale_report.user_id,"product_name": sale_report.product_name,"quantity": sale_report.quantity,
                "unit_price": float(sale_report.unit_price),"total_price": float(sale_report.total_price),"sale_date": sale_report.sale_date.strftime("%Y-%m-%d"),
                "reserved_at": reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_at": reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else None,
                "status": reservation.status})
        
        summary = {"total_sales": float(total_sales),"total_orders": total_orders,
            "completed_orders": total_orders,  # All sales reports are completed orders
            "total_products": total_products}
        
        response_data = {"success": True,"report": report_data,"summary": summary}
        set_cached_data(cache_key_str, response_data, 300)
        return jsonify(response_data), 200
        
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
        sales_data = (db.session.query(SalesReport, Reservation)
            .join(Reservation, SalesReport.reservation_id == Reservation.reservation_id)
            .filter(SalesReport.sale_date == target_date)
            .order_by(Reservation.completed_at.asc())
            .all())
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header - added reserved_at and status
        writer.writerow(['Sales ID', 'Reservation ID', 'User ID', 'Product Name', 'Quantity', 'Unit Price', 'Total Price', 'Sale Date', 'Reserved Date', 'Completed Time', 'Status'])
        
        # Write data - FIXED: Remove peso sign, export only numbers
        for sale_report, reservation in sales_data:
            writer.writerow([sale_report.sales_id,sale_report.reservation_id,sale_report.user_id,sale_report.product_name,sale_report.quantity,
                float(sale_report.unit_price),  # FIXED: No peso sign, just the number
                float(sale_report.total_price),  # FIXED: No peso sign, just the number
                sale_report.sale_date.strftime("%Y-%m-%d"),
                reservation.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),
                reservation.completed_at.strftime("%Y-%m-%d %H:%M:%S") if reservation.completed_at else "N/A",
                reservation.status])
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
        cache_key_str = "sales_summary:daily"
        
        # Try cache first (2 minutes cache for sales summary)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=120)
        if found:
            return jsonify(cached_data)
        
        # Today's sales
        today = datetime.now(timezone.utc).date()
        today_sales = db.session.query(db.func.sum(SalesReport.total_price)).filter(SalesReport.sale_date == today).scalar() or 0
        
        # This month's sales
        first_day_of_month = today.replace(day=1)
        month_sales = db.session.query(db.func.sum(SalesReport.total_price)).filter(SalesReport.sale_date >= first_day_of_month).scalar() or 0
        
        # Total completed orders today
        today_orders = db.session.query(SalesReport).filter(SalesReport.sale_date == today).count()
        
        # Total products sold today
        today_products = db.session.query(db.func.sum(SalesReport.quantity)).filter(SalesReport.sale_date == today).scalar() or 0
        
        response_data = {
            "success": True,
            "summary": {
                "today_sales": float(today_sales),
                "month_sales": float(month_sales),
                "today_orders": today_orders,
                "today_products": today_products
            }
        }
        
        set_cached_data(cache_key_str, response_data, 120)
        return jsonify(response_data), 200
        
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
        
        cache_key_str = cache_key("sales_range", start_date_str, end_date_str)
        
        # Try cache first (5 minutes cache for date range queries)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=300)
        if found:
            return jsonify(cached_data)
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # Get daily sales for the date range
        daily_sales = db.session.query(SalesReport.sale_date,
            db.func.sum(SalesReport.total_price).label('daily_total'),
            db.func.count(SalesReport.sales_id).label('order_count'),
            db.func.sum(SalesReport.quantity).label('product_count')).filter(
            SalesReport.sale_date >= start_date,SalesReport.sale_date <= end_date).group_by(SalesReport.sale_date).order_by(SalesReport.sale_date).all()
        
        sales_data = []
        for day in daily_sales:
            sales_data.append({"date": day.sale_date.strftime("%Y-%m-%d"),"total_sales": float(day.daily_total or 0),
                "order_count": day.order_count,"product_count": day.product_count or 0})
        
        response_data = {
            "success": True,
            "sales_data": sales_data,
            "start_date": start_date_str,
            "end_date": end_date_str
        }
        
        set_cached_data(cache_key_str, response_data, 300)
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting sales by date range: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500
    
# AUTO-CANCEL OVERDUE RESERVATIONS
@reservation_bp.route("/check-overdue", methods=["POST"])
def check_overdue_reservations():
    """
    Auto-cancel reservations that haven't been picked up within the specified time
    Uses timeout_ms parameter to determine how old reservations should be auto-cancelled
    """
    try:
        data = request.get_json()
        timeout_ms = data.get("timeout_ms", 60 * 1000)  # Default 1 minute for testing
        
        # Calculate the cutoff time
        cutoff_time = datetime.now() - timedelta(milliseconds=timeout_ms)
        
        # Find approved reservations older than the cutoff time
        overdue_reservations = Reservation.query.filter(Reservation.status == "approved",Reservation.reserved_at < cutoff_time).all()
        
        rejected_count = 0
        affected_users = set()
        affected_products = set()
        
        # Reject each overdue reservation
        for reservation in overdue_reservations:
            try:
                # Get product to restore stock
                product = IncubateeProduct.query.get(reservation.product_id)
                if product:
                    # Restore stock
                    product.stock_amount = (product.stock_amount or 0) + reservation.quantity
                    affected_products.add(reservation.product_id)
                
                # Update reservation status to rejected instead of deleting
                reservation.status = "rejected"
                reservation.rejected_at = datetime.now()
                reservation.rejected_reason = "Not picked up on time"
                
                affected_users.add(reservation.user_id)
                rejected_count += 1
                current_app.logger.info(f"Auto-rejected reservation {reservation.reservation_id}, restored {reservation.quantity} units to product {product.product_id}")
                
            except Exception as e:
                current_app.logger.error(f"Error processing reservation {reservation.reservation_id}: {e}")
                continue
        
        db.session.commit()
        
        # Invalidate caches for affected users and products
        for user_id in affected_users:
            invalidate_reservation_caches(user_id=user_id)
        for product_id in affected_products:
            invalidate_reservation_caches(product_id=product_id)
        
        return jsonify({"success": True,"rejected_count": rejected_count,"message": f"Auto-rejected {rejected_count} overdue reservations","cutoff_time": cutoff_time.strftime("%Y-%m-%d %H:%M:%S"),"timeout_minutes": timeout_ms / (60 * 1000)}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in auto-rejection: {e}")
        return jsonify({"success": False,"error": "Failed to process auto-rejection"}), 500