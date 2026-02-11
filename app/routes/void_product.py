# routes/void_product.py
from flask import Blueprint, jsonify, request, session, current_app
from ..extension import db
from ..models.void_product import VoidProduct
from ..models.reservation import Reservation
from ..models.admin import IncubateeProduct
import os
from werkzeug.utils import secure_filename
from datetime import datetime

void_bp = Blueprint("void_bp", __name__, url_prefix="/void")

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@void_bp.route("/request", methods=["POST"])
def request_void():
    """Request a void/return for a completed reservation"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        data = request.form.to_dict()
        reservation_id = data.get("reservation_id")
        
        if not reservation_id:
            return jsonify({"success": False, "message": "Missing reservation ID"}), 400
        
        # Check if reservation exists and belongs to user
        reservation = Reservation.query.filter_by(
            reservation_id=reservation_id,
            user_id=user_id,
            status="completed"
        ).first()
        
        if not reservation:
            return jsonify({"success": False, "message": "Completed reservation not found"}), 404
        
        # Check if void request already exists
        existing_void = VoidProduct.query.filter_by(
            reservation_id=reservation_id,
            user_id=user_id
        ).first()
        
        if existing_void:
            return jsonify({"success": False, "message": "Void request already submitted"}), 400
        
        # Handle file upload
        image_path = None
        if 'void_image' in request.files:
            file = request.files['void_image']
            if file and file.filename:
                if not allowed_file(file.filename):
                    return jsonify({"success": False, "message": "Invalid file type"}), 400
                
                if file.content_length > MAX_FILE_SIZE:
                    return jsonify({"success": False, "message": "File too large (max 5MB)"}), 400
                
                filename = secure_filename(f"void_{reservation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                upload_folder = os.path.join(current_app.root_path, 'static', 'void_images')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                image_path = f"static/void_images/{filename}"
        
        # Create void request
        void_request = VoidProduct(
            reservation_id=reservation_id,
            user_id=user_id,
            product_id=reservation.product_id,
            reason=data.get("reason", ""),
            problem_description=data.get("problem_description", ""),
            return_type=data.get("return_type", "other"),
            image_path=image_path,
            void_status="pending",
            requested_at=datetime.utcnow()
        )
        
        db.session.add(void_request)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Void request submitted successfully",
            "void_id": void_request.void_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error submitting void request: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/user-requests", methods=["GET"])
def get_user_void_requests():
    """Get all void requests for the current user"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        void_requests = db.session.query(
            VoidProduct,
            IncubateeProduct.name,
            IncubateeProduct.image_path,
            Reservation.quantity
        ).join(
            IncubateeProduct, VoidProduct.product_id == IncubateeProduct.product_id
        ).join(
            Reservation, VoidProduct.reservation_id == Reservation.reservation_id
        ).filter(
            VoidProduct.user_id == user_id
        ).order_by(
            VoidProduct.requested_at.desc()
        ).all()
        
        requests_data = []
        for void_request, product_name, product_image, quantity in void_requests:
            # Format image path
            if product_image:
                if '\\' in product_image:
                    filename = product_image.split('\\')[-1]
                    image_url = f"/static/uploads/{filename}"
                elif '/' in product_image:
                    filename = product_image.split('/')[-1]
                    image_url = f"/static/uploads/{filename}"
                else:
                    image_url = f"/static/uploads/{product_image}"
            else:
                image_url = "https://cdn-icons-png.flaticon.com/512/4076/4076505.png"
            
            requests_data.append({
                "void_id": void_request.void_id,
                "reservation_id": void_request.reservation_id,
                "product_name": product_name,
                "product_image": image_url,
                "quantity": quantity,
                "reason": void_request.reason,
                "problem_description": void_request.problem_description,
                "return_type": void_request.return_type,
                "return_type_display": void_request.display_return_type,
                "image_path": void_request.image_path,
                "void_status": void_request.void_status,
                "status_display": void_request.display_status,
                "requested_at": void_request.requested_at.isoformat() if void_request.requested_at else None,
                "requested_at_display": void_request.formatted_requested_at,
                "processed_at": void_request.processed_at.isoformat() if void_request.processed_at else None,
                "admin_notes": void_request.admin_notes,
                "refund_amount": float(void_request.refund_amount) if void_request.refund_amount else None,
                "refund_method": void_request.refund_method,
                "refund_method_display": void_request.display_refund_method
            })
        
        return jsonify({
            "success": True,
            "requests": requests_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching void requests: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/<int:void_id>", methods=["GET"])
def get_void_request(void_id):
    """Get details of a specific void request"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        void_request = VoidProduct.query.filter_by(
            void_id=void_id,
            user_id=user_id
        ).first()
        
        if not void_request:
            return jsonify({"success": False, "message": "Void request not found"}), 404
        
        product = IncubateeProduct.query.get(void_request.product_id)
        reservation = Reservation.query.get(void_request.reservation_id)
        
        response_data = {
            "void_id": void_request.void_id,
            "reservation_id": void_request.reservation_id,
            "product_name": product.name if product else "Unknown Product",
            "product_image": product.image_path if product and product.image_path else None,
            "quantity": reservation.quantity if reservation else 0,
            "reason": void_request.reason,
            "problem_description": void_request.problem_description,
            "return_type": void_request.return_type,
            "return_type_display": void_request.display_return_type,
            "image_path": void_request.image_path,
            "void_status": void_request.void_status,
            "status_display": void_request.display_status,
            "requested_at": void_request.requested_at.isoformat() if void_request.requested_at else None,
            "processed_at": void_request.processed_at.isoformat() if void_request.processed_at else None,
            "admin_notes": void_request.admin_notes,
            "refund_amount": float(void_request.refund_amount) if void_request.refund_amount else None,
            "refund_method": void_request.refund_method
        }
        
        return jsonify({"success": True, "request": response_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching void request: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/<int:void_id>/cancel", methods=["POST"])
def cancel_void_request(void_id):
    """Cancel a pending void request"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        void_request = VoidProduct.query.filter_by(
            void_id=void_id,
            user_id=user_id,
            void_status="pending"
        ).first()
        
        if not void_request:
            return jsonify({"success": False, "message": "Pending void request not found"}), 404
        
        # Delete the image file if exists
        if void_request.image_path and os.path.exists(void_request.image_path):
            os.remove(void_request.image_path)
        
        db.session.delete(void_request)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Void request cancelled successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error cancelling void request: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/count", methods=["GET"])
def get_void_counts():
    """Get counts of void requests by status for current user"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        counts = {}
        for status in ["pending", "approved", "rejected", "refunded"]:
            count = VoidProduct.query.filter_by(user_id=user_id,void_status=status).count()
            counts[status] = count
        
        return jsonify({"success": True,"counts": counts})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching void counts: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500
    
@void_bp.route("/admin/all", methods=["GET"])
def get_all_void_requests():
    """Get all void requests for admin with pagination"""
    try:
        # Check if user is admin
        if not session.get("admin_logged_in"):
            return jsonify({"success": False, "message": "Admin not logged in"}), 401
        
        # Get pagination parameters
        status = request.args.get("status", "all")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        # Base query
        query = db.session.query(
            VoidProduct,
            IncubateeProduct.name.label("product_name"),
            IncubateeProduct.image_path,
            IncubateeProduct.price_per_stocks,
            Reservation.quantity,
            Reservation.reservation_id
        ).join(
            IncubateeProduct, VoidProduct.product_id == IncubateeProduct.product_id
        ).join(
            Reservation, VoidProduct.reservation_id == Reservation.reservation_id
        )
        
        # Filter by status
        if status != 'all':
            query = query.filter(VoidProduct.void_status == status)
        
        # Order by newest first
        query = query.order_by(VoidProduct.requested_at.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        void_requests = paginated.items
        
        requests_data = []
        for void_request, product_name, product_image, price, quantity, reservation_id in void_requests:
            # Format image path
            if product_image:
                if '\\' in product_image:
                    filename = product_image.split('\\')[-1]
                    image_url = f"/static/uploads/{filename}"
                elif '/' in product_image:
                    filename = product_image.split('/')[-1]
                    image_url = f"/static/uploads/{filename}"
                else:
                    image_url = f"/static/uploads/{product_image}"
            else:
                image_url = "https://cdn-icons-png.flaticon.com/512/4076/4076505.png"
            
            requests_data.append({
                "void_id": void_request.void_id,
                "reservation_id": void_request.reservation_id,
                "user_id": void_request.user_id,
                "product_name": product_name,
                "product_image": image_url,
                "quantity": quantity,
                "price": float(price) if price else 0,
                "total": float(price) * quantity if price else 0,
                "reason": void_request.reason,
                "problem_description": void_request.problem_description,
                "return_type": void_request.return_type,
                "return_type_display": void_request.display_return_type,
                "image_path": void_request.image_path,
                "void_status": void_request.void_status,
                "status_display": void_request.display_status,
                "requested_at": void_request.requested_at.isoformat() if void_request.requested_at else None,
                "requested_at_display": void_request.formatted_requested_at,
                "processed_at": void_request.processed_at.isoformat() if void_request.processed_at else None,
                "processed_at_display": void_request.formatted_processed_at,
                "admin_notes": void_request.admin_notes,
                "refund_amount": float(void_request.refund_amount) if void_request.refund_amount else None,
                "refund_method": void_request.refund_method,
                "refund_method_display": void_request.display_refund_method
            })
        
        return jsonify({
            "success": True,
            "requests": requests_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching all void requests: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/admin/<int:void_id>", methods=["GET"])
def get_admin_void_request(void_id):
    """Get void request details for admin"""
    try:
        # Check if user is admin
        if not session.get("admin_logged_in"):
            return jsonify({"success": False, "message": "Admin not logged in"}), 401
        
        void_request = VoidProduct.query.get(void_id)
        
        if not void_request:
            return jsonify({"success": False, "message": "Void request not found"}), 404
        
        product = IncubateeProduct.query.get(void_request.product_id)
        reservation = Reservation.query.get(void_request.reservation_id)
        
        # Format product image
        product_image = None
        if product and product.image_path:
            if '\\' in product.image_path:
                filename = product.image_path.split('\\')[-1]
                product_image = f"/static/uploads/{filename}"
            elif '/' in product.image_path:
                filename = product.image_path.split('/')[-1]
                product_image = f"/static/uploads/{filename}"
            else:
                product_image = f"/static/uploads/{product.image_path}"
        
        response_data = {
            "void_id": void_request.void_id,
            "reservation_id": void_request.reservation_id,
            "user_id": void_request.user_id,
            "product_name": product.name if product else "Unknown Product",
            "product_image": product_image,
            "quantity": reservation.quantity if reservation else 0,
            "price": float(product.price_per_stocks) if product and product.price_per_stocks else 0,
            "total": float(product.price_per_stocks) * reservation.quantity if product and product.price_per_stocks and reservation else 0,
            "reason": void_request.reason,
            "problem_description": void_request.problem_description,
            "return_type": void_request.return_type,
            "return_type_display": void_request.display_return_type,
            "image_path": void_request.image_path,
            "void_status": void_request.void_status,
            "status_display": void_request.display_status,
            "requested_at": void_request.requested_at.isoformat() if void_request.requested_at else None,
            "requested_at_display": void_request.formatted_requested_at,
            "processed_at": void_request.processed_at.isoformat() if void_request.processed_at else None,
            "processed_at_display": void_request.formatted_processed_at,
            "admin_notes": void_request.admin_notes,
            "refund_amount": float(void_request.refund_amount) if void_request.refund_amount else None,
            "refund_method": void_request.refund_method,
            "refund_method_display": void_request.display_refund_method
        }
        
        return jsonify({"success": True, "request": response_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin void request: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/admin/process", methods=["POST"])
def process_void_request():
    """Process void request (approve/reject)"""
    try:
        # Check if user is admin
        if not session.get("admin_logged_in"):
            return jsonify({"success": False, "message": "Admin not logged in"}), 401
        
        data = request.get_json()
        void_id = data.get("void_id")
        action = data.get("action")  # 'approve' or 'reject'
        admin_notes = data.get("admin_notes", "")
        refund_amount = data.get("refund_amount")
        refund_method = data.get("refund_method")
        
        void_request = VoidProduct.query.get(void_id)
        
        if not void_request:
            return jsonify({"success": False, "message": "Void request not found"}), 404
        
        if void_request.void_status != "pending":
            return jsonify({"success": False, "message": "This request has already been processed"}), 400
        
        # Update void request
        void_request.void_status = action if action == 'reject' else 'approved'
        void_request.processed_at = datetime.utcnow()
        void_request.admin_notes = admin_notes
        
        # If approved, set refund details
        if action == 'approve':
            void_request.refund_amount = refund_amount
            void_request.refund_method = refund_method
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Void request {action}ed successfully",
            "void_id": void_request.void_id,
            "status": void_request.void_status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing void request: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500

@void_bp.route("/admin/counts", methods=["GET"])
def get_admin_void_counts():
    """Get counts of void requests by status for admin"""
    try:
        # Check if user is admin
        if not session.get("admin_logged_in"):
            return jsonify({"success": False, "message": "Admin not logged in"}), 401
        
        counts = {}
        for status in ["pending", "approved", "rejected", "refunded"]:
            count = VoidProduct.query.filter_by(void_status=status).count()
            counts[status] = count
        
        return jsonify({"success": True, "counts": counts})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin void counts: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500