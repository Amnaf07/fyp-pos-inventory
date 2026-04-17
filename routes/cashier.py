from flask import Blueprint, render_template, request, jsonify, flash
from db import db
from models import Product, Sale
from auth import login_required, role_required
import json
from datetime import datetime

bp = Blueprint("cashier", __name__, url_prefix="/cashier")

@bp.route("/dashboard")
@login_required
@role_required("Cashier")
def cashier_dashboard():
    products = Product.query.all()
    return render_template("dashboard_cashier.html", products=products)

@bp.route("/checkout", methods=["POST"])
@login_required
@role_required("Cashier")
def checkout():
    data = request.get_json()
    cart = data.get("cart", [])

    for item in cart:
        product = Product.query.get(item["id"])
        if not product:
            return jsonify({"error": f"Product ID {item['id']} not found"}), 400
        if product.stock < item["qty"]:
            return jsonify({"error": f"Insufficient stock for {product.name}"}), 400

    total = sum(item["qty"] * float(item["price"]) for item in cart)
    sale = Sale(total=total, items=json.dumps(cart))
    db.session.add(sale)

    for item in cart:
        product = Product.query.get(item["id"])
        product.stock -= item["qty"]

    db.session.commit()
    return jsonify({"message": "Sale successful", "receipt_id": sale.id})
