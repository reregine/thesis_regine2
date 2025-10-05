# app/routes/contact.py
from flask import Blueprint, render_template

# Create a blueprint for contacts
contact_bp = Blueprint("contact", __name__, url_prefix="/contacts")

@contact_bp.route("/", methods=["GET"])
def contact_page():
    # This will render your contacts.html page
    return render_template("contacts/contacts.html")
