from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.models.shop import Shop

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")


@shop_bp.route("/")
def shop_home():
    """Render the shop page."""
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))
    return render_template("shop/shop.html")


@shop_bp.route("/search-products", methods=["GET"])
def search_products():
    """Search or list all incubatee products."""
    query = request.args.get("q", "").strip()

    try:
        products = Shop.search_products(query)
        result = []
        for p in products:
            result.append({
                "incubatee_id": p.incubatee_id,
                "name": p.name,
                "products": p.products,
                "category": p.category,
                "details": p.details,
                "price_per_stocks": float(p.price_per_stocks),
                "expiration_date": (
                    p.expiration_date.strftime("%Y-%m-%d")
                    if p.expiration_date
                    else "No Expiry"
                ),
                "warranty": p.warranty,
                "added_on": p.added_on.strftime("%Y-%m-%d"),
                "image_path": p.image_path
            })

        return jsonify({"success": True, "products": result})

    except Exception as e:
        print("❌ Error fetching products:", e)
        return jsonify({"success": False, "error": str(e)}), 500
