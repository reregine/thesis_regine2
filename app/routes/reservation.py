from flask import Blueprint, request, jsonify, session, current_app, url_for
from app.extension import db
from ..models.reservation import Reservation
from ..models.admin import IncubateeProduct
from datetime import datetime

reservation_bp = Blueprint("reservation_bp", __name__, url_prefix="/reservations")


# ======================================================
# CREATE A RESERVATION
# ======================================================
@reservation_bp.route("/create", methods=["POST"])
def create_reservation():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not all([user_id, product_id, quantity]):
            return jsonify({"error": "Missing required fields"}), 400

        product = IncubateeProduct.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        if product.stock_amount < quantity:
            return jsonify({"error": "Insufficient stock"}), 400

        # Temporarily deduct stock (optional)
        product.stock_amount -= quantity
        reservation = Reservation(user_id=user_id,product_id=product_id,quantity=quantity,status="pending",reserved_at=datetime.utcnow())

        db.session.add(reservation)
        db.session.commit()

        return jsonify({"message": "Reservation created successfully","reservation_id": reservation.reservation_id,}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating reservation: {e}")
        return jsonify({"error": "Server error"}), 500


# ======================================================
# GET ALL RESERVATIONS (ADMIN / STAFF)
# ======================================================
@reservation_bp.route("/", methods=["GET"])
def get_all_reservations():
    try:
        reservations = Reservation.query.all()
        result = [{"reservation_id": r.reservation_id,"user_id": r.user_id,"product_name": r.product.name,"quantity": r.quantity,"status": r.status,"reserved_at": r.reserved_at.strftime("%Y-%m-%d %H:%M:%S"),} for r in reservations]

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching all reservations: {e}")
        return jsonify({"error": "Server error"}), 500

# ======================================================
# GET RESERVATIONS BY STATUS (Shopee-style tab)
# ======================================================
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


# ======================================================
# UPDATE RESERVATION STATUS
# ======================================================
@reservation_bp.route("/<int:reservation_id>/status", methods=["PUT"])
def update_reservation_status(reservation_id):
    try:
        data = request.get_json()
        new_status = data.get("status")
        reason = data.get("reason")

        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({"error": "Reservation not found"}), 404

        if new_status not in ["pending", "approved", "completed", "rejected"]:
            return jsonify({"error": "Invalid status"}), 400

        reservation.status = new_status

        if new_status == "approved":
            reservation.approved_at = datetime.utcnow()
        elif new_status == "completed":
            reservation.completed_at = datetime.utcnow()
        elif new_status == "rejected":
            reservation.rejected_at = datetime.utcnow()
            reservation.rejected_reason = reason or "No reason provided"

        db.session.commit()
        return jsonify({"message": f"Reservation status updated to {new_status}"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating reservation: {e}")
        return jsonify({"error": "Server error"}), 500


# ======================================================
# DELETE RESERVATION
# ======================================================
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
