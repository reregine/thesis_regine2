# Reservation endpoints
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..extension import db
from ..models import Reservation, Product

reserve_bp = Blueprint("reservation", __name__, url_prefix="/reservation")

@reserve_bp.route("/new/<int:product_id>", methods=["GET", "POST"])
def new_reservation(product_id):
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        customer_name = request.form.get("name")
        customer_email = request.form.get("email")
        quantity = int(request.form.get("quantity", 1))

        reservation = Reservation(
            customer_name=customer_name,
            customer_email=customer_email,
            quantity=quantity,
            product_id=product.id
        )
        db.session.add(reservation)
        db.session.commit()
        flash("Reservation created successfully!", "success")
        return redirect(url_for("showroom.index"))

    return render_template("reservation/form.html", product=product)
