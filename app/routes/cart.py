from flask import Blueprint, jsonify, request, session, current_app, render_template, redirect, url_for
from app.extension import db
from app.models.cart import Cart
from app.models.reservation import Reservation
from app.models.admin import IncubateeProduct
from app.models.user import User
from datetime import datetime

cart_bp = Blueprint("cart_bp", __name__, url_prefix="/cart")

@cart_bp.route("/")
def cart_page():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    # This will render templates/cart/cart.html
    return render_template("cart/cart.html")

@cart_bp.route("/count", methods=["GET"])
def cart_count():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        # Count DISTINCT products in the user's cart
        total_items = db.session.query(db.func.count(Cart.product_id))\
            .filter(Cart.user_id == user_id).scalar() or 0

        return jsonify({"success": True, "count": total_items}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching cart count: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500
    
@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        data = request.get_json()
        product_id = data.get("product_id")
        quantity = data.get("quantity", 1)

        if not product_id:
            return jsonify({"success": False, "message": "Missing product_id"}), 400

        # Check if product exists
        product = IncubateeProduct.query.get(product_id)
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404

        # Check if already in cart
        existing = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
        if existing:
            existing.quantity += quantity
        else:
            cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()
        return jsonify({"success": True, "message": "Added to cart successfully"})

    except Exception as e:
        current_app.logger.error(f"Error adding to cart: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500

@cart_bp.route("/get-items", methods=["GET"])
def get_cart_items():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        cart_items = (
            db.session.query(Cart, IncubateeProduct)
            .join(IncubateeProduct, Cart.product_id == IncubateeProduct.product_id)
            .filter(Cart.user_id == user_id)
            .all())

        if not cart_items:
            return jsonify({"success": True, "items": [], "message": "Your cart is empty."}), 200

        items = []
        for cart, product in cart_items:
            # FIX: Handle paths that start with "static/"
            if product.image_path:
                # Remove "static/" prefix if it exists
                clean_path = product.image_path
                if clean_path.startswith('static/'):
                    clean_path = clean_path.replace('static/', '', 1)
                
                image_url = url_for('static', filename=clean_path)
            else:
                image_url = url_for('static', filename='images/no-image.png')
                
            items.append({
                "cart_id": cart.cart_id,
                "product_id": product.product_id,
                "name": product.name,
                "image_path": image_url,
                "price_per_stocks": float(product.price_per_stocks or 0),
                "stock_amount": product.stock_amount or 0,
                "quantity": cart.quantity,
                "added_at": cart.added_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({"success": True, "items": items}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching cart items: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@cart_bp.route("/reserve", methods=["POST"])
def reserve_selected_items():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        data = request.get_json()
        cart_ids = data.get("cart_ids", [])
        if not cart_ids:
            return jsonify({"success": False, "message": "No items selected"}), 400

        selected_items = Cart.query.filter(Cart.user_id == user_id, Cart.cart_id.in_(cart_ids)).all()

        if not selected_items:
            return jsonify({"success": False, "message": "No valid items found"}), 404

        for item in selected_items:
            reservation = Reservation(user_id=user_id,product_id=item.product_id,quantity=item.quantity,status="pending",reserved_at=datetime.utcnow())
            db.session.add(reservation)
            db.session.delete(item)  # remove from cart after reservation

        db.session.commit()
        return jsonify({"success": True, "message": "Items reserved successfully"})

    except Exception as e:
        current_app.logger.error(f"Error reserving items: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500

@cart_bp.route("/delete/<int:cart_id>", methods=["DELETE"])
def delete_cart_item(cart_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        item = Cart.query.filter_by(cart_id=cart_id, user_id=user_id).first()
        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": "Item deleted successfully"})

    except Exception as e:
        current_app.logger.error(f"Error deleting cart item: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500
    
@cart_bp.route("/update-quantity/<int:cart_id>", methods=["POST"])
def update_cart_quantity(cart_id):
    try:
        data = request.get_json()
        qty = data.get("quantity")
        if qty is None or qty <= 0:
            return jsonify({"success": False, "message": "Invalid quantity"}), 400

        cart_item = Cart.query.get(cart_id)
        if not cart_item:
            return jsonify({"success": False, "message": "Cart item not found"}), 404

        cart_item.quantity = qty
        db.session.commit()

        return jsonify({"success": True, "message": "Quantity updated"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

