from flask import Blueprint, jsonify, request, session, url_for
from ..extension import db
from ..models.favorites import Favorite
from ..models.admin import IncubateeProduct
from ..models.user import User

favorites_bp = Blueprint("favorites_bp", __name__, url_prefix="/favorites")

@favorites_bp.route("/add", methods=["POST"])
def add_to_favorites():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        data = request.get_json()
        product_id = data.get("product_id")

        if not product_id:
            return jsonify({"success": False, "message": "Product ID is required"}), 400

        # Check if product exists
        product = IncubateeProduct.query.get(product_id)
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404

        # Check if already in favorites
        existing_favorite = Favorite.query.filter_by(
            user_id=user_id, 
            product_id=product_id
        ).first()

        if existing_favorite:
            return jsonify({"success": False, "message": "Product already in favorites"}), 400

        # Add to favorites
        favorite = Favorite(user_id=user_id, product_id=product_id)
        db.session.add(favorite)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Product added to favorites",
            "favorite_id": favorite.favorite_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@favorites_bp.route("/remove", methods=["POST"])
def remove_from_favorites():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        data = request.get_json()
        product_id = data.get("product_id")

        if not product_id:
            return jsonify({"success": False, "message": "Product ID is required"}), 400

        # Find and remove favorite
        favorite = Favorite.query.filter_by(
            user_id=user_id, 
            product_id=product_id
        ).first()

        if not favorite:
            return jsonify({"success": False, "message": "Product not in favorites"}), 404

        db.session.delete(favorite)
        db.session.commit()

        return jsonify({"success": True, "message": "Product removed from favorites"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@favorites_bp.route("/toggle", methods=["POST"])
def toggle_favorite():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        data = request.get_json()
        product_id = data.get("product_id")

        if not product_id:
            return jsonify({"success": False, "message": "Product ID is required"}), 400

        # Check if already in favorites
        existing_favorite = Favorite.query.filter_by(
            user_id=user_id, 
            product_id=product_id
        ).first()

        if existing_favorite:
            # Remove from favorites
            db.session.delete(existing_favorite)
            db.session.commit()
            return jsonify({
                "success": True, 
                "message": "Product removed from favorites",
                "is_favorite": False
            })
        else:
            # Add to favorites
            favorite = Favorite(user_id=user_id, product_id=product_id)
            db.session.add(favorite)
            db.session.commit()
            return jsonify({
                "success": True, 
                "message": "Product added to favorites",
                "is_favorite": True,
                "favorite_id": favorite.favorite_id
            })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@favorites_bp.route("/user", methods=["GET"])
def get_user_favorites():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        # Get user's favorites with product details
        favorites = (
            db.session.query(Favorite, IncubateeProduct)
            .join(IncubateeProduct, Favorite.product_id == IncubateeProduct.product_id)
            .filter(Favorite.user_id == user_id)
            .all()
        )

        favorite_products = []
        for favorite, product in favorites:
            # Handle image path
            if product.image_path:
                clean_path = product.image_path
                if clean_path.startswith('static/'):
                    clean_path = clean_path.replace('static/', '', 1)
                image_url = url_for('static', filename=clean_path)
            else:
                image_url = url_for('static', filename='images/no-image.png')
                
            favorite_products.append({
                "favorite_id": favorite.favorite_id,
                "product_id": product.product_id,
                "name": product.name,
                "image_path": image_url,
                "price_per_stocks": float(product.price_per_stocks or 0),
                "category": product.category,
                "details": product.details,
                "added_at": favorite.added_at.isoformat() if favorite.added_at else None
            })

        return jsonify({
            "success": True, 
            "favorites": favorite_products,
            "count": len(favorite_products)
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@favorites_bp.route("/check/<int:product_id>", methods=["GET"])
def check_favorite_status(product_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        favorite = Favorite.query.filter_by(
            user_id=user_id, 
            product_id=product_id
        ).first()

        return jsonify({
            "success": True, 
            "is_favorite": favorite is not None
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500